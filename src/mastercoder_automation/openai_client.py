"""REQ-03: OpenAI 兼容 API 客户端"""

import json
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
import httpx


@dataclass
class Message:
    """消息类型定义"""

    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role, "content": self.content}


@dataclass
class ToolCall:
    """工具调用类型定义"""

    id: str
    function_name: str
    function_arguments: str  # JSON 字符串，由上层工具执行器负责解析


@dataclass
class APIResponse:
    """API 响应类型定义"""

    content: str
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: Optional[str] = None


class APIError(Exception):
    """API 错误类型"""

    pass


class OpenAIClient:
    """OpenAI 兼容 API 客户端"""

    def __init__(self, api_base_url: str, api_key: str, model: str, timeout: int = 120):
        """
        初始化客户端

        Args:
            api_base_url: API 基础 URL
            api_key: API 密钥
            model: 模型名称
            timeout: 请求超时时间（秒），默认 120
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    def _build_request_body(
        self,
        messages: List[Message],
        stream: bool,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        构建请求体

        Args:
            messages: 消息列表
            stream: 是否流式请求
            max_tokens: 最大 token 数
            temperature: 温度参数
            tools: 工具定义列表

        Returns:
            请求体字典
        """
        body = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        if tools:
            body["tools"] = tools

        return body

    def _handle_error_response(self, status_code: int, response_text: str) -> None:
        """
        处理错误响应

        Args:
            status_code: HTTP 状态码
            response_text: 响应文本

        Raises:
            APIError: 对应的错误信息
        """
        if status_code == 401:
            raise APIError("Authentication failed: invalid API key")
        elif status_code == 404:
            raise APIError(f"Model not found: {self.model}")
        elif status_code == 429:
            raise APIError("Rate limit exceeded, please retry later")
        elif status_code >= 500:
            raise APIError(f"Server error: {status_code}")
        else:
            raise APIError(f"API request failed with status {status_code}: {response_text}")

    def _parse_tool_calls(self, tool_calls_data: List[Dict[str, Any]]) -> List[ToolCall]:
        """
        解析工具调用列表

        Args:
            tool_calls_data: 工具调用数据列表

        Returns:
            ToolCall 对象列表
        """
        tool_calls = []
        for tc in tool_calls_data:
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    function_name=tc.get("function", {}).get("name", ""),
                    function_arguments=tc.get("function", {}).get("arguments", "{}"),
                )
            )
        return tool_calls

    def _parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析 SSE 行

        Args:
            line: SSE 行内容

        Returns:
            解析后的数据字典，如果行无效则返回 None
        """
        line = line.strip()

        # 跳过空行
        if not line:
            return None

        # 检查是否是 data 行
        if not line.startswith("data: "):
            return None

        # 提取数据部分
        data = line[6:]  # 去掉 "data: " 前缀

        # 检查是否是结束标记
        if data == "[DONE]":
            return {"done": True}

        # 尝试解析 JSON
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            # 忽略无效的 JSON
            return None

    def _parse_streaming_chunk(
        self, chunk_data: Dict[str, Any]
    ) -> tuple[str, Optional[List[ToolCall]]]:
        """
        解析流式响应块

        Args:
            chunk_data: 块数据

        Returns:
            (内容片段, 工具调用列表)
        """
        content = ""
        tool_calls = None

        choices = chunk_data.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")

            # 检查工具调用
            if "tool_calls" in delta:
                tool_calls = self._parse_tool_calls(delta["tool_calls"])

        return content, tool_calls

    def chat(
        self,
        messages: List[Message],
        stream: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> APIResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            stream: 是否使用流式模式，默认 True
            max_tokens: 最大 token 数
            temperature: 温度参数
            tools: 工具定义列表
            callback: 流式回调函数，每个片段都会调用

        Returns:
            APIResponse 对象

        Raises:
            APIError: API 错误
        """
        url = f"{self.api_base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_request_body(messages, stream, max_tokens, temperature, tools)

        if stream:
            return self._stream_request(url, headers, body, callback)
        else:
            return self._non_stream_request(url, headers, body)

    def _non_stream_request(
        self, url: str, headers: Dict[str, str], body: Dict[str, Any]
    ) -> APIResponse:
        """
        发送非流式请求

        Args:
            url: 请求 URL
            headers: 请求头
            body: 请求体

        Returns:
            APIResponse 对象
        """
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=self.timeout)

            # 检查状态码
            if response.status_code != 200:
                self._handle_error_response(response.status_code, response.text)

            # 解析响应
            try:
                data = response.json()
            except json.JSONDecodeError:
                raise APIError("Invalid response format from API")

            # 提取内容
            choices = data.get("choices", [])
            if not choices:
                return APIResponse(content="")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            finish_reason = choices[0].get("finish_reason")

            # 检查工具调用
            tool_calls = None
            if "tool_calls" in message:
                tool_calls = self._parse_tool_calls(message["tool_calls"])

            return APIResponse(content=content, tool_calls=tool_calls, finish_reason=finish_reason)

        except httpx.TimeoutException as e:
            raise APIError(f"Connection failed: timeout - {str(e)}")
        except httpx.RequestError as e:
            raise APIError(f"Connection failed: {str(e)}")

    def _stream_request(
        self,
        url: str,
        headers: Dict[str, str],
        body: Dict[str, Any],
        callback: Optional[Callable[[str], None]] = None,
    ) -> APIResponse:
        """
        发送流式请求

        Args:
            url: 请求 URL
            headers: 请求头
            body: 请求体
            callback: 回调函数

        Returns:
            APIResponse 对象
        """
        try:
            with httpx.stream(
                "POST", url, headers=headers, json=body, timeout=self.timeout
            ) as response:
                # 检查状态码
                if response.status_code != 200:
                    self._handle_error_response(response.status_code, "")

                # 收集所有片段
                content_chunks = []
                all_tool_calls = []
                finish_reason = None

                # 逐行读取 SSE 响应
                for line in response.iter_lines():
                    chunk_data = self._parse_sse_line(line)

                    # 跳过无效行
                    if chunk_data is None:
                        continue

                    # 检查是否结束
                    if chunk_data.get("done"):
                        break

                    # 解析块
                    chunk_content, tool_calls = self._parse_streaming_chunk(chunk_data)

                    # 调用回调
                    if chunk_content and callback:
                        callback(chunk_content)

                    # 收集内容
                    if chunk_content:
                        content_chunks.append(chunk_content)

                    # 收集工具调用
                    if tool_calls:
                        all_tool_calls.extend(tool_calls)

                    # 获取 finish_reason
                    if "choices" in chunk_data and chunk_data["choices"]:
                        finish_reason = chunk_data["choices"][0].get("finish_reason")

                # 拼接完整内容
                full_content = "".join(content_chunks)

                return APIResponse(
                    content=full_content,
                    tool_calls=all_tool_calls if all_tool_calls else None,
                    finish_reason=finish_reason,
                )

        except httpx.TimeoutException as e:
            raise APIError(f"Connection failed: timeout - {str(e)}")
        except httpx.RequestError as e:
            raise APIError(f"Connection failed: {str(e)}")
