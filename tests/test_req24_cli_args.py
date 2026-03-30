"""REQ-24: command-line parsing and startup options."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from mastercoder.cli import (
    API_KEY_ERROR,
    build_initial_messages,
    create_config_from_args,
    get_version,
    is_non_interactive_mode,
    parse_args,
    run_non_interactive_mode,
)


class _FakeTTY(StringIO):
    def isatty(self) -> bool:
        return True


class _FakePipe(StringIO):
    def isatty(self) -> bool:
        return False


def test_parse_all_supported_arguments() -> None:
    args = parse_args(
        [
            "-m",
            "deepseek-chat",
            "--api-key",
            "sk-test123",
            "--api-url",
            "https://example.invalid/v1",
            "-y",
            "--resume",
            "session-123",
            "--no-color",
        ]
    )

    assert args.model == "deepseek-chat"
    assert args.api_key == "sk-test123"
    assert args.api_url == "https://example.invalid/v1"
    assert args.auto_approve is True
    assert args.resume == "session-123"
    assert args.no_color is True


def test_resume_without_session_id_uses_empty_string() -> None:
    args = parse_args(["--resume"])
    assert args.resume == ""


def test_version_flag_prints_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])

    assert exc_info.value.code == 0
    assert get_version() in capsys.readouterr().out


def test_help_mentions_api_key_visibility(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "--api-key" in output
    assert "MASTERCODER_API_KEY" in output


def test_cli_overrides_env_and_project_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"model": "file-model", "api_key": "file-key"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("MASTERCODER_MODEL", "env-model")

    config = create_config_from_args(
        parse_args(["-m", "cli-model"]),
        working_dir=tmp_path,
        stdin=_FakeTTY(),
    )

    assert config.model == "cli-model"
    assert config.api_key == "file-key"


def test_non_interactive_mode_enables_auto_approve_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = create_config_from_args(parse_args([]), working_dir=tmp_path, stdin=_FakePipe())

    assert config.auto_approve is True


def test_is_non_interactive_mode_uses_stream_tty_state() -> None:
    assert is_non_interactive_mode(_FakePipe()) is True
    assert is_non_interactive_mode(_FakeTTY()) is False


def test_build_initial_messages_appends_custom_system_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"api_key": "sk-test", "system_prompt": "Be precise."}),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = create_config_from_args(parse_args([]), working_dir=tmp_path, stdin=_FakeTTY())
    messages = build_initial_messages(config, "hello")

    assert messages[0]["role"] == "system"
    assert "Be precise." in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "hello"}


def test_run_non_interactive_mode_streams_plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    config = create_config_from_args(
        parse_args(["--api-key", "sk-test"]),
        stdin=_FakePipe("hello"),
    )
    output = _FakePipe()

    class _Client:
        def __init__(self, cfg):
            self.cfg = cfg

        def stream_chat(self, messages):
            assert messages[-1]["content"] == "hello"
            yield "Hello"
            yield " world"

    monkeypatch.setattr("mastercoder.cli.APIClient", _Client)

    exit_code = run_non_interactive_mode(config, stdin=_FakePipe("hello"), stdout=output)

    assert exit_code == 0
    assert output.getvalue() == "Hello world\n"
    assert "\033[" not in output.getvalue()


def test_run_non_interactive_mode_without_api_key_returns_error() -> None:
    config = create_config_from_args(parse_args([]), stdin=_FakePipe("hello"))
    output = _FakePipe()

    exit_code = run_non_interactive_mode(config, stdin=_FakePipe("hello"), stdout=output)

    assert exit_code == 1
    assert output.getvalue() == API_KEY_ERROR + "\n"


def test_main_uses_conversation_loop_when_api_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _Loop:
        def __init__(self, config, enable_color=True):
            captured["model"] = config.model
            captured["enable_color"] = enable_color

        def run(self) -> None:
            captured["ran"] = True

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: False)
    monkeypatch.setattr("mastercoder.main.ConversationLoop", _Loop)

    from mastercoder import main as mc

    mc.main(["-m", "deepseek-chat", "--api-key", "sk-test", "--no-color"])

    assert captured == {
        "model": "deepseek-chat",
        "enable_color": False,
        "ran": True,
    }


def test_main_uses_non_interactive_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: True)

    def fake_run_non_interactive(config) -> int:
        captured["model"] = config.model
        return 0

    monkeypatch.setattr("mastercoder.main.run_non_interactive_mode", fake_run_non_interactive)

    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main(["-m", "deepseek-chat"])

    assert exc_info.value.code == 0
    assert captured["model"] == "deepseek-chat"