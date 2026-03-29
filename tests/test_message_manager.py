"""
Tests for REQ-04: 对话消息管理器
"""
import pytest
from src.message_manager import MessageManager


class TestMessageManager:
    """测试消息管理器的基本功能"""

    def test_add_and_get_messages(self):
        """测试添加各角色消息后 get_messages() 返回正确"""
        manager = MessageManager()
        manager.add_message("system", "You are a helpful assistant.")
        manager.add_message("user", "Hello!")
        manager.add_message("assistant", "Hi there!")
        
        messages = manager.get_messages()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["content"] == "Hi there!"

    def test_add_messages_with_tool_calls(self):
        """测试添加带 tool_calls 的 assistant 消息"""
        manager = MessageManager()
        manager.add_message("user", "What's the weather?")
        tool_calls = [{"id": "call_123", "function": {"name": "get_weather", "arguments": "{}"}}]
        manager.add_message("assistant", None, tool_calls=tool_calls)
        
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["tool_calls"] == tool_calls

    def test_add_messages_with_tool_call_id(self):
        """测试添加带 tool_call_id 的 tool 消息"""
        manager = MessageManager()
        manager.add_message("user", "What's the weather?")
        tool_calls = [{"id": "call_123", "function": {"name": "get_weather", "arguments": "{}"}}]
        manager.add_message("assistant", None, tool_calls=tool_calls)
        manager.add_message("tool", "Sunny, 25°C", tool_call_id="call_123")
        
        messages = manager.get_messages()
        assert len(messages) == 3
        assert messages[2]["role"] == "tool"
        assert messages[2]["tool_call_id"] == "call_123"
        assert messages[2]["content"] == "Sunny, 25°C"

    def test_clear_preserves_system_messages(self):
        """测试 clear() 后仅剩 system 消息"""
        manager = MessageManager()
        manager.add_message("system", "You are a helpful assistant.")
        manager.add_message("user", "Hello!")
        manager.add_message("assistant", "Hi there!")
        manager.add_message("user", "How are you?")
        
        manager.clear()
        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_clear_with_multiple_system_messages(self):
        """测试 clear() 保留所有 system 消息"""
        manager = MessageManager()
        manager.add_message("system", "System message 1")
        manager.add_message("user", "Hello!")
        manager.add_message("system", "System message 2")
        manager.add_message("assistant", "Hi there!")
        
        manager.clear()
        messages = manager.get_messages()
        assert len(messages) == 2
        assert all(msg["role"] == "system" for msg in messages)

    def test_token_estimate(self):
        """测试 Token 估算值与字符数 / 4 一致"""
        manager = MessageManager()
        # 1000 个字符应该返回 250 tokens
        long_content = "a" * 1000
        manager.add_message("user", long_content)
        
        estimate = manager.get_token_estimate()
        assert estimate == 250

    def test_token_estimate_multiple_messages(self):
        """测试多条消息的 token 估算"""
        manager = MessageManager()
        manager.add_message("system", "1234")  # 4 chars = 1 token
        manager.add_message("user", "5678")    # 4 chars = 1 token
        manager.add_message("assistant", "90") # 2 chars = 0.5 token
        
        estimate = manager.get_token_estimate()
        # 10 chars total / 4 = 2.5, should be rounded or floored
        assert estimate == 2 or estimate == 3  # Allow for rounding

    def test_prepare_messages_no_truncation(self):
        """测试未超出限制时 truncated 为 false"""
        manager = MessageManager()
        manager.add_message("system", "You are a helpful assistant.")
        manager.add_message("user", "Hello!")
        manager.add_message("assistant", "Hi there!")
        
        result = manager.prepare_messages(max_context_tokens=10000)
        assert result["truncated"] is False
        assert len(result["messages"]) == 3

    def test_prepare_messages_with_truncation(self):
        """测试超出上下文限制时截断行为正确"""
        manager = MessageManager()
        manager.add_message("system", "System message")
        # Add messages that will exceed limit
        manager.add_message("user", "a" * 200)   # 50 tokens
        manager.add_message("assistant", "b" * 200)  # 50 tokens
        manager.add_message("user", "c" * 200)   # 50 tokens
        manager.add_message("assistant", "d" * 200)  # 50 tokens
        # Total: 200 tokens without system message
        
        result = manager.prepare_messages(max_context_tokens=100)
        assert result["truncated"] is True
        # System message should be preserved
        assert result["messages"][0]["role"] == "system"
        # Total tokens should be <= max_context_tokens
        total_chars = sum(len(msg.get("content", "")) for msg in result["messages"])
        estimated_tokens = total_chars // 4
        assert estimated_tokens <= 100

    def test_prepare_messages_preserves_system_message(self):
        """测试 system 消息在任何情况下都不会被截断"""
        manager = MessageManager()
        manager.add_message("system", "Important system instruction")
        manager.add_message("user", "a" * 1000)  # 250 tokens
        
        result = manager.prepare_messages(max_context_tokens=50)
        assert result["truncated"] is True
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == "Important system instruction"

    def test_prepare_messages_returns_copy(self):
        """测试截断操作返回副本，不修改原始消息列表"""
        manager = MessageManager()
        manager.add_message("system", "System")
        manager.add_message("user", "a" * 400)   # 100 tokens
        manager.add_message("assistant", "b" * 400)  # 100 tokens
        
        original_messages = manager.get_messages()
        original_count = len(original_messages)
        
        result = manager.prepare_messages(max_context_tokens=50)
        
        # Original list should not be modified
        assert len(manager.get_messages()) == original_count
        # Result should have fewer messages
        assert len(result["messages"]) < original_count

    def test_acceptance_criteria_multiple_messages(self):
        """验收标准：添加 1 条 system、3 条 user、3 条 assistant 消息后，返回 7 条，顺序正确"""
        manager = MessageManager()
        manager.add_message("system", "System message")
        manager.add_message("user", "User 1")
        manager.add_message("assistant", "Assistant 1")
        manager.add_message("user", "User 2")
        manager.add_message("assistant", "Assistant 2")
        manager.add_message("user", "User 3")
        manager.add_message("assistant", "Assistant 3")
        
        messages = manager.get_messages()
        assert len(messages) == 7
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
        assert messages[4]["role"] == "assistant"
        assert messages[5]["role"] == "user"
        assert messages[6]["role"] == "assistant"

    def test_acceptance_criteria_clear(self):
        """验收标准：调用 clear() 后，返回 1 条（system）"""
        manager = MessageManager()
        manager.add_message("system", "System message")
        manager.add_message("user", "User 1")
        manager.add_message("assistant", "Assistant 1")
        manager.add_message("user", "User 2")
        
        manager.clear()
        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_acceptance_criteria_token_estimate_1000_chars(self):
        """验收标准：1000 个字符的消息，返回 250"""
        manager = MessageManager()
        content = "a" * 1000
        manager.add_message("user", content)
        
        estimate = manager.get_token_estimate()
        assert estimate == 250

    def test_acceptance_criteria_truncation_scenario(self):
        """验收标准：设置 max_context_tokens = 100，当总量为 200 token 时，截断正确"""
        manager = MessageManager()
        manager.add_message("system", "System")
        manager.add_message("user", "a" * 200)   # 50 tokens
        manager.add_message("assistant", "b" * 200)  # 50 tokens
        manager.add_message("user", "c" * 200)   # 50 tokens
        manager.add_message("assistant", "d" * 200)  # 50 tokens
        # Total: ~200 tokens
        
        result = manager.prepare_messages(max_context_tokens=100)
        assert result["truncated"] is True
        assert result["messages"][0]["role"] == "system"

    def test_message_order_preserved(self):
        """测试消息顺序正确保留"""
        manager = MessageManager()
        manager.add_message("system", "msg1")
        manager.add_message("user", "msg2")
        manager.add_message("assistant", "msg3")
        manager.add_message("user", "msg4")
        
        messages = manager.get_messages()
        assert messages[0]["content"] == "msg1"
        assert messages[1]["content"] == "msg2"
        assert messages[2]["content"] == "msg3"
        assert messages[3]["content"] == "msg4"

    def test_empty_manager(self):
        """测试空管理器的行为"""
        manager = MessageManager()
        assert manager.get_messages() == []
        assert manager.get_token_estimate() == 0
        
        result = manager.prepare_messages(max_context_tokens=100)
        assert result["truncated"] is False
        assert result["messages"] == []

    def test_clear_empty_manager(self):
        """测试对空管理器调用 clear()"""
        manager = MessageManager()
        manager.clear()
        assert manager.get_messages() == []
