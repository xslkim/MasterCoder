"""消息管理器 - 管理对话消息历史和上下文截断。"""


class MessageManager:
    """消息管理器，处理对话消息的添加、获取和截断。"""

    def __init__(self, max_messages: int = 100) -> None:
        """初始化消息管理器。

        Args:
            max_messages: 最大消息数量，超过时触发截断
        """
        self._messages: list[dict[str, str]] = []
        self._max_messages = max_messages
        self._was_truncated = False

    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史记录。

        Args:
            role: 消息角色（system, user, assistant）
            content: 消息内容
        """
        self._messages.append({"role": role, "content": content})

    def get_messages(self) -> list[dict[str, str]]:
        """获取所有消息。

        Returns:
            消息列表
        """
        return self._messages.copy()

    def prepare_messages(self) -> list[dict[str, str]]:
        """准备发送给 API 的消息列表，包括截断处理。

        Returns:
            处理后的消息列表
        """
        if len(self._messages) <= self._max_messages:
            return self._messages.copy()

        # 截断逻辑：保留 system 消息和最近的对话
        system_messages = [msg for msg in self._messages if msg["role"] == "system"]
        other_messages = [msg for msg in self._messages if msg["role"] != "system"]

        # 保留最近的非 system 消息
        keep_count = self._max_messages - len(system_messages)
        truncated_other = other_messages[-keep_count:] if keep_count > 0 else []

        self._was_truncated = True
        return system_messages + truncated_other

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
        """清空所有消息。"""
        self._messages.clear()
        self._was_truncated = False

    def count(self) -> int:
        """获取消息数量。

        Returns:
            消息总数
        """
        return len(self._messages)

    def get_last_message(self) -> dict[str, str] | None:
        """获取最后一条消息。

        Returns:
            最后一条消息，如果没有消息则返回 None
        """
        if not self._messages:
            return None
        return self._messages[-1].copy()
