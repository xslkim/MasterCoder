"""Test REQ-01: MasterCoder REPL entry point."""

import subprocess
import sys


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


def test_ctrl_c_exit():
    """Test that Ctrl+C exits the program gracefully."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "mastercoder.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Send SIGINT (Ctrl+C)
    proc.send_signal(subprocess.signal.SIGINT)
    output, _ = proc.communicate(timeout=5)
    
    assert "Goodbye!" in output
    assert proc.returncode == 0
