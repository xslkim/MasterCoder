"""MasterCoder product entrypoint."""

import sys

from mastercoder.cli import create_config_from_args, is_non_interactive_mode, parse_args, run_non_interactive_mode
from mastercoder.conversation import ConversationLoop


def _run_basic_repl() -> None:
    """Run the original local echo REPL used before API-backed chat is configured."""
    print("MasterCoder v0.1.0")
    print("Type /help for available commands, /exit to quit.")

    try:
        while True:
            try:
                # 显示提示符并读取用户输入
                user_input = input("> ")

                # 空行跳过
                if not user_input.strip():
                    continue

                # /exit 命令退出
                if user_input.strip() == "/exit":
                    print("Goodbye!")
                    sys.exit(0)

                # 暂时原样回显（后续需求接入 AI）
                print(user_input)

            except KeyboardInterrupt:
                # Ctrl+C 处理
                print("\nGoodbye!")
                sys.exit(0)
    except EOFError:
        # 处理 EOF（例如管道输入结束）
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
