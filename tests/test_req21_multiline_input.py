"""
REQ-21：多行输入与输入历史 - 单元测试
"""
from src.input_handler import InputHandler, InputHistory


class TestInputHistory:
    """输入历史管理测试"""

    def test_add_and_retrieve_history(self):
        """测试添加和检索历史"""
        history = InputHistory(max_size=100)
        history.add("hello world")
        history.add("second input")

        assert history.navigate_up() == "second input"
        assert history.navigate_up() == "hello world"

    def test_history_max_size_100(self):
        """测试历史最多保存100条，超过后淘汰最旧的"""
        history = InputHistory(max_size=100)

        # 添加150条记录
        for i in range(150):
            history.add(f"input {i}")

        # 验证只保留最近100条
        assert len(history) == 100
        # 最早的应该是 input 50
        assert history.get(0) == "input 50"
        # 最新的应该是 input 149
        assert history.get(-1) == "input 149"

    def test_history_no_slash_commands(self):
        """测试斜杠命令不存入历史"""
        history = InputHistory(max_size=100)
        history.add("normal input")
        history.add("/help")
        history.add("/clear")
        history.add("another input")

        # 应该只有2条非斜杠命令
        assert len(history) == 2
        assert history.get(0) == "normal input"
        assert history.get(1) == "another input"

    def test_history_no_empty_input(self):
        """测试空输入不存入历史"""
        history = InputHistory(max_size=100)
        history.add("")
        history.add("   ")  # 纯空格
        history.add("valid input")

        assert len(history) == 1
        assert history.get(0) == "valid input"

    def test_navigate_up_down(self):
        """测试上下箭头导航"""
        history = InputHistory(max_size=100)
        history.add("first")
        history.add("second")
        history.add("third")

        # 向上导航
        assert history.navigate_up() == "third"
        assert history.navigate_up() == "second"
        assert history.navigate_up() == "first"
        # 到达最旧后继续向上应该返回最旧的
        assert history.navigate_up() == "first"

    def test_reset_navigation(self):
        """测试重置导航位置"""
        history = InputHistory(max_size=100)
        history.add("first")
        history.add("second")

        # 导航到第一条
        history.navigate_up()
        history.navigate_up()

        # 继续向下导航
        result = history.navigate_down()
        # 应该能回到更新的历史
        assert result in ["second", ""]


class TestMultilineInput:
    """多行输入测试"""

    def test_backslash_continuation(self):
        """测试反斜杠 + Enter 触发续行"""
        handler = InputHandler()

        # 模拟输入 "hello\" + Enter
        result = handler.process_line("hello\\")
        assert result.is_continuation
        assert handler.is_multiline_mode()
        assert result.prompt == "... "

    def test_multiline_content_assembly(self):
        """测试多行内容完整组装"""
        handler = InputHandler()

        # 第一行
        result1 = handler.process_line("帮我写一个函数\\")
        assert result1.is_continuation

        # 第二行
        result2 = handler.process_line("要求输入是字符串\\")
        assert result2.is_continuation

        # 第三行（无反斜杠，提交）
        result3 = handler.process_line("输出是反转后的字符串")
        assert not result3.is_continuation
        assert result3.should_submit
        expected = "帮我写一个函数\n要求输入是字符串\n输出是反转后的字符串"
        assert result3.content == expected
        assert not handler.is_multiline_mode()

    def test_single_line_submit(self):
        """测试单行直接提交"""
        handler = InputHandler()

        result = handler.process_line("hello world")
        assert not result.is_continuation
        assert result.should_submit
        assert result.content == "hello world"
        assert not handler.is_multiline_mode()

    def test_cancel_multiline_with_ctrl_c(self):
        """测试多行模式下 Ctrl+C 取消"""
        handler = InputHandler()

        # 进入多行模式
        handler.process_line("line 1\\")
        assert handler.is_multiline_mode()

        # 取消
        handler.cancel_input()
        assert not handler.is_multiline_mode()
        assert handler.get_buffer() == ""

    def test_multiline_with_empty_lines(self):
        """测试多行输入包含空行"""
        handler = InputHandler()

        handler.process_line("line 1\\")
        handler.process_line("\\")  # 空行
        result = handler.process_line("line 3")

        assert result.content == "line 1\n\nline 3"


class TestBracketedPasteMode:
    """Bracketed paste mode 测试"""

    def test_detect_paste_start(self):
        """检测粘贴开始序列"""
        handler = InputHandler()

        # Bracketed paste start: \x1b[200~
        assert handler.detect_paste_start("\x1b[200~")
        assert not handler.detect_paste_start("normal text")

    def test_detect_paste_end(self):
        """检测粘贴结束序列"""
        handler = InputHandler()

        # Bracketed paste end: \x1b[201~
        assert handler.detect_paste_end("\x1b[201~")
        assert not handler.detect_paste_end("normal text")

    def test_paste_multiline_not_submitted(self):
        """测试粘贴的多行文本不会逐行提交"""
        handler = InputHandler()

        # 模拟粘贴多行文本
        pasted_text = "line 1\nline 2\nline 3"

        # 处理粘贴
        result = handler.handle_paste(pasted_text)

        # 应该返回完整的多行文本，而不是逐行提交
        assert not result.should_submit
        assert result.display_text == pasted_text
        assert not handler.is_multiline_mode()
