"""API 客户端 - 处理与 OpenAI 兼容 API 的通信。"""

import json
from typing import Any, Generator
import urllib.request
import urllib.error

from mastercoder.config import Config


class APIError(Exception):
    """API 错误异常。"""

    pass


class APIClient:
    """OpenAI 兼容 API 客户端。"""

    def __init__(self, config: Config) -> None:
        """初始化 API 客户端。

        Args:
            config: 配置对象
        """
        self._config = config
        self._api_base_url = config.api_base_url.rstrip("/")
        self._api_key = config.api_key
        self._model = config.model
        self._max_tokens = config.max_tokens
        self._temperature = config.temperature

    def stream_chat(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """流式调用聊天 API。

        Args:
            messages: 消息列表

        Yields:
            响应文本片段

        Raises:
            APIError: API 调用失败时抛出
        """
        url = f"{self._api_base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        data = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
        }

        body = json.dumps(data).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")

            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    error_msg = self._parse_error_response(response)
                    raise APIError(f"HTTP {response.status}: {error_msg}")

                # 处理流式响应
                for line in response:
                    line_text = line.decode("utf-8").strip()

                    if not line_text:
                        continue

                    if line_text.startswith("data: "):
                        data_str = line_text[6:]  # 移除 "data: " 前缀

                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield content
                        except json.JSONDecodeError:
                            # 忽略无效的 JSON
                            continue

        except urllib.error.HTTPError as e:
            error_msg = self._parse_http_error(e)
            raise APIError(error_msg)
        except urllib.error.URLError as e:
            raise APIError(f"Connection error: {e.reason}")
        except Exception as e:
            raise APIError(str(e))

    def _parse_error_response(self, response: Any) -> str:
        """解析错误响应。

        Args:
            response: HTTP 响应对象

        Returns:
            错误消息
        """
        try:
            body = response.read().decode("utf-8")
            error_data = json.loads(body)
            return error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            return "Unknown error"

    def _parse_http_error(self, error: urllib.error.HTTPError) -> str:
        """解析 HTTP 错误。

        Args:
            error: HTTP 错误对象

        Returns:
            错误消息
        """
        try:
            body = error.read().decode("utf-8")
            error_data = json.loads(body)

            # 处理 OpenAI 格式的错误
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    error_type = error_info.get("type", "")
                    error_message = error_info.get("message", "")

                    # 认证错误
                    if error.code == 401 or "invalid" in error_type.lower():
                        return f"Authentication failed: {error_message}"

                    return error_message

            return f"HTTP {error.code}: {body}"
        except Exception:
            return f"HTTP {error.code}: {error.reason}"
