import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _skip_cli_preflight_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试环境未必安装 gh；CLI 用例在预检前会失败，故统一跳过。"""
    monkeypatch.setattr(
        "mastercoder_automation.cli.check_automation_prerequisites",
        lambda: None,
    )
