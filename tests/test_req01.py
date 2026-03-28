"""Test REQ-01: MasterCoder REPL entry point."""

import subprocess
import sys

import pytest


def test_startup_and_exit():
    """Test program startup, welcome message, and /exit command."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "mastercoder.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    output, _ = proc.communicate(input="/exit\n", timeout=5)

    assert "MasterCoder v0.1.0" in output
    assert "Type /help for available commands, /exit to quit." in output
    assert "Goodbye!" in output
    assert proc.returncode == 0


def test_empty_input_skip():
    """Test that empty input is skipped without output."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "mastercoder.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    output, _ = proc.communicate(input="\n/exit\n", timeout=5)

    assert proc.returncode == 0
    assert "Goodbye!" in output


def test_echo_input():
    """Test that user input is echoed back."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "mastercoder.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    test_text = "hello world"
    output, _ = proc.communicate(input=f"{test_text}\n/exit\n", timeout=5)

    assert test_text in output
    assert proc.returncode == 0


def test_keyboard_interrupt_exits_gracefully(monkeypatch, capsys):
    """模拟 Ctrl+C：input 抛出 KeyboardInterrupt 时应打印 Goodbye 并以 0 退出。"""

    def interrupt_input(prompt: str = "") -> str:
        raise KeyboardInterrupt()

    monkeypatch.setattr("builtins.input", interrupt_input)
    from mastercoder import main as mc

    with pytest.raises(SystemExit) as exc_info:
        mc.main()
    assert exc_info.value.code == 0
    assert "Goodbye!" in capsys.readouterr().out
