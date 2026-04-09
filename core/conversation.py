"""主对话循环 - 串联配置、API 客户端和消息管理器。"""

import sys
from pathlib import Path

from mastercoder.api_client import APIClient, APIError
from mastercoder.config import Config, get_config
from mastercoder.context_manager import build_enhanced_message, install_file_reference_completion
from mastercoder.git_info import build_prompt, get_git_info
from mastercoder.message_manager import MessageManager
from mastercoder.system_prompt import build_system_prompt


class ConversationLoop:
    """对话循环类，处理用户与 AI 的交互。"""

    def __init__(self, config: Config, enable_color: bool = True) -> None:
        """初始化对话循环。

        Args:
            config: 配置对象
            enable_color: 是否启用 ANSI 颜色输出
        """
        self._config = config
        self._working_dir = Path(getattr(config, "_working_dir", Path.cwd())).resolve()
        self._enable_color = enable_color
        self._message_manager = MessageManager()
        self._api_client = APIClient(config)
        self._initialize_system_message()

    def _initialize_system_message(self) -> None:
        """初始化系统消息，包括内置消息和自定义 prompt。"""
        system_content = build_system_prompt(
            Path.cwd(),
            self._config.system_prompt,
            git_info=get_git_info(),
        )
        self._message_manager.add_message("system", system_content)

    def run(self) -> None:
        """运行对话循环。"""
        if not self._config.api_key:
            print(
                "Error: API key not configured. Set MASTERCODER_API_KEY or add api_key to ~/.mastercoder/config.json"
            )
            sys.exit(1)

        print("MasterCoder - AI Programming Assistant")
        print("Type your message and press Enter to chat. Press Ctrl+C to exit.")
        print()
        install_file_reference_completion(str(self._working_dir))

        while True:
            try:
                user_input = input(build_prompt(self._config.model))

                if not user_input.strip():
                    continue

                self._handle_user_input(user_input)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                sys.exit(0)
            except EOFError:
                print("\nGoodbye!")
                sys.exit(0)

    def _handle_user_input(self, user_input: str) -> None:
        """处理用户输入。"""
        user_input = build_enhanced_message(user_input, str(self._working_dir))
        self._message_manager.add_message("user", user_input)

        messages = self._message_manager.prepare_messages()

        if self._message_manager.was_truncated():
            print("[Context truncated: earliest messages removed]")
            self._message_manager.clear_truncation_flag()

        try:
            self._stream_and_process_response(messages)
        except APIError as error:
            self._handle_api_error(error)
        except KeyboardInterrupt:
            raise

    def _stream_and_process_response(self, messages: list[dict[str, str]]) -> None:
        """流式调用 API 并处理响应。"""
        full_response = ""
        try:
            for chunk in self._api_client.stream_chat(messages):
                print(chunk, end="", flush=True)
                full_response += chunk

            print()
            print()

            if full_response:
                self._message_manager.add_message("assistant", full_response)

        except KeyboardInterrupt:
            print("\n[Interrupted]")
            print()

            if full_response:
                self._message_manager.add_message("assistant", full_response)

    def _handle_api_error(self, error: APIError) -> None:
        """处理 API 错误。"""
        error_msg = f"Error: {str(error)}"

        if self._enable_color and sys.stdout.isatty():
            print(f"\033[31m{error_msg}\033[0m")
        else:
            print(error_msg)

        print()


def main() -> None:
    """主函数入口。"""
    config = get_config()
    conversation = ConversationLoop(config)
    conversation.run()


if __name__ == "__main__":
    main()
