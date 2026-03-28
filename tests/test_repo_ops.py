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
