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
