from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# 防止子进程无限挂起（pytest/ruff 异常时）
_GATE_STEP_TIMEOUT_SEC = 900


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=_GATE_STEP_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as e:
        return (
            -1,
            "",
            f"命令超时（>{_GATE_STEP_TIMEOUT_SEC}s）：{' '.join(cmd)}\n{e}",
        )
    return proc.returncode, proc.stdout, proc.stderr


@dataclass
class GateResult:
    passed: bool
    output: str


def run_quality_gates(coverage_min: int, cwd: Path | None = None) -> GateResult:
    root = Path.cwd() if cwd is None else cwd
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    steps = [
        ["ruff", "format", "src/", "tests/"],
        ["ruff", "check", "src/", "tests/"],
        [
            "pytest",
            "tests/",
            "-q",
            "--tb=short",
            "--cov=mastercoder_automation",
            "--cov-report=term",
            "--cov-report=xml:reports/coverage.xml",
            f"--cov-fail-under={coverage_min}",
            "--junitxml=reports/junit.xml",
        ],
    ]
    logs: list[str] = []
    for step in steps:
        code, out, err = _run(step, cwd=root)
        logs.append(f"$ {' '.join(step)}\n{out}\n{err}")
        if code != 0:
            return GateResult(False, "\n".join(logs))
    return GateResult(True, "\n".join(logs))
