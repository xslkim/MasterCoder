from pathlib import Path

import pytest

from mastercoder_automation.config import Settings
from mastercoder_automation.models import PipelineState, ReqRecord, ReqState
from mastercoder_automation.orchestrator import Orchestrator
from mastercoder_automation.state_store import StateStore


class DummyGh:
    def __init__(self) -> None:
        self.merged = []
        self.approved: list[int] = []

    def approve_pr(self, pr_number: int, body: str, *, gh_token: str | None = None) -> None:
        self.approved.append(pr_number)

    def request_changes(self, pr_number: int, body: str, *, gh_token: str | None = None) -> None:
        pass

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
        "mastercoder_automation.orchestrator.repo_ops.git_checkout_main_pull",
        lambda *_a, **_k: "ok",
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_create_branch",
        lambda *_a, **_k: "ok",
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_changed_files_against_default",
        lambda *_a, **_k: changed_files or ["tests/test_req02.py", "src/mastercoder/config.py"],
    )
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_commits_ahead_of_default",
        lambda *_a, **_k: commits_ahead,
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
    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_checkout_main_pull",
        lambda *_a, **_k: "ok",
    )

    def fail_create_branch(*_a, **_k):
        raise RuntimeError("checkout blocked")

    monkeypatch.setattr(
        "mastercoder_automation.orchestrator.repo_ops.git_create_branch",
        fail_create_branch,
    )

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once(req_id="REQ-02")
    req = new_state.requirements[0]
    assert req.state == ReqState.FIXING
    assert "准备开发分支失败" in (req.last_error or "")
