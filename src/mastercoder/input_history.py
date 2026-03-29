"""
REQ-21：输入历史管理模块
"""

from typing import Optional, List


class InputHistory:
    """输入历史管理器"""

    def __init__(self, max_size: int = 100):
        """
        初始化输入历史

        Args:
            max_size: 最多保存的历史条数
        """
        self.max_size = max_size
        self._history: List[str] = []
        self._position: int = -1  # -1 表示未开始导航

    def add(self, input_text: str) -> None:
        """
        添加输入到历史

        Args:
            input_text: 用户输入文本
        """
        # 不保存空输入
        if not input_text or not input_text.strip():
            return

        # 不保存斜杠命令
        if input_text.strip().startswith("/"):
            return

        # 添加到历史
        self._history.append(input_text)

        # 如果超过最大数量，移除最旧的
        if len(self._history) > self.max_size:
            self._history.pop(0)

        # 重置导航位置
        self._position = -1

    def get_previous(self) -> Optional[str]:
        """
        获取上一条历史记录

        Returns:
            上一条历史，如果没有则返回 None
        """
        if not self._history:
            return None

        # 从最新的开始
        if self._position == -1:
            self._position = len(self._history) - 1
        else:
            self._position = max(0, self._position - 1)

        if 0 <= self._position < len(self._history):
            return self._history[self._position]

        return None

    def get_next(self) -> Optional[str]:
        """
        获取下一条历史记录

        Returns:
            下一条历史，如果已经到达最新则返回 None
        """
        if not self._history or self._position == -1:
            return None

        self._position += 1

        if self._position >= len(self._history):
            self._position = -1
            return None

        return self._history[self._position]

    def reset_position(self) -> None:
        """重置导航位置"""
        self._position = -1

    def get_all(self) -> List[str]:
        """
        获取所有历史记录

        Returns:
            历史记录列表
        """
        return self._history.copy()
