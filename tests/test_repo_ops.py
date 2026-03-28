from pathlib import Path

import pytest

from mastercoder_automation import repo_ops
from mastercoder_automation.models import ReqRecord, ReqState


def test_branch_slug() -> None:
    r = ReqRecord(
        req_id="REQ-02",
        title="Configuration system",
        state=ReqState.READY,
    )
    assert repo_ops.branch_slug(r).startswith("feat/req-02-")


def test_pr_number_from_gh_create_stdout_url() -> None:
    out = "https://github.com/octocat/Hello-World/pull/1347\n"
    assert repo_ops._pr_number_from_gh_create_stdout(out) == 1347


def test_pr_number_from_gh_create_stdout_json() -> None:
    assert repo_ops._pr_number_from_gh_create_stdout('{"number": 99}') == 99


def test_resolve_rejects_traversal(tmp_path: Path) -> None:
    (tmp_path / "safe.txt").write_text("x", encoding="utf-8")
    p = repo_ops.resolve_under_repo(tmp_path, "safe.txt")
    assert p.read_text() == "x"
    with pytest.raises(ValueError):
        repo_ops.resolve_under_repo(tmp_path, "../outside")
    with pytest.raises(ValueError):
        repo_ops.resolve_under_repo(tmp_path, "/etc/passwd")


def test_default_branch_name_prefers_main(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        calls.append(args)
        return "main-sha"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    assert repo_ops.default_branch_name(tmp_path) == "main"
    assert calls == [("rev-parse", "--verify", "main")]


def test_git_current_branch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        repo_ops,
        "_git",
        lambda _repo_root, *args, env=None: "feat/req-02-change\n",
    )
    assert repo_ops.git_current_branch(tmp_path) == "feat/req-02-change"


def test_default_branch_name_falls_back_to_master(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        calls.append(args)
        if args[-1] == "main":
            raise RuntimeError("missing main")
        return "master-sha"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    assert repo_ops.default_branch_name(tmp_path) == "master"
    assert calls == [
        ("rev-parse", "--verify", "main"),
        ("rev-parse", "--verify", "master"),
    ]


def test_git_changed_files_against_default(monkeypatch, tmp_path: Path) -> None:
    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        if args[:3] == ("rev-parse", "--verify", "main"):
            return "main-sha"
        assert args == ("diff", "--name-only", "main...feat/req-02-change")
        return "tests/test_req02.py\nsrc/mastercoder/config.py\n"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    assert repo_ops.git_changed_files_against_default(tmp_path, "feat/req-02-change") == [
        "tests/test_req02.py",
        "src/mastercoder/config.py",
    ]


def test_git_commits_ahead_of_default(monkeypatch, tmp_path: Path) -> None:
    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        if args[:3] == ("rev-parse", "--verify", "main"):
            return "main-sha"
        assert args == ("rev-list", "--count", "main..feat/req-02-change")
        return "2"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    assert repo_ops.git_commits_ahead_of_default(tmp_path, "feat/req-02-change") == 2


def test_repo_read_requirement_section_extracts_single_req(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirements.md").write_text(
        "# Specs\n\n## REQ-01：One\nalpha\n\n## REQ-02：Two\nbeta\n\n## REQ-03：Three\ngamma\n",
        encoding="utf-8",
    )
    out = repo_ops.repo_read_requirement_section(tmp_path, "REQ-02")
    assert out.startswith("## REQ-02：Two")
    assert "beta" in out
    assert "REQ-03" not in out


def test_git_checkout_main_pull_uses_detected_default_branch(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        calls.append(args)
        if args[:3] == ("rev-parse", "--verify", "main"):
            return "main-sha"
        return "ok"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    assert repo_ops.git_checkout_main_pull(tmp_path) == "成功：已更新默认分支 main"
    assert calls == [
        ("rev-parse", "--verify", "main"),
        ("fetch", "origin"),
        ("checkout", "main"),
        ("pull", "origin", "main", "--ff-only"),
    ]


def test_git_add_all_excludes_state_and_coverage(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_repo_root: Path, *args: str, env=None) -> str:
        calls.append(args)
        return "ok"

    monkeypatch.setattr(repo_ops, "_git", fake_git)
    msg = repo_ops.git_add_all(tmp_path)
    assert "state/req-status.json" in msg
    assert calls == [
        (
            "add",
            "-A",
            "--",
            ".",
            ":(exclude)state/req-status.json",
            ":(exclude).coverage",
        )
    ]
