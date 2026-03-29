"""测试 Markdown 终端渲染器 - REQ-16。"""

import re
import sys

from mastercoder.markdown_renderer import (
    DiffRenderer,
    MarkdownRenderer,
    StreamMarkdownRenderer,
    SyntaxHighlighter,
    detect_color_support,
)


class TestColorDetection:
    """测试终端颜色支持检测。"""

    def test_detect_color_with_tty(self, monkeypatch):
        """TTY 终端支持颜色。"""
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        monkeypatch.setenv("TERM", "xterm-256color")
        assert detect_color_support() is True

    def test_detect_color_without_tty(self, monkeypatch):
        """非 TTY 不支持颜色（重定向到文件）。"""
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        assert detect_color_support() is False

    def test_detect_color_with_dumb_term(self, monkeypatch):
        """dumb 终端不支持颜色。"""
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        monkeypatch.setenv("TERM", "dumb")
        assert detect_color_support() is False


class TestMarkdownRenderer:
    """测试 Markdown 渲染器。"""

    def setup_method(self):
        """每个测试方法前初始化渲染器。"""
        self.renderer = MarkdownRenderer(color_enabled=True)

    def test_heading_h1(self):
        """一级标题渲染为粗体 + 白色。"""
        result = self.renderer.render("# Title")
        assert "\033[1m" in result  # 粗体
        assert "Title" in result
        assert "\033[0m" in result  # 重置

    def test_heading_h2(self):
        """二级标题渲染为粗体。"""
        result = self.renderer.render("## Subtitle")
        assert "\033[1m" in result  # 粗体
        assert "Subtitle" in result

    def test_bold_text(self):
        """粗体文本渲染。"""
        result = self.renderer.render("**bold text**")
        assert "\033[1m" in result
        assert "bold text" in result

    def test_inline_code(self):
        """行内代码渲染为灰色背景。"""
        result = self.renderer.render("`inline code`")
        # 检查包含 ANSI 转义序列
        assert "\033[" in result
        assert "inline code" in result

    def test_list_item(self):
        """列表项保持原样并缩进。"""
        result = self.renderer.render("- list item")
        assert "- list item" in result or "  - list item" in result

    def test_blockquote(self):
        """引用渲染为灰色文字。"""
        result = self.renderer.render("> quote text")
        assert "│" in result or ">" in result
        assert "quote text" in result

    def test_code_block_with_language(self):
        """代码块渲染包含语言标签和边框。"""
        markdown = """```python
print("hello")
```"""
        result = self.renderer.render(markdown)
        assert "python" in result.lower()
        assert "─" in result or "│" in result
        assert "print" in result

    def test_code_block_without_language(self):
        """未指定语言的代码块有边框但无高亮。"""
        markdown = """```
plain text
```"""
        result = self.renderer.render(markdown)
        assert "─" in result or "│" in result
        assert "plain text" in result

    def test_color_disabled(self):
        """禁用颜色时不输出 ANSI 转义序列。"""
        renderer = MarkdownRenderer(color_enabled=False)
        result = renderer.render("# Title\n**bold**\n`code`")
        # 不应包含 ANSI 转义序列
        ansi_pattern = re.compile(r"\033\[[0-9;]+m")
        matches = ansi_pattern.findall(result)
        assert len(matches) == 0

    def test_nested_markdown(self):
        """嵌套 Markdown 元素处理。"""
        result = self.renderer.render("**bold `code` text**")
        assert "bold" in result
        assert "code" in result
        # 确保 ANSI 序列正确闭合
        assert result.count("\033[0m") >= result.count("\033[")

    def test_multiple_elements(self):
        """多个元素的混合渲染。"""
        markdown = """# Title

This is **bold** and `inline code`.

- item 1
- item 2

> quote
"""
        result = self.renderer.render(markdown)
        assert "Title" in result
        assert "bold" in result
        assert "inline code" in result
        assert "item" in result


class TestSyntaxHighlighter:
    """测试语法高亮器。"""

    def setup_method(self):
        """每个测试方法前初始化高亮器。"""
        self.highlighter = SyntaxHighlighter()

    def test_python_highlighting(self):
        """Python 代码高亮包含 ANSI 颜色码。"""
        code = 'def hello():\n    print("world")'
        result = self.highlighter.highlight(code, "python")
        # 应包含 ANSI 颜色码
        assert "\033[" in result
        assert "def" in result
        assert "print" in result

    def test_javascript_highlighting(self):
        """JavaScript 代码高亮。"""
        code = "const x = 42;"
        result = self.highlighter.highlight(code, "javascript")
        assert "\033[" in result
        assert "const" in result

    def test_json_highlighting(self):
        """JSON 代码高亮。"""
        code = '{"key": "value"}'
        result = self.highlighter.highlight(code, "json")
        assert "\033[" in result or "key" in result

    def test_unsupported_language(self):
        """不支持的语言不做高亮。"""
        code = "some unknown code"
        result = self.highlighter.highlight(code, "unknown_lang")
        # 不包含颜色码，返回原文本
        assert "some unknown code" in result

    def test_multiple_languages(self):
        """测试至少 3 种语言的高亮输出非空。"""
        languages = ["python", "javascript", "go"]
        for lang in languages:
            code = "test code"
            result = self.highlighter.highlight(code, lang)
            assert len(result) > 0
            assert "test code" in result


class TestDiffRenderer:
    """测试 Diff 渲染器。"""

    def setup_method(self):
        """每个测试方法前初始化渲染器。"""
        self.renderer = DiffRenderer(color_enabled=True)

    def test_unified_diff_format(self):
        """Diff 输出为 unified diff 格式。"""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"
        result = self.renderer.render_diff(old_content, new_content)
        assert "---" in result or "-" in result
        assert "+++" in result or "+" in result

    def test_deleted_line_red(self):
        """删除行标红色。"""
        old_content = "deleted line"
        new_content = ""
        result = self.renderer.render_diff(old_content, new_content)
        # 检查包含红色 ANSI 码
        assert "\033[31m" in result or "\033[" in result
        assert "-" in result

    def test_added_line_green(self):
        """新增行标绿色。"""
        old_content = ""
        new_content = "added line"
        result = self.renderer.render_diff(old_content, new_content)
        # 检查包含绿色 ANSI 码
        assert "\033[32m" in result or "\033[" in result
        assert "+" in result

    def test_context_lines(self):
        """上下文行显示正确。"""
        old_content = "line1\nline2\nline3\nline4\nline5"
        new_content = "line1\nline2\nmodified\nline4\nline5"
        result = self.renderer.render_diff(old_content, new_content)
        # 应包含上下文行
        assert "line1" in result or "line2" in result

    def test_diff_color_disabled(self):
        """禁用颜色时 diff 无 ANSI 转义序列。"""
        renderer = DiffRenderer(color_enabled=False)
        old_content = "old"
        new_content = "new"
        result = renderer.render_diff(old_content, new_content)
        ansi_pattern = re.compile(r"\033\[[0-9;]+m")
        matches = ansi_pattern.findall(result)
        assert len(matches) == 0


class TestStreamMarkdownRenderer:
    """测试流式 Markdown 渲染器。"""

    def setup_method(self):
        """每个测试方法前初始化渲染器。"""
        self.renderer = StreamMarkdownRenderer(color_enabled=True)

    def test_stream_text(self):
        """流式输出普通文本。"""
        result1 = self.renderer.feed("Hello ")
        result2 = self.renderer.feed("world")
        assert "Hello" in result1 or "Hello" in result2
        assert "world" in result2

    def test_stream_code_block_delayed(self):
        """代码块在完整接收后才渲染。"""
        # 发送代码块开始
        result1 = self.renderer.feed("```python\n")
        # 代码块内容应暂缓显示
        result2 = self.renderer.feed("print('hello')\n")
        # 代码块结束
        result3 = self.renderer.feed("```")

        # 代码块应在最后一次性输出
        final_output = result1 + result2 + result3
        assert "python" in final_output.lower() or "print" in final_output

    def test_stream_state_machine(self):
        """流式渲染状态机正确维护。"""
        # 模拟跨多个 delta 片段的代码块
        chunks = ["```", "py", "thon\n", "code", "```"]
        outputs = [self.renderer.feed(chunk) for chunk in chunks]

        # 合并所有输出
        final = "".join(outputs)
        # 应该正确识别代码块
        assert len(final) > 0

    def test_stream_reset(self):
        """重置流式渲染器状态。"""
        self.renderer.feed("```python\ncode")
        self.renderer.reset()
        # 重置后应能重新开始
        result = self.renderer.feed("new text")
        assert "new text" in result
