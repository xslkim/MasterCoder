"""Unit tests for REQ-18 slash command system."""

import pytest


def test_help_output_contains_all_commands():
    """Test that /help output includes all available commands."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    output = handler.execute("/help")

    assert "/help" in output
    assert "/clear" in output
    assert "/model" in output
    assert "/config" in output
    assert "/exit" in output
    assert "Available commands:" in output


def test_clear_leaves_only_system_message():
    """Test that /clear clears conversation history, leaving only system message."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    handler.conversation_history = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

    output = handler.execute("/clear")

    assert output == "Conversation cleared."
    assert len(handler.conversation_history) == 1
    assert handler.conversation_history[0]["role"] == "system"


def test_model_no_args_shows_current():
    """Test that /model without args shows current model."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    handler.config = {"model": "gpt-4o"}

    output = handler.execute("/model")

    assert "gpt-4o" in output


def test_model_with_args_switches():
    """Test that /model with args switches model."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    handler.config = {"model": "gpt-4o"}

    output = handler.execute("/model deepseek-chat")

    assert "Model switched to deepseek-chat" in output
    assert handler.config["model"] == "deepseek-chat"


def test_config_output_masks_api_key():
    """Test that /config output shows all config items with masked api_key."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    handler.config = {
        "api_base_url": "https://api.openai.com/v1",
        "api_key": "sk-test1234abcd",
        "model": "gpt-4o",
        "max_tokens": 4096,
        "temperature": 0.0,
        "auto_approve": False,
        "system_prompt": "",
    }

    output = handler.execute("/config")

    assert "api_base_url:" in output
    assert "api_key:" in output
    assert "sk-****abcd" in output
    assert "model:" in output
    assert "max_tokens:" in output
    assert "temperature:" in output
    assert "auto_approve:" in output
    assert "system_prompt:" in output
    # Ensure full key is NOT visible
    assert "sk-test1234abcd" not in output


def test_exit_command():
    """Test that /exit command exits the program with code 0."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()

    with pytest.raises(SystemExit) as exc_info:
        handler.execute("/exit")

    assert exc_info.value.code == 0


def test_unknown_command_shows_error():
    """Test that unknown command shows appropriate error message."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()
    output = handler.execute("/unknown")

    assert "Unknown command: /unknown" in output
    assert "Type /help for available commands" in output


def test_command_case_insensitive():
    """Test that command parsing is case-insensitive."""
    from src.slash_commands import SlashCommandHandler

    handler = SlashCommandHandler()

    output_upper = handler.execute("/HELP")
    assert "Available commands:" in output_upper

    output_mixed = handler.execute("/HeLp")
    assert "Available commands:" in output_mixed
