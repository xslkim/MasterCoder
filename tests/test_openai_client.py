"""REQ-03: OpenAI 兼容 API 客户端测试"""

import json
import pytest
from unittest.mock import Mock, patch
import httpx
from mastercoder_automation.openai_client import (
    OpenAIClient,
    Message,
    APIError,
)


class TestOpenAIClient:
    """OpenAI 客户端测试类"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return OpenAIClient(
            api_base_url="https://api.example.com/v1",
            api_key="test-api-key",
            model="gpt-4",
        )

    def test_non_streaming_request_success(self, client):
        """测试非流式正常请求与解析"""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello, how can I help you?",
                    },
                    "finish_reason": "stop",
                }
            ]
        }

        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)

            messages = [Message(role="user", content="Hi")]

            response = client.chat(messages, stream=False)

            assert response.content == "Hello, how can I help you?"
            assert response.tool_calls is None

            # 验证请求参数
            call_args = mock_post.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"
            assert call_args[1]["headers"]["Content-Type"] == "application/json"

            body = call_args[1]["json"]
            assert body["model"] == "gpt-4"
            assert body["messages"][0]["role"] == "user"
            assert body["stream"] is False

    def test_streaming_request_success(self, client):
        """测试流式正常请求，验证片段逐个回调且最终拼接正确"""
        # 模拟 SSE 响应
        sse_events = [
            'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
            'data: {"choices":[{"delta":{"content":" there"},"finish_reason":null}]}\n\n',
            'data: {"choices":[{"delta":{"content":"!"},"finish_reason":"stop"}]}\n\n',
            "data: [DONE]\n\n",
        ]

        collected_chunks = []

        def callback(chunk):
            collected_chunks.append(chunk)

        with patch("httpx.stream") as mock_stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_response.iter_lines.return_value = iter(sse_events)
            mock_stream.return_value = mock_response

            messages = [Message(role="user", content="Hi")]

            response = client.chat(messages, stream=True, callback=callback)

            # 验证回调被正确调用
            assert collected_chunks == ["Hello", " there", "!"]
            # 验证最终拼接结果
            assert response.content == "Hello there!"

    def test_streaming_with_tool_calls(self, client):
        """测试流式中包含工具调用的解析"""
        sse_events = [
            'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_123","function":{"name":"get_weather","arguments":"{\\"location\\":\\"Beijing\\"}"}}]},"finish_reason":"stop"}]}\n\n',
            "data: [DONE]\n\n",
        ]

        with patch("httpx.stream") as mock_stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_response.iter_lines.return_value = iter(sse_events)
            mock_stream.return_value = mock_response

            messages = [Message(role="user", content="What's the weather?")]

            response = client.chat(messages, stream=True)

            assert response.tool_calls is not None
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0].id == "call_123"
            assert response.tool_calls[0].function_name == "get_weather"
            assert response.tool_calls[0].function_arguments == '{"location":"Beijing"}'

    def test_error_401_authentication_failed(self, client):
        """测试 401 错误码处理"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=401, text="Unauthorized")

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert "Authentication failed" in str(exc_info.value)

    def test_error_404_model_not_found(self, client):
        """测试 404 错误码处理"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=404, text="Not Found")

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert "Model not found" in str(exc_info.value)

    def test_error_429_rate_limit(self, client):
        """测试 429 错误码处理"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=429, text="Too Many Requests")

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert "Rate limit exceeded" in str(exc_info.value)

    def test_error_500_server_error(self, client):
        """测试 500+ 错误码处理"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=500, text="Internal Server Error")

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert "Server error" in str(exc_info.value)

    def test_connection_timeout(self, client):
        """测试网络超时处理"""
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timeout")

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert (
                "Connection failed" in str(exc_info.value)
                or "timeout" in str(exc_info.value).lower()
            )

    def test_invalid_json_response(self, client):
        """测试非法 JSON 响应处理"""
        with patch("httpx.post") as mock_post:

            def raise_json_error():
                raise json.JSONDecodeError("Invalid JSON", "", 0)

            mock_post.return_value = Mock(status_code=200, json=raise_json_error)

            messages = [Message(role="user", content="Hi")]

            with pytest.raises(APIError) as exc_info:
                client.chat(messages, stream=False)

            assert "Invalid response format" in str(exc_info.value)

    def test_authorization_header_format(self, client):
        """验证 Authorization header 正确拼接，无多余空格"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "OK"}}]},
            )

            messages = [Message(role="user", content="Hi")]
            client.chat(messages, stream=False)

            call_args = mock_post.call_args
            auth_header = call_args[1]["headers"]["Authorization"]

            # 确保格式正确：Bearer + 单个空格 + key
            assert auth_header == "Bearer test-api-key"
            assert auth_header.count(" ") == 1  # 只有一个空格

    def test_request_timeout_set(self, client):
        """测试请求超时设置为 120 秒"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "OK"}}]},
            )

            messages = [Message(role="user", content="Hi")]
            client.chat(messages, stream=False)

            call_args = mock_post.call_args
            assert call_args[1]["timeout"] == 120

    def test_streaming_handles_empty_lines(self, client):
        """测试流式解析健壮：处理空行"""
        sse_events = [
            "",
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            "",
            "data: [DONE]\n\n",
        ]

        collected_chunks = []

        def callback(chunk):
            collected_chunks.append(chunk)

        with patch("httpx.stream") as mock_stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_response.iter_lines.return_value = iter(sse_events)
            mock_stream.return_value = mock_response

            messages = [Message(role="user", content="Hi")]
            response = client.chat(messages, stream=True, callback=callback)

            # 空行应该被忽略
            assert collected_chunks == ["Hello"]
            assert response.content == "Hello"

    def test_request_body_structure(self, client):
        """测试请求体结构符合规范"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "OK"}}]},
            )

            messages = [
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hi"),
            ]

            client.chat(messages, stream=False, max_tokens=4096, temperature=0.0)

            call_args = mock_post.call_args
            body = call_args[1]["json"]

            assert body["model"] == "gpt-4"
            assert len(body["messages"]) == 2
            assert body["messages"][0]["role"] == "system"
            assert body["messages"][1]["role"] == "user"
            assert body["max_tokens"] == 4096
            assert body["temperature"] == 0.0
            assert body["stream"] is False

    def test_tools_in_request(self, client):
        """测试请求中包含工具定义"""
        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "OK"}}]},
            )

            messages = [Message(role="user", content="Hi")]
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather info",
                        "parameters": {},
                    },
                }
            ]

            client.chat(messages, stream=False, tools=tools)

            call_args = mock_post.call_args
            body = call_args[1]["json"]

            assert "tools" in body
            assert body["tools"][0]["function"]["name"] == "get_weather"

    def test_non_streaming_tool_calls(self, client):
        """测试非流式模式下的工具调用解析"""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_456",
                                "function": {
                                    "name": "search",
                                    "arguments": '{"query":"python"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        with patch("httpx.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)

            messages = [Message(role="user", content="Search for python")]
            response = client.chat(messages, stream=False)

            assert response.tool_calls is not None
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0].id == "call_456"
            assert response.tool_calls[0].function_name == "search"
            assert response.tool_calls[0].function_arguments == '{"query":"python"}'
