"""Command-line parsing and startup helpers for REQ-24."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from mastercoder.api_client import APIClient, APIError
from mastercoder.config import Config
from mastercoder.conversation import BUILTIN_SYSTEM_PROMPT


VERSION = "0.1.0"
API_KEY_ERROR = (
    "Error: API key not configured. Set MASTERCODER_API_KEY or add api_key "
    "to ~/.mastercoder/config.json"
)


@dataclass(slots=True)
class CLIArgs:
    """Parsed command-line arguments."""

    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None
    auto_approve: bool = False
    resume: str | None = None
    version: bool = False
    no_color: bool = False


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the product CLI."""
    parser = argparse.ArgumentParser(
        prog="mastercoder",
        description="MasterCoder - AI-powered coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  mastercoder                    启动交互式会话\n"
            "  mastercoder -m deepseek-chat   使用 deepseek-chat 模型\n"
            "  mastercoder -y                 启用自动批准模式\n"
            "  mastercoder --version          显示版本号\n"
            "  echo \"hello\" | mastercoder     非交互模式（管道输入）\n\n"
            "Security Note:\n"
            "  --api-key 参数在进程列表中可见，建议使用环境变量 MASTERCODER_API_KEY"
        ),
    )
    parser.add_argument(
        "-m", "--model", metavar="NAME", help="指定模型名称（覆盖配置文件和环境变量）"
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        help=(
            "指定 API Key（覆盖配置文件和环境变量）\n"
            "警告：此参数在进程列表中可见，建议使用环境变量 MASTERCODER_API_KEY"
        ),
    )
    parser.add_argument("--api-url", metavar="URL", help="指定 API Base URL")
    parser.add_argument("-y", "--auto-approve", action="store_true", help="启用自动批准模式")
    parser.add_argument(
        "-r",
        "--resume",
        nargs="?",
        const="",
        default=None,
        metavar="SESSION_ID",
        help="恢复会话，可选指定 session_id",
    )
    parser.add_argument("-v", "--version", action="store_true", help="打印版本号并退出")
    parser.add_argument("--no-color", action="store_true", help="禁用终端颜色输出")
    return parser


def parse_args(args: list[str] | None = None) -> CLIArgs:
    """Parse CLI arguments."""
    parsed = build_parser().parse_args(args)
    result = CLIArgs(
        model=parsed.model,
        api_key=parsed.api_key,
        api_url=parsed.api_url,
        auto_approve=parsed.auto_approve,
        resume=parsed.resume,
        version=parsed.version,
        no_color=parsed.no_color,
    )
    if result.version:
        print(get_version())
        raise SystemExit(0)
    return result


def get_version() -> str:
    """Return the user-visible version string."""
    return f"MasterCoder v{VERSION}"


def is_non_interactive_mode(stdin: TextIO | None = None) -> bool:
    """Return whether input is being piped instead of typed in a TTY."""
    stream = stdin if stdin is not None else sys.stdin
    return not stream.isatty()


def create_config_from_args(
    args: CLIArgs,
    working_dir: Path | None = None,
    stdin: TextIO | None = None,
) -> Config:
    """Load config and apply CLI overrides with the documented precedence."""
    config = Config(working_dir=working_dir)
    cli_overrides: dict[str, Any] = {}

    if args.model is not None:
        cli_overrides["model"] = args.model
    if args.api_key is not None:
        cli_overrides["api_key"] = args.api_key
    if args.api_url is not None:
        cli_overrides["api_base_url"] = args.api_url
    if args.auto_approve:
        cli_overrides["auto_approve"] = True
    if is_non_interactive_mode(stdin) and "auto_approve" not in cli_overrides:
        cli_overrides["auto_approve"] = True

    config._config.update(cli_overrides)
    return config


def build_initial_messages(config: Config, user_input: str) -> list[dict[str, str]]:
    """Build a one-shot request payload for non-interactive mode."""
    system_content = BUILTIN_SYSTEM_PROMPT
    if config.system_prompt:
        system_content += " " + config.system_prompt
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_input},
    ]


def run_non_interactive_mode(
    config: Config,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run a single non-interactive request from stdin and print plain text output."""
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout

    try:
        user_input = input_stream.read()
    except KeyboardInterrupt:
        return 0

    if not user_input.strip():
        return 0

    if not config.api_key:
        output_stream.write(API_KEY_ERROR + "\n")
        output_stream.flush()
        return 1

    try:
        client = APIClient(config)
        for chunk in client.stream_chat(build_initial_messages(config, user_input)):
            output_stream.write(chunk)
            output_stream.flush()
        output_stream.write("\n")
        output_stream.flush()
        return 0
    except APIError as error:
        output_stream.write(f"Error: {error}\n")
        output_stream.flush()
        return 1


if __name__ == "__main__":
    main()
