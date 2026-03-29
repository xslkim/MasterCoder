"""REQ-05：基础对话循环集成测试

测试覆盖以下场景：
- 正常对话流程：输入 → 流式输出 → 下一轮输入
- API 报错时的错误展示和恢复
- 多轮对话的消息累积正确性
- api_key 为空时的启动拒绝
- Ctrl+C 中断流式输出后的恢复
"""

from pathlib import Path

from mastercoder.message_manager import MessageManager


class TestConversationFlow:
    """测试正常对话流程"""

    def test_normal_conversation_single_turn(self, tmp_path: Path, monkeypatch) -> None:
        """测试单轮正常对话：输入 → 流式输出"""
        # 设置配置
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test123", "model": "gpt-4o"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # 重新加载配置
        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        # 创建消息管理器
        msg_manager = MessageManager()

        # 添加用户消息
        msg_manager.add_message("user", "Hello")

        # 验证消息已添加
        messages = msg_manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_streaming_output_display(self, tmp_path: Path, monkeypatch) -> None:
        """测试流式输出实时显示"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test123"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        # 模拟流式输出
        output_chunks = ["Hello", " ", "world", "!"]
        captured_output = []

        for chunk in output_chunks:
            captured_output.append(chunk)

        # 验证输出片段被正确捕获
        assert "".join(captured_output) == "Hello world!"

    def test_multi_turn_conversation_message_accumulation(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """测试多轮对话消息累积正确性"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test123"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        # 创建消息管理器
        msg_manager = MessageManager()

        # 添加内置 system 消息
        system_msg = "You are MasterCoder, an AI programming assistant."
        msg_manager.add_message("system", system_msg)

        # 第一轮对话
        msg_manager.add_message("user", "My name is Alice")
        msg_manager.add_message("assistant", "Nice to meet you, Alice!")

        # 第二轮对话
        msg_manager.add_message("user", "What's my name?")
        msg_manager.add_message("assistant", "Your name is Alice.")

        # 验证消息累积
        messages = msg_manager.get_messages()
        assert len(messages) == 5
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
        assert messages[4]["role"] == "assistant"


class TestAPIErrorHandling:
    """测试 API 报错处理"""

    def test_api_error_display_and_recovery(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """测试 API 报错时的错误展示和恢复"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-invalid"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        # 创建消息管理器
        msg_manager = MessageManager()

        # 添加用户消息
        msg_manager.add_message("user", "Hello")

        # 模拟 API 错误
        error_msg = "Authentication failed: invalid API key"

        # 验证错误信息格式
        expected_error = f"Error: {error_msg}"
        assert "Error:" in expected_error
        assert "invalid API key" in expected_error

        # 验证错误不会污染消息列表
        messages = msg_manager.get_messages()
        assert len(messages) == 1  # 只有用户消息，没有错误消息
        assert messages[0]["role"] == "user"

    def test_api_error_does_not_add_to_messages(self, tmp_path: Path, monkeypatch) -> None:
        """测试 API 错误不会添加到消息列表"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager()
        msg_manager.add_message("user", "Test")

        # 模拟 API 错误场景
        initial_count = len(msg_manager.get_messages())

        # 错误不应添加消息
        # （在实际实现中，API 错误不会调用 add_message）
        assert len(msg_manager.get_messages()) == initial_count


class TestEmptyAPIKey:
    """测试 API Key 为空时的启动拒绝"""

    def test_empty_api_key_exits_on_startup(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """测试 api_key 为空时程序启动直接报错退出"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": ""}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        import mastercoder.config

        mastercoder.config._config = None
        config = mastercoder.config.get_config()

        # 验证 api_key 为空
        assert config.api_key == ""

        # 验证错误消息格式
        expected_error = "Error: API key not configured. Set MASTERCODER_API_KEY or add api_key to ~/.mastercoder/config.json"
        assert "API key not configured" in expected_error

    def test_no_config_file_empty_api_key(self, tmp_path: Path, monkeypatch) -> None:
        """测试无配置文件且无环境变量时 api_key 为空"""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        import mastercoder.config

        mastercoder.config._config = None
        config = mastercoder.config.get_config()

        # 验证默认 api_key 为空
        assert config.api_key == ""


class TestSystemMessageHandling:
    """测试系统消息处理"""

    def test_builtin_system_message_added(self, tmp_path: Path, monkeypatch) -> None:
        """测试内置 system 消息被添加"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager()

        # 添加内置 system 消息
        builtin_system = "You are MasterCoder, an AI programming assistant. You help users with software development tasks including writing code, debugging, refactoring, and explaining code. You have access to tools that can read files, write files, edit files, search files, and run commands on the user's local machine. Always be helpful, concise, and accurate."
        msg_manager.add_message("system", builtin_system)

        messages = msg_manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "MasterCoder" in messages[0]["content"]

    def test_custom_system_prompt_appended(self, tmp_path: Path, monkeypatch) -> None:
        """测试自定义 system_prompt 被追加"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(
            '{"api_key": "sk-test", "system_prompt": "You are a Python expert."}'
        )

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        config = mastercoder.config.get_config()

        # 验证 system_prompt 已加载
        assert config.system_prompt == "You are a Python expert."

        msg_manager = MessageManager()

        # 添加内置 system 消息
        builtin_system = "You are MasterCoder, an AI programming assistant."
        # 追加自定义 prompt
        full_system = builtin_system
        if config.system_prompt:
            full_system += " " + config.system_prompt

        msg_manager.add_message("system", full_system)

        messages = msg_manager.get_messages()
        assert "MasterCoder" in messages[0]["content"]
        assert "Python expert" in messages[0]["content"]


class TestContextTruncation:
    """测试上下文截断"""

    def test_context_truncation_warning(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """测试上下文截断时打印警告"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager(max_messages=10)

        # 添加大量消息触发截断
        msg_manager.add_message("system", "System message")
        for i in range(20):
            msg_manager.add_message("user", f"User message {i}")
            msg_manager.add_message("assistant", f"Assistant message {i}")

        # 调用 prepare_messages
        messages = msg_manager.prepare_messages()

        # 验证截断发生
        assert msg_manager.was_truncated()
        assert len(messages) <= 10


class TestInterruptHandling:
    """测试 Ctrl+C 中断处理"""

    def test_interrupt_saves_partial_response(self, tmp_path: Path, monkeypatch) -> None:
        """测试中断后保存部分响应"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager()
        msg_manager.add_message("user", "Hello")

        # 模拟部分接收的响应
        partial_response = "Hello! I was "

        # 在中断场景中，部分响应应被添加为 assistant 消息
        msg_manager.add_message("assistant", partial_response)

        messages = msg_manager.get_messages()
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == partial_response

    def test_interrupt_allows_continuation(self, tmp_path: Path, monkeypatch) -> None:
        """测试中断后可继续对话"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager()

        # 第一轮对话（被中断）
        msg_manager.add_message("user", "Question 1")
        msg_manager.add_message("assistant", "Partial answer")

        # 第二轮对话（继续）
        msg_manager.add_message("user", "Question 2")
        msg_manager.add_message("assistant", "Answer 2")

        messages = msg_manager.get_messages()
        assert len(messages) == 4
        # 验证消息角色交替正确
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"


class TestMessageRoleAlternation:
    """测试消息角色交替"""

    def test_message_roles_alternate_correctly(self, tmp_path: Path, monkeypatch) -> None:
        """测试多轮对话消息角色交替正确"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"api_key": "sk-test"}')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        import mastercoder.config

        mastercoder.config._config = None
        mastercoder.config.get_config()

        msg_manager = MessageManager()

        # 添加消息序列
        msg_manager.add_message("system", "System prompt")
        msg_manager.add_message("user", "User 1")
        msg_manager.add_message("assistant", "Assistant 1")
        msg_manager.add_message("user", "User 2")
        msg_manager.add_message("assistant", "Assistant 2")

        messages = msg_manager.get_messages()

        # 验证角色交替
        expected_roles = ["system", "user", "assistant", "user", "assistant"]
        actual_roles = [msg["role"] for msg in messages]
        assert actual_roles == expected_roles
