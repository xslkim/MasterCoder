"""主对话循环 - 串联配置、API 客户端和消息管理器。"""

import sys
from pathlib import Path

from mastercoder.api_client import APIClient, APIError
from mastercoder.config import Config, get_config
from mastercoder.context_manager import build_enhanced_message, install_file_reference_completion
from mastercoder.message_manager import MessageManager


# 内置 system 消息
BUILTIN_SYSTEM_PROMPT = """You are MasterCoder, an AI programming assistant. You help users with software development tasks including writing code, debugging, refactoring, and explaining code. You have access to tools that can read files, write files, edit files, search files, and run commands on the user's local machine. Always be helpful, concise, and accurate."""


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
        system_content = BUILTIN_SYSTEM_PROMPT

        # 追加自定义 system_prompt（如果非空）
        if self._config.system_prompt:
            system_content += " " + self._config.system_prompt

        self._message_manager.add_message("system", system_content)

    def run(self) -> None:
        """运行对话循环。"""
        # 检查 API key
        if not self._config.api_key:
            print(
                "Error: API key not configured. Set MASTERCODER_API_KEY or add api_key to ~/.mastercoder/config.json"
            )
            sys.exit(1)

        # 显示欢迎信息和提示符
        print("MasterCoder - AI Programming Assistant")
        print("Type your message and press Enter to chat. Press Ctrl+C to exit.")
        print()
        install_file_reference_completion(str(self._working_dir))

        while True:
            try:
                # 显示提示符
                print("> ", end="", flush=True)

                # 读取用户输入
                user_input = input()

                if not user_input.strip():
                    continue

                # 处理用户输入
                self._handle_user_input(user_input)

            except KeyboardInterrupt:
                # Ctrl+C 退出程序
                print("\nGoodbye!")
                sys.exit(0)
            except EOFError:
                # Ctrl+D 退出程序
                print("\nGoodbye!")
                sys.exit(0)

    def _handle_user_input(self, user_input: str) -> None:
        """处理用户输入。

        Args:
            user_input: 用户输入文本
        """
        user_input = build_enhanced_message(user_input, str(self._working_dir))

        # 添加用户消息
        self._message_manager.add_message("user", user_input)

        # 准备消息（包括截断处理）
        messages = self._message_manager.prepare_messages()

        # 检查是否发生截断
        if self._message_manager.was_truncated():
            print("[Context truncated: earliest messages removed]")
            self._message_manager.clear_truncation_flag()

        # 调用 API 并处理响应
        try:
            self._stream_and_process_response(messages)
        except APIError as e:
            # API 错误处理
            self._handle_api_error(e)
        except KeyboardInterrupt:
            # 流式输出期间的 Ctrl+C 在 _stream_and_process_response 中处理
            raise

    def _stream_and_process_response(self, messages: list[dict[str, str]]) -> None:
        """流式调用 API 并处理响应。

        Args:
            messages: 消息列表
        """
        full_response = ""
        try:
            # 流式调用 API
            for chunk in self._api_client.stream_chat(messages):
                # 实时打印片段（无换行缓冲）
                print(chunk, end="", flush=True)
                full_response += chunk

            # 流结束后，打印空行
            print()
            print()

            # 添加完整回复到消息管理器
            if full_response:
                self._message_manager.add_message("assistant", full_response)

        except KeyboardInterrupt:
            # Ctrl+C 中断流式接收
            print("\n[Interrupted]")
            print()

            # 将已接收的部分内容作为 assistant 消息
            if full_response:
                self._message_manager.add_message("assistant", full_response)

    def _handle_api_error(self, error: APIError) -> None:
        """处理 API 错误。

        Args:
            error: API 错误对象
        """
        # 打印错误信息（红色文字，如果终端支持）
        error_msg = f"Error: {str(error)}"

        # 尝试使用 ANSI 颜色代码
        if self._enable_color and sys.stdout.isatty():
            # 红色文字: \033[31m
            print(f"\033[31m{error_msg}\033[0m")
        else:
            print(error_msg)

        print()

        # 注意：不将错误信息添加到消息列表


def main() -> None:
    """主函数入口。"""
    config = get_config()
    conversation = ConversationLoop(config)
    conversation.run()


if __name__ == "__main__":
    main()
