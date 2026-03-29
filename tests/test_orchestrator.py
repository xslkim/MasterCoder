from pathlib import Path

import pytest

from mastercoder_automation.config import Settings
from mastercoder_automation.models import PipelineState, ReqRecord, ReqState
from mastercoder_automation.orchestrator import (
    Orchestrator,
    _truncate_gate_reason,
    is_transient_error,
)
from mastercoder_automation.state_store import StateStore


class DummyGh:
    def __init__(self) -> None:
        self.merged = []
        self.approved: list[int] = []
        self.requested_changes: list[int] = []

    def approve_pr(self, pr_number: int, body: str, *, gh_token: str | None = None) -> None:
        self.approved.append(pr_number)

    def request_changes(self, pr_number: int, body: str, *, gh_token: str | None = None) -> None:
        self.requested_changes.append(pr_number)

    def comment_pr(self, pr_number: int, body: str, *, gh_token: str | None = None) -> None:
        pass

    def merge_pr(self, pr_number: int, *, gh_token: str | None = None) -> None:
        self.merged.append(pr_number)


def _make_state_file(tmp_path: Path, state: PipelineState) -> Path:
    path = tmp_path / "req-status.json"
    StateStore(path).save(state)
    return path


def _stub_branch_checks(monkeypatch, *, changed_files=None, commits_ahead: int = 1) -> None:
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_worktree_exists",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_current_branch",
        lambda *_a, **_k: "main",
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_prepare_worktree",
        lambda repo_root, branch: repo_root / ".automation-worktrees" / branch.replace("/", "__"),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_changed_files_against_default",
        lambda *_a, **_k: changed_files or ["tests/test_req02.py", "src/mastercoder/config.py"],
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_commits_ahead_of_default",
        lambda *_a, **_k: commits_ahead,
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_diff_against_default",
        lambda *_a, **_k: "diff --git a/tests/test_req02.py b/tests/test_req02.py\n+assert True\n",
    )


def test_ready_transitions_when_dependencies_done(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(req_id="REQ-01", title="base", state=ReqState.DONE),
            ReqRecord(
                req_id="REQ-02", title="child", blocked_by=["REQ-01"], state=ReqState.PENDING
            ),
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))

    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "test-review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "test-qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("skipped", 7),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": True, "output": "ok"})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_test_cases_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.qa_decision",
        lambda *_: type("D", (), {"verdict": "QA_PASSED", "reasons": []})(),
    )
    _stub_branch_checks(monkeypatch)

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once()
    by_id = {r.req_id: r for r in new_state.requirements}
    assert by_id["REQ-02"].state == ReqState.DONE


def test_failures_go_to_fixing_then_blocked(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-01",
                title="base",
                state=ReqState.READY,
                retries=3,
                max_retries=3,
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))

    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "test-review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "test-qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("skipped", None),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": False, "output": "gate failed"})(),
    )
    _stub_branch_checks(monkeypatch)

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once()
    req = new_state.requirements[0]
    assert req.state == ReqState.BLOCKED
    assert req.last_error is not None


def test_run_once_unknown_req_id_raises(tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-01", title="base", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    with pytest.raises(ValueError, match="REQ-99"):
        orchestrator.run_once(req_id="REQ-99")


def test_blocked_by_unknown_dependency_stays_pending(tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(req_id="REQ-01", title="base", state=ReqState.DONE),
            ReqRecord(
                req_id="REQ-02",
                title="child",
                blocked_by=["REQ-typo-not-in-list"],
                state=ReqState.PENDING,
            ),
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once()
    assert new_state.requirements[1].state == ReqState.PENDING


def test_merge_failure_does_not_crash(monkeypatch, tmp_path: Path) -> None:
    class BadMergeGh(DummyGh):
        def merge_pr(self, pr_number: int, *, gh_token: str | None = None) -> None:
            raise RuntimeError("merge denied")

    state = PipelineState(
        requirements=[
            ReqRecord(req_id="REQ-01", title="base", state=ReqState.READY),
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "test-review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "test-qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("ok", 1),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": True, "output": "ok"})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_test_cases_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.qa_decision",
        lambda *_: type("D", (), {"verdict": "QA_PASSED", "reasons": []})(),
    )
    _stub_branch_checks(monkeypatch)
    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=BadMergeGh())
    new_state = orchestrator.run_once()
    assert new_state.requirements[0].state == ReqState.DONE


def test_missing_test_changes_goes_to_fixing(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-02", title="config", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("ok", None),
    )
    _stub_branch_checks(monkeypatch, changed_files=["src/mastercoder/config.py"])

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "tests/" in (req.last_error or "")


def test_missing_commits_goes_to_fixing(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-02", title="config", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("ok", None),
    )
    _stub_branch_checks(monkeypatch, commits_ahead=0)

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "没有新的 commit" in (req.last_error or "")


def test_branch_prepare_failure_goes_to_fixing(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-02", title="config", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    def fail_prepare_worktree(*_a, **_k):
        raise RuntimeError("worktree blocked")

    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_prepare_worktree",
        fail_prepare_worktree,
    )

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "准备开发 worktree 失败" in (req.last_error or "")


def test_prepare_branch_reuses_worktree_path(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-02",
                title="config",
                state=ReqState.READY,
                branch="feat/req-02-change",
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_prepare_worktree",
        lambda repo_root, branch: repo_root / ".automation-worktrees" / branch.replace("/", "__"),
    )
    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    out = orchestrator._prepare_req_branch(state.requirements[0])
    assert out == Path(".") / ".automation-worktrees" / "feat__req-02-change"
    assert state.requirements[0].branch == "feat/req-02-change"


def test_resume_existing_branch_skips_dev_agent(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-02",
                title="config",
                state=ReqState.FIXING,
                branch="feat/req-02-change",
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    monkeypatch.setenv("GIT_AGENT_TOKEN_DEV", "dev-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_worktree_exists",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_current_branch",
        lambda *_a, **_k: "feat/req-02-change",
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_changed_files_against_default",
        lambda *_a, **_k: ["tests/test_config.py", "src/mastercoder/config.py"],
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_commits_ahead_of_default",
        lambda *_a, **_k: 1,
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: (_ for _ in ()).throw(AssertionError("dev crew should be skipped")),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": True, "output": "ok"})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.git_push_https",
        lambda *_a, **_k: "pushed",
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.gh_pr_create_json",
        lambda *_a, **_k: 23,
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_test_cases_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": []})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.qa_decision",
        lambda *_: type("D", (), {"verdict": "QA_PASSED", "reasons": []})(),
    )

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.pr_number == 23
    assert req.state == ReqState.DONE


def test_rejected_test_case_review_goes_to_fixing(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-02", title="config", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    gh = DummyGh()

    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("ok", 5),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": True, "output": "ok"})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": ["code ok"]})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_test_cases_decision",
        lambda *_: type("D", (), {"verdict": "REJECTED", "reasons": ["tests too weak"]})(),
    )
    _stub_branch_checks(monkeypatch)

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=gh)
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "测试用例审查未通过" in (req.last_error or "")
    assert gh.requested_changes == [5]


def test_missing_test_diff_goes_to_fixing(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[ReqRecord(req_id="REQ-02", title="config", state=ReqState.READY)]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    gh = DummyGh()

    monkeypatch.setenv("GIT_AGENT_TOKEN_REVIEW", "review-token")
    monkeypatch.setenv("GIT_AGENT_TOKEN_TEST", "qa-token")
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_dev_implementation_crew",
        lambda *_: ("ok", 6),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.run_quality_gates",
        lambda *_a, **_k: type("G", (), {"passed": True, "output": "ok"})(),
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.review_decision",
        lambda *_: type("D", (), {"verdict": "APPROVED", "reasons": ["code ok"]})(),
    )
    _stub_branch_checks(monkeypatch)
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_diff_against_default",
        lambda *_a, **_k: "",
    )

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=gh)
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "必须先经过 review 工程师审核" in (req.last_error or "")
    assert gh.requested_changes == [6]


def test_is_transient_error() -> None:
    assert is_transient_error("Connection timed out while pushing to origin")
    assert is_transient_error("HTTP 503 service unavailable")
    assert is_transient_error("Error 429 too many requests")
    assert not is_transient_error("pytest failed: AssertionError")
    assert not is_transient_error("审查未通过：ruff format")


def test_truncate_gate_reason_keeps_head_and_tail() -> None:
    suffix = "FAIL: last line of pytest output"
    long = ("PASS\n" * 400) + suffix
    out = _truncate_gate_reason(long)
    assert len(out) <= 2000
    assert "[truncated middle]" in out
    assert suffix in out


def test_retry_or_block_transient_does_not_increment_retries(tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-01",
                title="x",
                state=ReqState.FIXING,
                retries=2,
                max_retries=3,
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    orch = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    req = orch.store.load().requirements[0]
    orch._retry_or_block(
        req,
        "fatal: unable to access 'https://github.com/x/y.git/': Failed to connect: Connection timed out",
        transient=None,
    )
    assert req.retries == 2
    assert req.state == ReqState.FIXING


def test_retry_or_block_non_transient_increments_retries(tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-01",
                title="x",
                state=ReqState.FIXING,
                retries=2,
                max_retries=3,
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    orch = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    req = orch.store.load().requirements[0]
    orch._retry_or_block(req, "FAILED tests/test_x.py::test_a - AssertionError", transient=None)
    assert req.retries == 3
    assert req.state == ReqState.FIXING


def test_unblock_req_resets_state(tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-01",
                title="x",
                state=ReqState.BLOCKED,
                retries=4,
                max_retries=3,
                last_error="old",
            )
        ]
    )
    state_file = _make_state_file(tmp_path, state)
    settings = Settings("gpt-4o-mini", "x/y", 80, state_file, Path("."))
    orch = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    out = orch.unblock_req("REQ-01")
    rec = out.requirements[0]
    assert rec.state == ReqState.READY
    assert rec.retries == 0
    assert rec.last_error is None
