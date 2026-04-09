"""Slash command system for REQ-18.

Implements slash command parsing and execution mechanism.
Commands are processed when user input starts with '/'.
"""

import sys
from typing import Dict, List, Optional, Any


class SlashCommandHandler:
    """Handles slash command parsing and execution."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize slash command handler.

        Args:
            config: Configuration dictionary with api_key, model, etc.
        """
        self.config = config or {}
        self.conversation_history: List[Dict[str, str]] = []

    def execute(self, user_input: str) -> str:
        """Parse and execute a slash command.

        Args:
            user_input: User input string starting with '/'

        Returns:
            Output string from command execution
        """
        if not user_input.startswith("/"):
            raise ValueError("Input must start with '/' to be a slash command")

        # Parse command and args
        parts = user_input.strip().split(maxsplit=1)
        command = parts[0].lower()  # Case-insensitive
        args = parts[1] if len(parts) > 1 else ""

        # Route to command handlers
        if command == "/help":
            return self._cmd_help()
        elif command == "/clear":
            return self._cmd_clear()
        elif command == "/model":
            return self._cmd_model(args)
        elif command == "/config":
            return self._cmd_config()
        elif command == "/exit":
            return self._cmd_exit()
        else:
            return f"Unknown command: {command}. Type /help for available commands."

    def _cmd_help(self) -> str:
        """Show available commands and their descriptions."""
        return """Available commands:
  /help           Show this help message
  /clear          Clear conversation history
  /model [name]   Show or switch the current model
  /config         Show current configuration
  /exit           Exit MasterCoder"""

    def _cmd_clear(self) -> str:
        """Clear conversation history, keeping only system message."""
        # Keep only system messages
        self.conversation_history = [
            msg for msg in self.conversation_history if msg.get("role") == "system"
        ]
        return "Conversation cleared."

    def _cmd_model(self, args: str) -> str:
        """Show or switch the current model.

        Args:
            args: Optional model name to switch to

        Returns:
            Current model name or confirmation of switch
        """
        if not args:
            # Show current model
            current_model = self.config.get("model", "unknown")
            return f"Current model: {current_model}"
        else:
            # Switch model
            model_name = args.strip()
            self.config["model"] = model_name
            return f"Model switched to {model_name}"

    def _cmd_config(self) -> str:
        """Show current configuration with masked api_key."""
        lines = ["Current configuration:"]

        # api_base_url
        api_base_url = self.config.get("api_base_url", "")
        lines.append(f"  api_base_url:  {api_base_url}")

        # api_key (masked)
        api_key = self.config.get("api_key", "")
        masked_key = self._mask_api_key(api_key)
        lines.append(f"  api_key:       {masked_key}")

        # model
        model = self.config.get("model", "")
        lines.append(f"  model:         {model}")

        # max_tokens
        max_tokens = self.config.get("max_tokens", 4096)
        lines.append(f"  max_tokens:    {max_tokens}")

        # temperature
        temperature = self.config.get("temperature", 0.0)
        lines.append(f"  temperature:   {temperature}")

        # auto_approve
        auto_approve = self.config.get("auto_approve", False)
        lines.append(f"  auto_approve:  {auto_approve}")

        # system_prompt
        system_prompt = self.config.get("system_prompt", "")
        if not system_prompt:
            prompt_display = "(default)"
        elif len(system_prompt) > 50:
            prompt_display = system_prompt[:50] + "..."
        else:
            prompt_display = system_prompt
        lines.append(f"  system_prompt: {prompt_display}")

        return "\n".join(lines)

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key to show only first 3 and last 4 characters.

        Args:
            api_key: The API key to mask

        Returns:
            Masked API key string
        """
        if not api_key:
            return ""

        if len(api_key) <= 7:
            # Key too short to mask properly
            return "****"

        prefix = api_key[:3]
        suffix = api_key[-4:]
        return f"{prefix}****{suffix}"

    def _cmd_exit(self) -> str:
        """Exit the program.

        Raises:
            SystemExit: Always exits with code 0
        """
        print("Goodbye!")
        sys.exit(0)


def is_slash_command(user_input: str) -> bool:
    """Check if user input is a slash command.

    Args:
        user_input: User input string

    Returns:
        True if input starts with '/', False otherwise
    """
    return user_input.strip().startswith("/")
