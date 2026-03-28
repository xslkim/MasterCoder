from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .models import ReqRecord


def branch_slug(req: ReqRecord) -> str:
    rid = req.req_id.replace("_", "-").lower()
    s = req.title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = s[:48].strip("-") or "change"
    return f"feat/{rid}-{s}"


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


def git_checkout_main_pull(repo_root: Path) -> str:
    _git(repo_root, "fetch", "origin")
    try:
        _git(repo_root, "checkout", "main")
    except RuntimeError:
        _git(repo_root, "checkout", "master")
    try:
        _git(repo_root, "pull", "origin", "main", "--ff-only")
    except RuntimeError:
        _git(repo_root, "pull", "origin", "master", "--ff-only")
    return "成功：已更新默认分支"


def git_create_branch(repo_root: Path, branch: str) -> str:
    try:
        _git(repo_root, "checkout", "-b", branch)
    except RuntimeError:
        _git(repo_root, "checkout", branch)
    return f"成功：当前分支 {branch}"


def git_status_short(repo_root: Path) -> str:
    return _git(repo_root, "status", "--short") or "(clean)"


def git_add_all(repo_root: Path) -> str:
    _git(repo_root, "add", "-A")
    return "成功：已执行 git add -A"


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


def gh_pr_create_json(repo: str, head: str, title: str, body: str, token: str) -> int:
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
            "--json",
            "number",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    payload = json.loads(proc.stdout)
    return int(payload["number"])
