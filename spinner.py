"""
REQ-17: Spinner 动画

实现终端旋转动画，用于显示 AI 思考和工具执行状态。
"""

from typing import List


class Spinner:
    """
    Spinner 动画管理器

    使用 braille spinner 字符序列实现旋转动画
    """

    # Braille spinner 字符序列
    BRAILLE_FRAMES: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        """初始化 Spinner"""
        self._current_index = 0

    def get_frames(self) -> List[str]:
        """
        获取 spinner 帧序列

        Returns:
            braille 字符列表
        """
        return self.BRAILLE_FRAMES.copy()

    def get_next_frame(self) -> str:
        """
        获取下一帧字符

        Returns:
            当前帧的 braille 字符
        """
        frame = self.BRAILLE_FRAMES[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.BRAILLE_FRAMES)
        return frame

    def format_message(self, action: str, tool_name: str = None) -> str:
        """
        格式化带动画的消息

        Args:
            action: 动作类型（"Thinking" 或 "Running"）
            tool_name: 工具名称（可选）

        Returns:
            格式化的消息，如 "⠋ Thinking..." 或 "⠋ Running read_file..."
        """
        frame = self.get_next_frame()

        if tool_name:
            return f"{frame} {action} {tool_name}..."
        else:
            return f"{frame} {action}..."

    def get_clear_sequence(self) -> str:
        """
        获取清除动画的控制序列

        使用 \\r + 空格覆盖当前行

        Returns:
            清除控制序列
        """
        # \r 回到行首，然后用空格覆盖整行（假设终端宽度80）
        return "\r" + " " * 80 + "\r"

    def reset(self) -> None:
        """重置 spinner 到初始状态"""
        self._current_index = 0
