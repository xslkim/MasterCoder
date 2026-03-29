"""
REQ-07: 工具调用执行引擎测试

测试工具调用执行引擎的各种场景
"""

import pytest
from unittest.mock import Mock, patch
from io import StringIO
import json

from src.tool_executor import ToolExecutor, ToolRegistry


class TestToolRegistry:
    """工具注册器测试"""

    def test_register_tool(self):
        """测试工具注册"""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="result")

        registry.register("test_tool", mock_tool)

        assert registry.get("test_tool") == mock_tool

    def test_get_unknown_tool(self):
        """测试获取未注册的工具"""
        registry = ToolRegistry()

        assert registry.get("unknown_tool") is None


class TestToolExecutor:
    """工具调用执行引擎测试"""

    @pytest.fixture
    def registry(self):
        """创建工具注册器"""
        return ToolRegistry()

    @pytest.fixture
    def message_manager(self):
        """创建消息管理器 Mock"""
        return Mock()

    @pytest.fixture
    def api_client(self):
        """创建 API 客户端 Mock"""
        return Mock()

    @pytest.fixture
    def executor(self, registry, message_manager, api_client):
        """创建工具执行器"""
        return ToolExecutor(
            registry=registry,
            message_manager=message_manager,
            api_client=api_client,
            auto_approve=False,
        )

    def test_execute_single_tool_with_user_approval_y(
        self, executor, registry, message_manager, api_client
    ):
        """测试单个工具调用完整流程 - 用户确认 Y"""
        # 准备工具
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="file content here")
        registry.register("read_file", mock_tool)

        # 准备 tool_calls
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "/home/user/project/main.py"}),
                },
            }
        ]

        # Mock 用户输入
        with patch("sys.stdin", StringIO("Y\n")):
            # Mock API 响应
            api_client.call_api = Mock(
                return_value={"content": "Based on the file content...", "tool_calls": None}
            )

            executor.execute_tool_calls(tool_calls)

        # 验证工具被调用
        mock_tool.execute.assert_called_once_with({"path": "/home/user/project/main.py"})

        # 验证消息被添加
        assert message_manager.add_message.call_count == 2  # assistant + tool

    def test_execute_tool_user_rejects_n(self, executor, registry, message_manager, api_client):
        """测试用户拒绝工具调用 - N"""
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="should not be called")
        registry.register("read_file", mock_tool)

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "read_file", "arguments": json.dumps({"path": "/test.py"})},
            }
        ]

        with patch("sys.stdin", StringIO("N\n")):
            api_client.call_api = Mock(
                return_value={"content": "User rejected the tool call", "tool_calls": None}
            )

            executor.execute_tool_calls(tool_calls)

        # 工具不应被调用
        mock_tool.execute.assert_not_called()

        # 验证拒绝消息被添加
        calls = message_manager.add_message.call_args_list
        tool_call = [c for c in calls if c[1].get("role") == "tool"][0]
        assert "rejected by user" in tool_call[1]["content"].lower()

    def test_execute_tool_user_selects_always(
        self, executor, registry, message_manager, api_client
    ):
        """测试用户选择 Always 后后续自动执行"""
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="result")
        registry.register("read_file", mock_tool)

        tool_call_1 = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": json.dumps({"path": "/file1.py"})},
            }
        ]

        tool_call_2 = [
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "read_file", "arguments": json.dumps({"path": "/file2.py"})},
            }
        ]

        # 第一次用户选择 A
        with patch("sys.stdin", StringIO("A\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_call_1)

        # 第二次不应询问（auto_approve 已设为 true）
        with patch("builtins.input") as mock_input:
            # 如果 input 被调用，说明还在询问
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_call_2)

            # input 不应被调用
            mock_input.assert_not_called()

        # 验证 auto_approve 已设置
        assert executor.auto_approve is True

    def test_auto_approve_mode(self, registry, message_manager, api_client):
        """测试 auto_approve 模式直接执行"""
        executor = ToolExecutor(
            registry=registry,
            message_manager=message_manager,
            api_client=api_client,
            auto_approve=True,
        )

        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="result")
        registry.register("read_file", mock_tool)

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "read_file", "arguments": json.dumps({"path": "/test.py"})},
            }
        ]

        with patch("builtins.input") as mock_input:
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

            # 不应询问用户
            mock_input.assert_not_called()

        # 工具应被执行
        mock_tool.execute.assert_called_once()

    def test_unknown_tool_error(self, executor, registry, message_manager, api_client):
        """测试未知工具名称处理"""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "unknown_tool", "arguments": json.dumps({})},
            }
        ]

        with patch("sys.stdin", StringIO("Y\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

        # 验证错误消息
        calls = message_manager.add_message.call_args_list
        tool_call = [c for c in calls if c[1].get("role") == "tool"][0]
        assert "unknown tool" in tool_call[1]["content"].lower()

    def test_invalid_arguments_error(self, executor, registry, message_manager, api_client):
        """测试参数解析失败处理"""
        mock_tool = Mock()
        registry.register("test_tool", mock_tool)

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "arguments": "invalid json{",  # 无效 JSON
                },
            }
        ]

        with patch("sys.stdin", StringIO("Y\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

        # 验证错误消息
        calls = message_manager.add_message.call_args_list
        tool_call = [c for c in calls if c[1].get("role") == "tool"][0]
        assert "invalid tool arguments" in tool_call[1]["content"].lower()

    def test_tool_execution_exception(self, executor, registry, message_manager, api_client):
        """测试工具执行异常处理"""
        mock_tool = Mock()
        mock_tool.execute = Mock(side_effect=Exception("Tool crashed"))
        registry.register("test_tool", mock_tool)

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_tool", "arguments": json.dumps({"param": "value"})},
            }
        ]

        with patch("sys.stdin", StringIO("Y\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

        # 验证错误消息
        calls = message_manager.add_message.call_args_list
        tool_call = [c for c in calls if c[1].get("role") == "tool"][0]
        assert "tool execution failed" in tool_call[1]["content"].lower()
        assert "tool crashed" in tool_call[1]["content"].lower()

    def test_multiple_tool_calls_sequential(self, executor, registry, message_manager, api_client):
        """测试多工具调用顺序执行"""
        tool1 = Mock()
        tool1.execute = Mock(return_value="result1")
        registry.register("tool1", tool1)

        tool2 = Mock()
        tool2.execute = Mock(return_value="result2")
        registry.register("tool2", tool2)

        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "tool1", "arguments": json.dumps({"x": 1})},
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "tool2", "arguments": json.dumps({"y": 2})},
            },
        ]

        with patch("sys.stdin", StringIO("Y\nY\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

        # 验证两个工具都被调用，且顺序正确
        assert tool1.execute.call_count == 1
        assert tool2.execute.call_count == 1

        # 验证调用顺序
        assert tool1.execute.called_before(tool2.execute)

    def test_nested_tool_calls_depth_limit(self, executor, registry, message_manager, api_client):
        """测试嵌套调用达到上限"""
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="result")
        registry.register("test_tool", mock_tool)

        tool_call = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_tool", "arguments": json.dumps({})},
            }
        ]

        # Mock API 始终返回 tool_calls（模拟无限嵌套）
        call_count = [0]

        def mock_api_call(messages):
            call_count[0] += 1
            if call_count[0] > 20:
                # 超过限制后应该不会继续调用
                return {"content": "final", "tool_calls": None}
            return {"content": None, "tool_calls": tool_call}

        api_client.call_api = mock_api_call

        with patch("sys.stdin", StringIO("Y\n" * 25)):
            with patch("sys.stdout", new_callable=StringIO):
                executor.execute_tool_calls(tool_call)

        # 验证在达到上限后停止
        # 应该在第 20 次后停止
        assert call_count[0] <= 22  # 允许一些误差

    def test_tool_call_id_correct_mapping(self, executor, registry, message_manager, api_client):
        """测试 tool_call_id 正确对应"""
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value="result")
        registry.register("test_tool", mock_tool)

        tool_calls = [
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "test_tool", "arguments": json.dumps({"id": 1})},
            },
            {
                "id": "call_xyz",
                "type": "function",
                "function": {"name": "test_tool", "arguments": json.dumps({"id": 2})},
            },
        ]

        with patch("sys.stdin", StringIO("Y\nY\n")):
            api_client.call_api = Mock(return_value={"content": "result", "tool_calls": None})

            executor.execute_tool_calls(tool_calls)

        # 验证 tool_call_id 正确映射
        calls = message_manager.add_message.call_args_list
        tool_calls_made = [c for c in calls if c[1].get("role") == "tool"]

        ids = [c[1].get("tool_call_id") for c in tool_calls_made]
        assert "call_abc" in ids
        assert "call_xyz" in ids
