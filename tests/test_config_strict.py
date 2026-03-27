from mastercoder_automation.config import load_settings


def test_strict_human_flags_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AUTOMATION_STRICT_HUMAN_REVIEW", "true")
    monkeypatch.setenv("AUTOMATION_STRICT_HUMAN_QA", "1")
    monkeypatch.setenv("AUTOMATION_HUMAN_POLL_INTERVAL_SEC", "2")
    monkeypatch.setenv("AUTOMATION_HUMAN_POLL_TIMEOUT_SEC", "99")
    s = load_settings()
    assert s.strict_human_review is True
    assert s.strict_human_qa is True
    assert s.human_poll_interval_sec == 2
    assert s.human_poll_timeout_sec == 99
