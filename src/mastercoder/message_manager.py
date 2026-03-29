"""消息管理器 - 管理对话消息历史和上下文截断。"""

from typing import Any


class MessageManager:
    """消息管理器，处理对话消息的添加、获取和截断。"""

    def __init__(self, max_messages: int = 100) -> None:
        """初始化消息管理器。

        Args:
            max_messages: 最大消息数量，超过时触发截断
        """
        self._messages: list[dict[str, Any]] = []
        self._max_messages = max_messages
        self._was_truncated = False

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """添加消息到历史记录。

        Args:
            role: 消息角色（system, user, assistant, tool）
            content: 消息内容
            tool_calls: 工具调用列表（仅 assistant 角色）
            tool_call_id: 工具调用 ID（仅 tool 角色）
        """
        message: dict[str, Any] = {"role": role, "content": content}

        if tool_calls is not None:
            message["tool_calls"] = tool_calls

        if tool_call_id is not None:
            message["tool_call_id"] = tool_call_id

        self._messages.append(message)

    def get_messages(self) -> list[dict[str, Any]]:
        """获取所有消息。

        Returns:
            消息列表
        """
        return self._messages.copy()

    def prepare_messages(
        self, max_context_tokens: int | None = None
    ) -> tuple[list[dict[str, Any]], bool]:
        """准备发送给 API 的消息列表，包括截断处理。

        Args:
            max_context_tokens: 最大上下文 token 数（可选）

        Returns:
            (处理后的消息列表, 是否发生截断)
        """
        # 简化实现：基于消息数量而非 token 数
        if len(self._messages) <= self._max_messages:
            return self._messages.copy(), False

        # 截断逻辑：保留 system 消息和最近的对话
        system_messages = [msg for msg in self._messages if msg["role"] == "system"]
        other_messages = [msg for msg in self._messages if msg["role"] != "system"]

        # 保留最近的非 system 消息
        keep_count = self._max_messages - len(system_messages)
        truncated_other = other_messages[-keep_count:] if keep_count > 0 else []

        self._was_truncated = True
        return system_messages + truncated_other, True

    def was_truncated(self) -> bool:
        """检查是否发生了截断。

        Returns:
            是否发生截断
        """
        return self._was_truncated

    def clear_truncation_flag(self) -> None:
        """清除截断标志。"""
        self._was_truncated = False

    def clear(self) -> None:
        """清空所有消息（保留 system 消息）。"""
        # 保留 system 消息
        system_messages = [msg for msg in self._messages if msg["role"] == "system"]
        self._messages = system_messages
        self._was_truncated = False

    def count(self) -> int:
        """获取消息数量。

        Returns:
            消息总数
        """
        return len(self._messages)

    def get_last_message(self) -> dict[str, Any] | None:
        """获取最后一条消息。

        Returns:
            最后一条消息，如果没有消息则返回 None
        """
        if not self._messages:
            return None
        return self._messages[-1].copy()

    def get_token_estimate(self) -> int:
        """估算当前消息列表的 token 数。

        Returns:
            估算的 token 数（字符数 / 4）
        """
        total_chars = 0
        for msg in self._messages:
            content = msg.get("content", "")
            total_chars += len(content)
        return total_chars // 4
