from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from shutil import which

from .models import ReqRecord


def _pr_number_from_gh_create_stdout(stdout: str) -> int:
    """解析 `gh pr create` 输出：新版可能为 JSON，旧版为一行 PR URL。"""
    text = (stdout or "").strip()
    if not text:
        raise ValueError("gh pr create 无输出")
    if text.startswith("{"):
        try:
            return int(json.loads(text)["number"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
    m = re.search(r"github\.com/[^/\s]+/[^/\s]+/pull/(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"/pull/(\d+)", text)
    if m:
        return int(m.group(1))
    raise ValueError(f"无法从 gh pr create 输出解析 PR 编号：{text[:800]!r}")


def _pr_number_from_gh_pr_list(stdout: str) -> int | None:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    number = first.get("number")
    if isinstance(number, int):
        return number
    return None


def branch_slug(req: ReqRecord) -> str:
    rid = req.req_id.replace("_", "-").lower()
    s = req.title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = s[:48].strip("-") or "change"
    return f"feat/{rid}-{s}"


def automation_worktree_path(repo_root: Path, branch: str) -> Path:
    safe = branch.replace("/", "__")
    return (repo_root.resolve() / ".automation-worktrees" / safe).resolve()


def resolve_under_repo(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    rel = relative.strip().replace("\\", "/")
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("invalid relative_path")
    target = (root / rel).resolve()
    target.relative_to(root)
    return target


def repo_read_text(repo_root: Path, relative_path: str) -> str:
    path = resolve_under_repo(repo_root, relative_path)
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    return path.read_text(encoding="utf-8")


def repo_read_requirement_section(
    repo_root: Path, req_id: str, relative_path: str = "docs/requirements.md"
) -> str:
    text = repo_read_text(repo_root, relative_path)
    pattern = rf"^##\s+{re.escape(req_id)}[：:].*?(?=^##\s+REQ-\d+[：:]|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"未在 {relative_path} 中找到需求章节：{req_id}")
    return match.group(0).strip()


def repo_write_text(repo_root: Path, relative_path: str, content: str) -> str:
    path = resolve_under_repo(repo_root, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"成功：已写入 {relative_path}（{len(content)} 字节）"


def _git(repo_root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env or os.environ,
        check=False,
    )
    err = (proc.stderr or proc.stdout or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"git 命令失败 {' '.join(args)}\n{err}")
    return proc.stdout.strip()


def _git_remote_url(repo_root: Path, remote: str = "origin") -> str | None:
    try:
        return _git(repo_root, "remote", "get-url", remote).strip()
    except RuntimeError:
        return None


def _github_https_remote_url(repo_root: Path, remote: str = "origin") -> str | None:
    raw = _git_remote_url(repo_root, remote)
    if raw:
        text = raw.strip()
        if text.startswith("https://github.com/"):
            return text.removesuffix("/")
        m = re.match(r"git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?$", text)
        if m:
            return f"https://github.com/{m.group(1)}/{m.group(2)}.git"
        m = re.match(r"ssh://git@github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?$", text)
        if m:
            return f"https://github.com/{m.group(1)}/{m.group(2)}.git"
    env_repo = (os.getenv("GITHUB_REPO") or "").strip()
    if "/" not in env_repo:
        return None
    owner, _, repo = env_repo.partition("/")
    return f"https://github.com/{owner}/{repo}.git"


def _git_fetch_origin(repo_root: Path) -> str:
    try:
        return _git(repo_root, "fetch", "origin")
    except RuntimeError as origin_err:
        https_url = _github_https_remote_url(repo_root)
        if not https_url:
            raise
        try:
            return _git(
                repo_root,
                "fetch",
                https_url,
                "+refs/heads/*:refs/remotes/origin/*",
            )
        except RuntimeError:
            raise origin_err


def git_checkout_main_pull(repo_root: Path) -> str:
    base = default_branch_name(repo_root)
    _git_fetch_origin(repo_root)
    _git(repo_root, "checkout", base)
    _git(repo_root, "pull", "origin", base, "--ff-only")
    return f"成功：已更新默认分支 {base}"


def git_create_branch(repo_root: Path, branch: str) -> str:
    try:
        _git(repo_root, "checkout", "-b", branch)
    except RuntimeError:
        _git(repo_root, "checkout", branch)
    return f"成功：当前分支 {branch}"


def git_current_branch(repo_root: Path) -> str:
    return _git(repo_root, "branch", "--show-current").strip()


def git_worktree_exists(repo_root: Path, branch: str) -> bool:
    path = automation_worktree_path(repo_root, branch)
    return path.exists() and (path / ".git").exists()


def git_prepare_worktree(repo_root: Path, branch: str) -> Path:
    repo_root = repo_root.resolve()
    path = automation_worktree_path(repo_root, branch)
    base = default_branch_name(repo_root)
    _git_fetch_origin(repo_root)

    if git_worktree_exists(repo_root, branch):
        current = git_current_branch(path)
        if current != branch:
            raise RuntimeError(f"已存在 worktree {path}，但当前分支为 {current}，期望 {branch}")
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git(repo_root, "rev-parse", "--verify", branch)
        _git(repo_root, "worktree", "add", str(path), branch)
    except RuntimeError:
        _git(repo_root, "worktree", "add", "-b", branch, str(path), base)
    return path


def default_branch_name(repo_root: Path) -> str:
    try:
        _git(repo_root, "rev-parse", "--verify", "main")
        return "main"
    except RuntimeError:
        _git(repo_root, "rev-parse", "--verify", "master")
        return "master"


def git_changed_files_against_default(repo_root: Path, branch: str | None = None) -> list[str]:
    ref = branch or "HEAD"
    base = default_branch_name(repo_root)
    out = _git(repo_root, "diff", "--name-only", f"{base}...{ref}")
    return [line.strip() for line in out.splitlines() if line.strip()]


def git_diff_against_default(
    repo_root: Path, branch: str | None = None, pathspecs: list[str] | None = None
) -> str:
    ref = branch or "HEAD"
    base = default_branch_name(repo_root)
    args = ["diff", f"{base}...{ref}"]
    if pathspecs:
        args.extend(["--", *pathspecs])
    return _git(repo_root, *args)


def git_commits_ahead_of_default(repo_root: Path, branch: str | None = None) -> int:
    ref = branch or "HEAD"
    base = default_branch_name(repo_root)
    out = _git(repo_root, "rev-list", "--count", f"{base}..{ref}")
    return int(out or "0")


def git_status_short(repo_root: Path) -> str:
    return _git(repo_root, "status", "--short") or "(clean)"


def git_add_all(repo_root: Path) -> str:
    _git(
        repo_root,
        "add",
        "-A",
        "--",
        ".",
        ":(exclude)state/req-status.json",
        ":(exclude).coverage",
    )
    return "成功：已执行 git add -A（已排除 state/req-status.json 与 .coverage）"


def git_commit(repo_root: Path, message: str) -> str:
    name = os.environ.get("GIT_AGENT_USERNAME_DEV", "dev-agent").strip() or "dev-agent"
    email = (
        os.environ.get("GIT_AGENT_EMAIL_DEV", "dev-agent@users.noreply.github.com").strip()
        or "dev-agent@users.noreply.github.com"
    )
    proc = subprocess.run(
        [
            "git",
            "-c",
            f"user.name={name}",
            "-c",
            f"user.email={email}",
            "commit",
            "-m",
            message,
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return "成功：已提交"


def git_push_https(repo_root: Path, branch: str, token: str, github_repo: str) -> str:
    if "/" not in github_repo:
        raise ValueError("github_repo 须为 owner/repo 形式")
    owner, _, repo = github_repo.partition("/")
    url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    proc = subprocess.run(
        ["git", "push", "-u", url, f"HEAD:{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return f"成功：已推送分支 {branch}"


def gh_pr_existing_number(
    repo: str, head: str, token: str, *, cwd: Path | None = None
) -> int | None:
    if which("gh") is None:
        raise RuntimeError("未找到 gh（GitHub CLI），无法查询 PR。请安装：https://cli.github.com/")
    env = {**os.environ}
    if token:
        env["GH_TOKEN"] = token
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            head,
            "--state",
            "open",
            "--json",
            "number",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return _pr_number_from_gh_pr_list(proc.stdout)


def gh_pr_create_json(
    repo: str,
    head: str,
    title: str,
    body: str,
    token: str,
    *,
    cwd: Path | None = None,
) -> int:
    if which("gh") is None:
        raise RuntimeError("未找到 gh（GitHub CLI），无法创建 PR。请安装：https://cli.github.com/")
    env = {**os.environ}
    if token:
        env["GH_TOKEN"] = token
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--head",
            head,
            "--title",
            title,
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )
    # 部分 gh 版本把 PR URL 打在 stdout 或 stderr
    blob = f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
    if proc.returncode != 0:
        if "already exists" in blob.lower():
            existing = gh_pr_existing_number(repo, head, token, cwd=cwd)
            if existing is not None:
                return existing
            return _pr_number_from_gh_create_stdout(blob)
        raise RuntimeError(blob)
    return _pr_number_from_gh_create_stdout(blob)
