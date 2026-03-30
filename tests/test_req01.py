"""Test REQ-01: MasterCoder REPL entry point."""

import pytest


def test_startup_and_exit(monkeypatch, capsys):
    """Test program startup, welcome message, and /exit command."""
    inputs = iter(["/exit"])

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: False)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main([])

    output = capsys.readouterr().out
    assert "MasterCoder v0.1.0" in output
    assert "Type /help for available commands, /exit to quit." in output
    assert "Goodbye!" in output
    assert exc_info.value.code == 0


def test_empty_input_skip(monkeypatch, capsys):
    """Test that empty input is skipped without output."""
    inputs = iter(["", "/exit"])

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: False)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main([])

    output = capsys.readouterr().out
    assert "Goodbye!" in output
    assert exc_info.value.code == 0


def test_echo_input(monkeypatch, capsys):
    """Test that user input is echoed back."""
    test_text = "hello world"
    inputs = iter([test_text, "/exit"])

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: False)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main([])

    output = capsys.readouterr().out
    assert test_text in output
    assert exc_info.value.code == 0


def test_keyboard_interrupt_exits_gracefully(monkeypatch, capsys):
    """模拟 Ctrl+C：input 抛出 KeyboardInterrupt 时应打印 Goodbye 并以 0 退出。"""

    def interrupt_input(prompt: str = "") -> str:
        raise KeyboardInterrupt()

    monkeypatch.setattr("mastercoder.main.is_non_interactive_mode", lambda: False)
    monkeypatch.setattr("builtins.input", interrupt_input)
    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main([])
    assert exc_info.value.code == 0
    assert "Goodbye!" in capsys.readouterr().out
