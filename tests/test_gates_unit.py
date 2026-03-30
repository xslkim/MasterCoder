"""gates 子进程超时分支。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mastercoder_automation import gates


def test_run_step_timeout_returns_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def timeout_run(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=1)

    monkeypatch.setattr(gates.subprocess, "run", timeout_run)
    r = gates.run_quality_gates(50, cwd=tmp_path)
    assert r.passed is False
    assert "超时" in r.output or "timeout" in r.output.lower()


def test_run_quality_gates_uses_compact_pytest_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check, cwd, timeout):
        calls.append(cmd)

        class Proc:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        return Proc()

    monkeypatch.setattr(gates.subprocess, "run", fake_run)

    result = gates.run_quality_gates(50, cwd=tmp_path)

    assert result.passed is True
    pytest_cmd = calls[2]
    assert pytest_cmd[:3] == ["pytest", "tests/", "-q"]
    assert "-v" not in pytest_cmd
