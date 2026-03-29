"""
REQ-17: Token 统计

跟踪和显示 API Token 使用情况。
"""


class TokenStats:
    """
    Token 统计管理器

    跟踪单轮和多轮对话的 token 使用情况
    """

    def __init__(self):
        """初始化 token 统计器"""
        # 使用 Python int（64位整数）存储，支持大数值
        self._session_prompt_tokens: int = 0
        self._session_completion_tokens: int = 0
        self._round_prompt_tokens: int = 0
        self._round_completion_tokens: int = 0

    def add_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """
        添加 token 使用量

        Args:
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
        """
        # 累加到当前轮次
        self._round_prompt_tokens += prompt_tokens
        self._round_completion_tokens += completion_tokens

        # 累加到会话总计
        self._session_prompt_tokens += prompt_tokens
        self._session_completion_tokens += completion_tokens

    def next_round(self) -> None:
        """
        进入下一轮对话，重置轮次统计
        """
        self._round_prompt_tokens = 0
        self._round_completion_tokens = 0

    def get_round_prompt_tokens(self) -> int:
        """获取当前轮次的输入 token 数"""
        return self._round_prompt_tokens

    def get_round_completion_tokens(self) -> int:
        """获取当前轮次的输出 token 数"""
        return self._round_completion_tokens

    def get_session_prompt_tokens(self) -> int:
        """获取会话累计的输入 token 数"""
        return self._session_prompt_tokens

    def get_session_completion_tokens(self) -> int:
        """获取会话累计的输出 token 数"""
        return self._session_completion_tokens

    def format_stats(self, estimated: bool = False) -> str:
        """
        格式化 token 统计信息

        Args:
            estimated: 是否使用估算值（无 API usage 数据时）

        Returns:
            格式化的统计字符串，如 "[tokens: ↑1234 ↓567 | total: ↑5000 ↓2000]"
        """
        if estimated and self._round_prompt_tokens == 0 and self._round_completion_tokens == 0:
            return "[tokens: estimated]"

        round_prompt = self._round_prompt_tokens
        round_completion = self._round_completion_tokens
        session_prompt = self._session_prompt_tokens
        session_completion = self._session_completion_tokens

        return (
            f"[tokens: ↑{round_prompt} ↓{round_completion} | "
            f"total: ↑{session_prompt} ↓{session_completion}]"
        )

    def reset(self) -> None:
        """重置所有统计"""
        self._session_prompt_tokens = 0
        self._session_completion_tokens = 0
        self._round_prompt_tokens = 0
        self._round_completion_tokens = 0
