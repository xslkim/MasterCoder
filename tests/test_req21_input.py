"""
REQ-21: 多行输入与输入历史测试
"""
from src.input_handler import InputHandler, InputHistory


class TestInputHistory:
    """输入历史管理测试"""

    def test_add_input_to_history(self):
        """测试添加输入到历史"""
        history = InputHistory()
        history.add("hello world")
        assert len(history) == 1
        assert history.get(-1) == "hello world"

    def test_history_max_100_items(self):
        """测试历史记录最多保存100条，超过后最旧的被淘汰"""
        history = InputHistory()
        for i in range(150):
            history.add(f"input {i}")

        assert len(history) == 100
        # 最旧的应该是 input 50（input 0-49 被淘汰）
        assert history.get(0) == "input 50"
        # 最新的应该是 input 149
        assert history.get(-1) == "input 149"

    def test_history_navigation_up(self):
        """测试按上箭头浏览历史"""
        history = InputHistory()
        history.add("first")
        history.add("second")
        history.add("third")

        # 从最新开始往上翻
        assert history.navigate_up() == "third"
        assert history.navigate_up() == "second"
        assert history.navigate_up() == "first"
        # 到最旧后继续往上应该返回最旧的
        assert history.navigate_up() == "first"

    def test_history_navigation_down(self):
        """测试按下箭头浏览历史"""
        history = InputHistory()
        history.add("first")
        history.add("second")
        history.add("third")

        # 先往上翻到最旧
        history.navigate_up()
        history.navigate_up()
        history.navigate_up()

        # 再往下翻
        assert history.navigate_down() == "second"
        assert history.navigate_down() == "third"
        # 到最新后继续往下应该返回空（或最新）
        assert history.navigate_down() == ""

    def test_slash_commands_not_saved(self):
        """测试斜杠命令不存入历史"""
        history = InputHistory()
        history.add("/help")
        history.add("normal input")
        history.add("/exit")
        history.add("another input")

        assert len(history) == 2
        assert history.get(0) == "normal input"
        assert history.get(1) == "another input"

    def test_empty_input_not_saved(self):
        """测试空输入不存入历史"""
        history = InputHistory()
        history.add("")
        history.add("   ")
        history.add("valid input")

        assert len(history) == 1
        assert history.get(0) == "valid input"


class TestMultilineInput:
    """多行输入测试"""

    def test_backslash_enter_triggers_continuation(self):
        """测试反斜杠+Enter触发换行"""
        handler = InputHandler()

        # 输入 "hello\" 后按 Enter 应该触发续行
        result = handler.process_line("hello\\")
        assert result.is_continuation
        assert result.prompt == "... "
        assert result.content == "hello\n"

    def test_multiline_submit_complete(self):
        """测试多行提交后内容完整"""
        handler = InputHandler()

        # 模拟多行输入
        lines = ["first line\\", "second line\\", "third line"]

        full_input = ""
        for line in lines:
            result = handler.process_line(line)
            if result.is_continuation:
                full_input += line.rstrip("\\") + "\n"
            else:
                full_input += line

        expected = "first line\nsecond line\nthird line"
        assert full_input == expected

    def test_enter_submits_input(self):
        """测试单独Enter提交输入"""
        handler = InputHandler()

        result = handler.process_line("single line")
        assert not result.is_continuation
        assert result.should_submit

    def test_ctrl_c_cancels_multiline(self):
        """测试Ctrl+C取消多行输入"""
        handler = InputHandler()

        # 开始多行输入
        handler.process_line("line 1\\")
        assert handler.is_multiline_mode()

        # Ctrl+C 取消
        handler.cancel_input()
        assert not handler.is_multiline_mode()
        assert handler.get_buffer() == ""


class TestBracketedPaste:
    """粘贴支持测试"""

    def test_detect_paste_mode(self):
        """测试检测粘贴模式"""
        handler = InputHandler()

        # 检测粘贴开始
        paste_detected = handler.detect_paste_start("\x1b[200~")
        assert paste_detected

        # 检测粘贴结束
        paste_ended = handler.detect_paste_end("\x1b[201~")
        assert paste_ended

    def test_multiline_paste_not_submitted(self):
        """测试粘贴多行文本不会自动提交"""
        handler = InputHandler()

        # 模拟粘贴多行文本
        pasted_text = "line 1\nline 2\nline 3"
        result = handler.handle_paste(pasted_text)

        # 不应该提交，应该在缓冲区中
        assert not result.should_submit
        assert result.display_text == pasted_text
