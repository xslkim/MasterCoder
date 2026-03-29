"""
REQ-21：多行输入与输入历史 - 单元测试
"""

import pytest
from mastercoder.input_handler import InputHandler
from mastercoder.input_history import InputHistory


class TestInputHistory:
    """输入历史管理测试"""

    def test_add_and_retrieve_history(self):
        """测试添加和检索历史"""
        history = InputHistory(max_size=100)
        history.add("hello world")
        history.add("second input")

        assert history.get_previous() == "second input"
        assert history.get_previous() == "hello world"

    def test_history_max_size_100(self):
        """测试历史最多保存100条，超过后淘汰最旧的"""
        history = InputHistory(max_size=100)

        # 添加101条记录
        for i in range(101):
            history.add(f"input {i}")

        # 验证只保留最近100条
        count = 0
        while history.get_previous() is not None:
            count += 1

        assert count == 100
        # 最早的 input 0 应该被淘汰了
        history.reset_position()
        first = history.get_previous()
        assert first == "input 100"  # 最新的一条

    def test_history_no_slash_commands(self):
        """测试斜杠命令不存入历史"""
        history = InputHistory(max_size=100)
        history.add("normal input")
        history.add("/help")
        history.add("/clear")
        history.add("another input")

        # 应该只有2条非斜杠命令
        history.reset_position()
        assert history.get_previous() == "another input"
        assert history.get_previous() == "normal input"
        assert history.get_previous() is None

    def test_history_no_empty_input(self):
        """测试空输入不存入历史"""
        history = InputHistory(max_size=100)
        history.add("")
        history.add("   ")  # 纯空格
        history.add("valid input")

        history.reset_position()
        assert history.get_previous() == "valid input"
        assert history.get_previous() is None

    def test_navigate_up_down(self):
        """测试上下箭头导航"""
        history = InputHistory(max_size=100)
        history.add("first")
        history.add("second")
        history.add("third")

        # 向上导航
        assert history.get_previous() == "third"
        assert history.get_previous() == "second"
        assert history.get_previous() == "first"
        assert history.get_previous() is None  # 到达最旧

        # 向下导航
        assert history.get_next() == "second"
        assert history.get_next() == "third"
        assert history.get_next() is None  # 到达最新

    def test_reset_position(self):
        """测试重置导航位置"""
        history = InputHistory(max_size=100)
        history.add("first")
        history.add("second")

        # 导航到第一条
        history.get_previous()
        history.get_previous()

        # 重置后应该能重新从最新开始
        history.reset_position()
        assert history.get_previous() == "second"


class TestMultilineInput:
    """多行输入测试"""

    def test_backslash_continuation(self):
        """测试反斜杠 + Enter 触发续行"""
        handler = InputHandler()

        # 模拟输入 "hello\" + Enter
        result = handler.process_input("hello\\")
        assert result is None  # 应该返回 None 表示继续输入
        assert handler.is_multiline_mode() is True
        assert handler.get_continuation_prompt() == "... "

    def test_multiline_content_assembly(self):
        """测试多行内容完整组装"""
        handler = InputHandler()

        # 第一行
        handler.process_input("帮我写一个函数\\")
        assert handler.is_multiline_mode() is True

        # 第二行
        handler.process_input("要求输入是字符串")
        assert handler.is_multiline_mode() is True

        # 第三行（无反斜杠，提交）
        result = handler.process_input("输出是反转后的字符串")

        assert result is not None
        expected = "帮我写一个函数\n要求输入是字符串\n输出是反转后的字符串"
        assert result == expected
        assert handler.is_multiline_mode() is False

    def test_single_line_submit(self):
        """测试单行直接提交"""
        handler = InputHandler()

        result = handler.process_input("hello world")
        assert result == "hello world"
        assert handler.is_multiline_mode() is False

    def test_cancel_multiline_with_ctrl_c(self):
        """测试多行模式下 Ctrl+C 取消"""
        handler = InputHandler()

        # 进入多行模式
        handler.process_input("line 1\\")
        assert handler.is_multiline_mode() is True

        # 取消
        handler.cancel_multiline()
        assert handler.is_multiline_mode() is False
        assert handler.get_current_input() == ""

    def test_multiline_with_empty_lines(self):
        """测试多行输入包含空行"""
        handler = InputHandler()

        handler.process_input("line 1\\")
        handler.process_input("\\")  # 空行
        result = handler.process_input("line 3")

        assert result == "line 1\n\nline 3"


class TestInputHandlerIntegration:
    """输入处理器集成测试"""

    def test_history_excludes_slash_commands(self):
        """测试历史不包含斜杠命令（集成测试）"""
        handler = InputHandler()

        # 提交普通输入
        handler.process_input("user message")
        # 提交斜杠命令
        handler.process_input("/help")
        # 提交另一个普通输入
        handler.process_input("another message")

        # 检查历史
        history = handler.get_history()
        assert len(history) == 2
        assert "user message" in history
        assert "another message" in history
        assert "/help" not in history

    def test_multiline_in_history(self):
        """测试多行输入正确保存到历史"""
        handler = InputHandler()

        # 输入多行
        handler.process_input("line 1\\")
        result = handler.process_input("line 2")

        assert result == "line 1\nline 2"

        # 检查历史
        history = handler.get_history()
        assert "line 1\nline 2" in history


class TestBracketedPasteMode:
    """Bracketed paste mode 测试"""

    def test_detect_paste_start(self):
        """检测粘贴开始序列"""
        handler = InputHandler()

        # Bracketed paste start: \x1b[200~
        assert handler.is_paste_start("\x1b[200~") is True
        assert handler.is_paste_start("normal text") is False

    def test_detect_paste_end(self):
        """检测粘贴结束序列"""
        handler = InputHandler()

        # Bracketed paste end: \x1b[201~
        assert handler.is_paste_end("\x1b[201~") is True
        assert handler.is_paste_end("normal text") is False

    def test_paste_multiline_not_submitted(self):
        """测试粘贴的多行文本不会逐行提交"""
        handler = InputHandler()

        # 模拟粘贴多行文本
        pasted_text = "line 1\nline 2\nline 3"

        # 处理粘贴
        result = handler.handle_paste(pasted_text)

        # 应该返回完整的多行文本，而不是逐行提交
        assert result == pasted_text
        assert handler.is_multiline_mode() is False
