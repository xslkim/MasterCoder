"""
REQ-21：输入处理器模块 - 多行输入与历史管理
"""

from typing import Optional, List
from mastercoder.input_history import InputHistory


class InputHandler:
    """输入处理器 - 管理多行输入和历史"""

    # Bracketed paste mode 控制序列
    PASTE_START = "\x1b[200~"
    PASTE_END = "\x1b[201~"

    def __init__(self, history_max_size: int = 100):
        """
        初始化输入处理器

        Args:
            history_max_size: 历史记录最大数量
        """
        self.history = InputHistory(max_size=history_max_size)
        self._multiline_buffer: List[str] = []
        self._is_multiline: bool = False

    def process_input(self, input_text: str) -> Optional[str]:
        """
        处理用户输入

        Args:
            input_text: 用户输入的文本

        Returns:
            如果输入完成则返回完整内容，如果需要继续输入则返回 None
        """
        # 检查是否是多行模式的续行
        if self._is_multiline:
            # 检查是否继续续行
            if input_text.endswith("\\"):
                # 去掉反斜杠，添加到缓冲区
                self._multiline_buffer.append(input_text[:-1])
                return None
            else:
                # 最后一行，完成输入
                self._multiline_buffer.append(input_text)
                result = "\n".join(self._multiline_buffer)

                # 保存到历史
                self.history.add(result)

                # 重置多行模式
                self._multiline_buffer = []
                self._is_multiline = False

                return result
        else:
            # 单行模式
            # 检查是否进入多行模式（以反斜杠结尾）
            if input_text.endswith("\\"):
                # 进入多行模式
                self._multiline_buffer.append(input_text[:-1])
                self._is_multiline = True
                return None
            else:
                # 单行直接提交
                # 保存到历史
                self.history.add(input_text)
                return input_text

    def is_multiline_mode(self) -> bool:
        """
        检查是否处于多行模式

        Returns:
            True 如果正在多行输入
        """
        return self._is_multiline

    def get_continuation_prompt(self) -> str:
        """
        获取续行提示符

        Returns:
            续行提示符 "... "
        """
        return "... "

    def cancel_multiline(self) -> None:
        """取消当前多行输入"""
        self._multiline_buffer = []
        self._is_multiline = False

    def get_current_input(self) -> str:
        """
        获取当前已输入的内容

        Returns:
            当前输入缓冲区内容
        """
        return "\n".join(self._multiline_buffer)

    def get_history(self) -> List[str]:
        """
        获取历史记录

        Returns:
            历史记录列表
        """
        return self.history.get_all()

    def is_paste_start(self, text: str) -> bool:
        """
        检测是否是粘贴开始序列

        Args:
            text: 输入文本

        Returns:
            True 如果是粘贴开始序列
        """
        return text == self.PASTE_START

    def is_paste_end(self, text: str) -> bool:
        """
        检测是否是粘贴结束序列

        Args:
            text: 输入文本

        Returns:
            True 如果是粘贴结束序列
        """
        return text == self.PASTE_END

    def handle_paste(self, pasted_text: str) -> str:
        """
        处理粘贴的多行文本

        Args:
            pasted_text: 粘贴的文本

        Returns:
            处理后的文本（完整的多行内容）
        """
        # 粘贴的多行文本直接作为完整输入
        # 不逐行提交，直接返回完整内容
        # 保存到历史
        self.history.add(pasted_text)
        return pasted_text
