"""preflight 本机命令检查。"""

from __future__ import annotations

import pytest

from mastercoder_automation.preflight import check_automation_prerequisites


def test_preflight_fails_when_git_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "git":
            return None
        return f"/bin/{name}"

    monkeypatch.setattr("mastercoder_automation.preflight.which", fake_which)
    with pytest.raises(RuntimeError, match="git"):
        check_automation_prerequisites()


def test_preflight_fails_when_gh_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "gh":
            return None
        return f"/bin/{name}"

    monkeypatch.setattr("mastercoder_automation.preflight.which", fake_which)
    with pytest.raises(RuntimeError, match="gh"):
        check_automation_prerequisites()


def test_preflight_ok_when_git_and_gh_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mastercoder_automation.preflight.which", lambda _n: "/bin/x")
    check_automation_prerequisites()
