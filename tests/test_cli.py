"""CLI 冒烟：Typer 入口与 init-state / 无效 req-id。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mastercoder_automation.cli import app
from mastercoder_automation.models import PipelineState, ReqRecord, ReqState
from mastercoder_automation.state_store import StateStore


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_init_state_writes_state_file(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "state").mkdir()
    shutil.copy(
        project_root / "state/req-status.example.json", tmp_path / "state/req-status.example.json"
    )
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "my-state.json"))

    runner = CliRunner()
    result = runner.invoke(app, ["init-state"])
    assert result.exit_code == 0
    assert (tmp_path / "my-state.json").is_file()
    data = json.loads((tmp_path / "my-state.json").read_text(encoding="utf-8"))
    assert "requirements" in data


def test_init_state_missing_template_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "empty").mkdir()
    monkeypatch.setenv("REPO_ROOT", str(tmp_path / "empty"))
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "out.json"))

    runner = CliRunner()
    result = runner.invoke(app, ["init-state"])
    assert result.exit_code == 1


def test_run_once_unknown_req_id_exits_1(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "state").mkdir()
    shutil.copy(project_root / "state/req-status.example.json", tmp_path / "state/req-status.json")
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FILE", "state/req-status.json")

    runner = CliRunner()
    result = runner.invoke(app, ["run-once", "--req-id", "REQ-999"])
    assert result.exit_code == 1


def test_run_all_unknown_req_id_exits_1(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "state").mkdir()
    shutil.copy(project_root / "state/req-status.example.json", tmp_path / "state/req-status.json")
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FILE", "state/req-status.json")

    runner = CliRunner()
    result = runner.invoke(app, ["run-all", "--req-id", "REQ-999"])
    assert result.exit_code == 1


def test_run_all_req_id_auto_refreshes_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Rec:
        def __init__(self, req_id: str, state: str):
            self.req_id = req_id
            self.state = state

    class _State:
        def __init__(self, requirements):
            self.requirements = requirements

        def model_dump(self):
            return {"requirements": [{"req_id": r.req_id, "state": r.state.value} for r in self.requirements]}

    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            self._refresh_calls = 0
            self.run_once_calls: list[str | None] = []

        def refresh_ready_only(self):
            self._refresh_calls += 1
            if self._refresh_calls == 1:
                return _State([_Rec("REQ-05", ReqState.READY)])
            return _State([_Rec("REQ-05", ReqState.DONE)])

        def run_once(self, req_id=None):
            self.run_once_calls.append(req_id)
            return _State([_Rec("REQ-05", ReqState.DONE)])

    class _FakeStore:
        def __init__(self, *args, **kwargs):
            pass

        def load(self):
            return _State([_Rec("REQ-05", ReqState.DONE)])

    monkeypatch.setattr("mastercoder_automation.cli.check_automation_prerequisites", lambda: None)
    monkeypatch.setattr("mastercoder_automation.cli.load_settings", lambda: type("S", (), {"state_file": Path("."), "github_repo": "x/y"})())
    monkeypatch.setattr("mastercoder_automation.cli.GhClient", lambda *a, **k: object())
    monkeypatch.setattr("mastercoder_automation.cli.StateStore", _FakeStore)
    monkeypatch.setattr("mastercoder_automation.cli.Orchestrator", _FakeOrchestrator)

    runner = CliRunner()
    result = runner.invoke(app, ["run-all", "--req-id", "REQ-05", "--max-rounds", "2"])
    assert result.exit_code == 0
    assert "第 1/2 轮：run-once --req-id REQ-05" in result.output
    assert "当前=READY" in result.output


def test_run_all_auto_refreshes_global_work_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Rec:
        def __init__(self, req_id: str, state: str):
            self.req_id = req_id
            self.state = state

    class _State:
        def __init__(self, requirements):
            self.requirements = requirements

        def model_dump(self):
            return {"requirements": [{"req_id": r.req_id, "state": r.state.value} for r in self.requirements]}

    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            self._refresh_calls = 0

        def refresh_ready_only(self):
            self._refresh_calls += 1
            if self._refresh_calls == 1:
                return _State([_Rec("REQ-05", ReqState.READY)])
            return _State([_Rec("REQ-05", ReqState.DONE)])

        def run_once(self, req_id=None):
            return _State([_Rec("REQ-05", ReqState.DONE)])

    class _FakeStore:
        def __init__(self, *args, **kwargs):
            pass

        def load(self):
            return _State([_Rec("REQ-05", ReqState.DONE)])

    monkeypatch.setattr("mastercoder_automation.cli.check_automation_prerequisites", lambda: None)
    monkeypatch.setattr("mastercoder_automation.cli.load_settings", lambda: type("S", (), {"state_file": Path("."), "github_repo": "x/y"})())
    monkeypatch.setattr("mastercoder_automation.cli.GhClient", lambda *a, **k: object())
    monkeypatch.setattr("mastercoder_automation.cli.StateStore", _FakeStore)
    monkeypatch.setattr("mastercoder_automation.cli.Orchestrator", _FakeOrchestrator)

    runner = CliRunner()
    result = runner.invoke(app, ["run-all", "--max-rounds", "2"])
    assert result.exit_code == 0
    assert "第 1/2 轮：run-once（READY/FIXING：" in result.output


def test_unblock_cmd_sets_ready_and_clears_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "st.json"
    st = PipelineState(
        requirements=[
            ReqRecord(
                req_id="REQ-01",
                title="t",
                state=ReqState.BLOCKED,
                retries=4,
                last_error="was blocked",
            )
        ]
    )
    StateStore(state_path).save(st)
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FILE", str(state_path))

    runner = CliRunner()
    result = runner.invoke(app, ["unblock", "--req-id", "REQ-01"])
    assert result.exit_code == 0
    assert "已解锁 REQ-01" in result.output
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["requirements"][0]["state"] == "READY"
    assert data["requirements"][0]["retries"] == 0
    assert data["requirements"][0]["last_error"] is None


def test_unblock_unknown_req_id_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "st.json"
    StateStore(state_path).save(
        PipelineState(requirements=[ReqRecord(req_id="REQ-01", title="t", state=ReqState.DONE)])
    )
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FILE", str(state_path))

    runner = CliRunner()
    result = runner.invoke(app, ["unblock", "--req-id", "REQ-999"])
    assert result.exit_code == 1
