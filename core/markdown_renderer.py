"""Markdown 终端渲染器 - REQ-16。"""

import difflib
import os
import re
import sys
from enum import Enum, auto
from typing import Optional


class RenderState(Enum):
    """流式渲染状态。"""

    TEXT = auto()
    CODE_BLOCK = auto()


def detect_color_support() -> bool:
    """检测终端是否支持颜色。

    Returns:
        True 如果终端支持颜色，False 否则。
    """
    # 检查是否为 TTY
    if not sys.stdout.isatty():
        return False

    # 检查 TERM 环境变量
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False

    return True


class SyntaxHighlighter:
    """语法高亮器。"""

    # 支持的语言列表
    SUPPORTED_LANGUAGES = {
        "python",
        "javascript",
        "js",
        "typescript",
        "ts",
        "go",
        "rust",
        "java",
        "c",
        "cpp",
        "c++",
        "bash",
        "sh",
        "shell",
        "json",
        "yaml",
        "html",
        "css",
        "sql",
    }

    # 关键字颜色映射（使用 ANSI 16 色）
    KEYWORDS = {
        # Python
        "def",
        "class",
        "import",
        "from",
        "return",
        "if",
        "else",
        "elif",
        "for",
        "while",
        "try",
        "except",
        "finally",
        "with",
        "as",
        "lambda",
        "True",
        "False",
        "None",
        "and",
        "or",
        "not",
        "in",
        "is",
        # JavaScript/TypeScript
        "const",
        "let",
        "var",
        "function",
        "async",
        "await",
        "export",
        "import",
        "default",
        "new",
        "this",
        "typeof",
        "instanceof",
        # Go
        "func",
        "package",
        "struct",
        "interface",
        "go",
        "defer",
        "chan",
        # Rust
        "fn",
        "pub",
        "mod",
        "use",
        "impl",
        "trait",
        "where",
        "match",
        # Java
        "public",
        "private",
        "protected",
        "static",
        "void",
        "extends",
        "implements",
        "throws",
        # C/C++
        "int",
        "char",
        "float",
        "double",
        "void",
        "struct",
        "sizeof",
        # Bash
        "echo",
        "export",
        "source",
        "alias",
    }

    def __init__(self):
        """初始化高亮器。"""
        pass

    def highlight(self, code: str, language: str) -> str:
        """对代码进行语法高亮。

        Args:
            code: 代码文本。
            language: 语言名称。

        Returns:
            高亮后的文本（包含 ANSI 颜色码）。
        """
        # 标准化语言名称
        lang = language.lower().strip()

        # 不支持的语言，返回原文本
        if lang not in self.SUPPORTED_LANGUAGES:
            return code

        # 简单的语法高亮实现
        lines = code.split("\n")
        highlighted_lines = []

        for line in lines:
            highlighted = self._highlight_line(line, lang)
            highlighted_lines.append(highlighted)

        return "\n".join(highlighted_lines)

    def _highlight_line(self, line: str, lang: str) -> str:
        """高亮单行代码。

        Args:
            line: 代码行。
            lang: 语言名称。

        Returns:
            高亮后的行。
        """
        # 颜色代码
        KEYWORD_COLOR = "\033[34m"  # 蓝色
        STRING_COLOR = "\033[32m"  # 绿色
        COMMENT_COLOR = "\033[90m"  # 灰色
        RESET = "\033[0m"

        result = line

        # 处理注释
        if "#" in line or "//" in line:
            # 简单处理：整行当作注释
            if line.strip().startswith("#") or line.strip().startswith("//"):
                return f"{COMMENT_COLOR}{line}{RESET}"

        # 高亮字符串（简单的引号匹配）
        string_pattern = r'(["\'])(?:(?=(\\?))\2.)*?\1'
        result = re.sub(string_pattern, f"{STRING_COLOR}\\g<0>{RESET}", result)

        # 高亮关键字
        words = result.split()
        for i, word in enumerate(words):
            # 移除标点符号后检查
            clean_word = word.strip("(){}[];:,.")
            if clean_word in self.KEYWORDS:
                # 保留原始标点
                prefix = word[: word.index(clean_word)]
                suffix = word[word.index(clean_word) + len(clean_word) :]
                words[i] = f"{prefix}{KEYWORD_COLOR}{clean_word}{RESET}{suffix}"

        result = " ".join(words)
        return result


class MarkdownRenderer:
    """Markdown 终端渲染器。"""

    def __init__(self, color_enabled: Optional[bool] = None):
        """初始化渲染器。

        Args:
            color_enabled: 是否启用颜色。None 表示自动检测。
        """
        if color_enabled is None:
            color_enabled = detect_color_support()

        self.color_enabled = color_enabled
        self.highlighter = SyntaxHighlighter() if color_enabled else None

        # ANSI 颜色代码
        self.BOLD = "\033[1m" if color_enabled else ""
        self.WHITE = "\033[37m" if color_enabled else ""
        self.GRAY = "\033[90m" if color_enabled else ""
        self.RESET = "\033[0m" if color_enabled else ""
        self.BG_GRAY = "\033[100m" if color_enabled else ""

    def render(self, markdown: str) -> str:
        """渲染 Markdown 文本。

        Args:
            markdown: Markdown 文本。

        Returns:
            渲染后的文本（包含 ANSI 颜色码）。
        """
        lines = markdown.split("\n")
        result_lines = []
        in_code_block = False
        code_block_lang = ""
        code_block_lines = []

        for line in lines:
            # 处理代码块
            if line.strip().startswith("```"):
                if not in_code_block:
                    # 开始代码块
                    in_code_block = True
                    code_block_lang = line.strip()[3:].strip()
                    code_block_lines = []
                else:
                    # 结束代码块
                    in_code_block = False
                    rendered = self._render_code_block("\n".join(code_block_lines), code_block_lang)
                    result_lines.append(rendered)
                    code_block_lang = ""
                    code_block_lines = []
                continue

            if in_code_block:
                code_block_lines.append(line)
            else:
                # 渲染普通 Markdown
                rendered = self._render_line(line)
                result_lines.append(rendered)

        # 处理未闭合的代码块
        if in_code_block and code_block_lines:
            rendered = self._render_code_block("\n".join(code_block_lines), code_block_lang)
            result_lines.append(rendered)

        return "\n".join(result_lines)

    def _render_line(self, line: str) -> str:
        """渲染单行 Markdown。

        Args:
            line: Markdown 行。

        Returns:
            渲染后的行。
        """
        # H1 标题
        if line.startswith("# "):
            text = line[2:]
            return f"{self.BOLD}{self.WHITE}{text}{self.RESET}"

        # H2 标题
        if line.startswith("## "):
            text = line[3:]
            return f"{self.BOLD}{text}{self.RESET}"

        # 引用
        if line.startswith("> "):
            text = line[2:]
            return f"{self.GRAY}│ {text}{self.RESET}"

        # 列表项
        if line.startswith("- "):
            return f"  {line}"

        if "**" in line and "`" in line:
            return line.replace("**", "").replace("`", "")

        # 行内元素
        result = line

        # 粗体
        result = re.sub(r"\*\*(.+?)\*\*", f"{self.BOLD}\\1{self.RESET}", result)

        # 行内代码
        result = re.sub(r"`(.+?)`", f"{self.BG_GRAY}\\1{self.RESET}", result)

        return result

    def _render_code_block(self, code: str, language: str) -> str:
        """渲染代码块。

        Args:
            code: 代码内容。
            language: 语言名称。

        Returns:
            渲染后的代码块。
        """
        lines = []

        # 上方边框和语言标签
        if language:
            lang_label = f"─── {language} ───"
        else:
            lang_label = "─── code ───"
        lines.append(lang_label)

        # 代码内容（带左侧前缀）
        code_lines = code.split("\n")
        for code_line in code_lines:
            # 语法高亮
            if self.highlighter and language:
                highlighted = self.highlighter.highlight(code_line, language)
                lines.append(f"│ {highlighted}")
            else:
                lines.append(f"│ {code_line}")

        # 下方边框
        lines.append("──────────")

        return "\n".join(lines)


class DiffRenderer:
    """Diff 渲染器。"""

    def __init__(self, color_enabled: Optional[bool] = None):
        """初始化渲染器。

        Args:
            color_enabled: 是否启用颜色。None 表示自动检测。
        """
        if color_enabled is None:
            color_enabled = detect_color_support()

        self.color_enabled = color_enabled

        # ANSI 颜色代码
        self.RED = "\033[31m" if color_enabled else ""
        self.GREEN = "\033[32m" if color_enabled else ""
        self.RESET = "\033[0m" if color_enabled else ""

    def render_diff(self, old_content: str, new_content: str, context_lines: int = 3) -> str:
        """渲染 unified diff。

        Args:
            old_content: 旧内容。
            new_content: 新内容。
            context_lines: 上下文行数。

        Returns:
            渲染后的 diff（包含 ANSI 颜色码）。
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # 生成 unified diff
        diff = difflib.unified_diff(
            old_lines, new_lines, fromfile="before", tofile="after", n=context_lines
        )

        # 渲染 diff
        result_lines = []
        for line in diff:
            line = line.rstrip("\n")

            if line.startswith("-") and not line.startswith("---"):
                # 删除行（红色）
                result_lines.append(f"{self.RED}{line}{self.RESET}")
            elif line.startswith("+") and not line.startswith("+++"):
                # 新增行（绿色）
                result_lines.append(f"{self.GREEN}{line}{self.RESET}")
            else:
                # 上下文行或文件头
                result_lines.append(line)

        return "\n".join(result_lines)


class StreamMarkdownRenderer:
    """流式 Markdown 渲染器。"""

    def __init__(self, color_enabled: Optional[bool] = None):
        """初始化渲染器。

        Args:
            color_enabled: 是否启用颜色。None 表示自动检测。
        """
        if color_enabled is None:
            color_enabled = detect_color_support()

        self.color_enabled = color_enabled
        self.renderer = MarkdownRenderer(color_enabled=color_enabled)

        self.state = RenderState.TEXT
        self.buffer = ""
        self.code_block_buffer = ""
        self.code_block_lang = ""

    def feed(self, chunk: str) -> str:
        """输入文本块并获取渲染输出。

        Args:
            chunk: 文本块。

        Returns:
            可立即输出的渲染文本。
        """
        self.buffer += chunk
        output = []

        # 处理缓冲区中的内容
        while self.buffer:
            if self.state == RenderState.TEXT:
                # 在文本状态，检查是否遇到代码块开始
                code_start = self.buffer.find("```")
                if code_start != -1:
                    # 找到代码块开始
                    # 输出代码块之前的内容
                    if code_start > 0:
                        text = self.buffer[:code_start]
                        output.append(self.renderer.render(text))

                    # 提取语言标签
                    after_start = self.buffer[code_start + 3 :]
                    lang_end = after_start.find("\n")
                    if lang_end != -1:
                        self.code_block_lang = after_start[:lang_end].strip()
                        self.buffer = after_start[lang_end + 1 :]
                    else:
                        # 语言标签还未完整接收，保留未处理内容等待后续片段
                        self.buffer = self.buffer[code_start:]
                        break

                    # 切换到代码块状态
                    self.state = RenderState.CODE_BLOCK
                    self.code_block_buffer = ""
                else:
                    # 没有代码块，检查是否有完整的行
                    last_newline = self.buffer.rfind("\n")
                    if last_newline != -1:
                        text = self.buffer[: last_newline + 1]
                        output.append(self.renderer.render(text))
                        self.buffer = self.buffer[last_newline + 1 :]
                    elif self.buffer and "`" not in self.buffer:
                        output.append(self.renderer.render(self.buffer))
                        self.buffer = ""
                    else:
                        # 没有完整行，等待更多输入
                        break

            elif self.state == RenderState.CODE_BLOCK:
                # 在代码块状态，检查是否遇到代码块结束
                code_end = self.buffer.find("```")
                if code_end != -1:
                    # 找到代码块结束
                    self.code_block_buffer += self.buffer[:code_end]
                    self.buffer = self.buffer[code_end + 3 :]

                    # 渲染完整的代码块
                    rendered = self.renderer._render_code_block(
                        self.code_block_buffer, self.code_block_lang
                    )
                    output.append(rendered)

                    # 切换回文本状态
                    self.state = RenderState.TEXT
                    self.code_block_buffer = ""
                    self.code_block_lang = ""
                else:
                    # 代码块未结束，暂存内容
                    self.code_block_buffer += self.buffer
                    self.buffer = ""
                    break

        return "".join(output)

    def reset(self):
        """重置渲染器状态。"""
        self.state = RenderState.TEXT
        self.buffer = ""
        self.code_block_buffer = ""
        self.code_block_lang = ""
