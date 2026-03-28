"""CLI 冒烟：Typer 入口与 init-state / 无效 req-id。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mastercoder_automation.cli import app


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
