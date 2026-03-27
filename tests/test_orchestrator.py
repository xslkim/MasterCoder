from pathlib import Path

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


def test_ready_transitions_when_dependencies_done(monkeypatch, tmp_path: Path) -> None:
    state = PipelineState(
        requirements=[
            ReqRecord(req_id="REQ-01", title="base", state=ReqState.DONE),
            ReqRecord(req_id="REQ-02", title="child", blocked_by=["REQ-01"], state=ReqState.PENDING),
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

    orchestrator = Orchestrator(settings=settings, store=StateStore(state_file), gh=DummyGh())
    new_state = orchestrator.run_once()
    req = new_state.requirements[0]
    assert req.state == ReqState.BLOCKED
    assert req.last_error is not None

