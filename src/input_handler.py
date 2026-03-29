"""
REQ-21: 多行输入与输入历史处理模块
"""

from collections import deque
from typing import Optional


class ProcessResult:
    """处理单行输入的结果"""

    def __init__(
        self,
        is_continuation: bool = False,
        should_submit: bool = False,
        prompt: str = "> ",
        content: str = "",
    ):
        self.is_continuation = is_continuation
        self.should_submit = should_submit
        self.prompt = prompt
        self.content = content


class PasteResult:
    """处理粘贴的结果"""

    def __init__(self, should_submit: bool = False, display_text: str = ""):
        self.should_submit = should_submit
        self.display_text = display_text


class InputHistory:
    """输入历史管理"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._history: deque = deque(maxlen=max_size)
        self._current_index: int = -1

    def add(self, input_text: str) -> None:
        """添加输入到历史"""
        # 不保存空输入或仅空白字符的输入
        if not input_text or not input_text.strip():
            return

        # 不保存斜杠命令（以 / 开头的）
        if input_text.strip().startswith("/"):
            return

        self._history.append(input_text)
        # 重置导航索引
        self._current_index = len(self._history)

    def __len__(self) -> int:
        return len(self._history)

    def get(self, index: int) -> Optional[str]:
        """获取历史记录（支持负索引）"""
        if len(self._history) == 0:
            return None

        try:
            return self._history[index]
        except IndexError:
            return None

    def navigate_up(self) -> Optional[str]:
        """向上导航（更旧的历史）"""
        if len(self._history) == 0:
            return None

        if self._current_index > 0:
            self._current_index -= 1

        return self._history[self._current_index]

    def navigate_down(self) -> Optional[str]:
        """向下导航（更新的历史）"""
        if len(self._history) == 0:
            return None

        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            return self._history[self._current_index]
        else:
            # 到达最新后，返回空字符串
            self._current_index = len(self._history)
            return ""


class InputHandler:
    """多行输入处理器"""

    # Bracketed paste mode 转义序列
    PASTE_START = "\x1b[200~"
    PASTE_END = "\x1b[201~"

    def __init__(self):
        self._multiline_buffer: list = []
        self._is_multiline: bool = False
        self._is_paste_mode: bool = False

    def process_line(self, line: str) -> ProcessResult:
        """处理单行输入"""
        # 检查是否是续行（以 \ 结尾）
        if line.rstrip().endswith("\\"):
            # 移除末尾的反斜杠，添加到缓冲区
            content = line.rstrip()[:-1]
            self._multiline_buffer.append(content)
            self._is_multiline = True
            return ProcessResult(is_continuation=True, prompt="... ", content=content + "\n")
        else:
            # 非续行
            if self._is_multiline:
                # 多行模式下的最后一行
                self._multiline_buffer.append(line)
                full_content = "\n".join(self._multiline_buffer)
                self._multiline_buffer = []
                self._is_multiline = False
                return ProcessResult(
                    is_continuation=False, should_submit=True, prompt="> ", content=full_content
                )
            else:
                # 单行模式，直接提交
                return ProcessResult(
                    is_continuation=False, should_submit=True, prompt="> ", content=line
                )

    def is_multiline_mode(self) -> bool:
        """是否处于多行输入模式"""
        return self._is_multiline

    def get_buffer(self) -> str:
        """获取当前缓冲区内容"""
        return "\n".join(self._multiline_buffer)

    def cancel_input(self) -> None:
        """取消当前输入（Ctrl+C）"""
        self._multiline_buffer = []
        self._is_multiline = False

    def detect_paste_start(self, sequence: str) -> bool:
        """检测粘贴开始"""
        return sequence == self.PASTE_START

    def detect_paste_end(self, sequence: str) -> bool:
        """检测粘贴结束"""
        return sequence == self.PASTE_END

    def handle_paste(self, pasted_text: str) -> PasteResult:
        """处理粘贴的多行文本"""
        # 粘贴的文本不自动提交，直接显示在输入区域
        return PasteResult(should_submit=False, display_text=pasted_text)

    def enable_bracketed_paste(self) -> str:
        """启用 bracketed paste mode（返回终端转义序列）"""
        return "\x1b[?2004h"

    def disable_bracketed_paste(self) -> str:
        """禁用 bracketed paste mode（返回终端转义序列）"""
        return "\x1b[?2004l"
