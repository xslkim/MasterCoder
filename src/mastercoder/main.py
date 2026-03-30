"""MasterCoder product entrypoint."""

import sys

from mastercoder.cli import (
    create_config_from_args,
    is_non_interactive_mode,
    parse_args,
    run_non_interactive_mode,
)
from mastercoder.conversation import ConversationLoop
from mastercoder.git_info import build_prompt, get_git_info


def _run_basic_repl() -> None:
    """Run the original local echo REPL used before API-backed chat is configured."""
    get_git_info()

    print("MasterCoder v0.1.0")
    print("Type /help for available commands, /exit to quit.")

    try:
        while True:
            try:
                user_input = input(build_prompt())

                if not user_input.strip():
                    continue

                if user_input.strip() == "/exit":
                    print("Goodbye!")
                    sys.exit(0)

                print(user_input)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                sys.exit(0)
    except EOFError:
        print("\nGoodbye!")
        sys.exit(0)


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to interactive or non-interactive mode."""
    args = parse_args(argv)
    config = create_config_from_args(args)

    if is_non_interactive_mode():
        sys.exit(run_non_interactive_mode(config))

    if config.api_key:
        ConversationLoop(config, enable_color=not args.no_color).run()
        return

    _run_basic_repl()


if __name__ == "__main__":
    main()
