"""REQ-10: edit_file 工具测试。"""

import os
import tempfile
from pathlib import Path

from mastercoder.tools.edit_file import EditFileTool


class TestEditFile:
    """edit_file 工具测试类。"""

    def test_unique_match_replacement(self):
        """测试唯一匹配的成功替换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World\nThis is a test\nGoodbye everyone", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": "World", "new_string": "Universe"}
            )

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "Hello Universe\nThis is a test\nGoodbye everyone"

    def test_old_string_not_found(self):
        """测试未找到匹配。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": "Python", "new_string": "Java"}
            )

            assert result == "Error: old_string not found in file"

    def test_multiple_matches_error(self):
        """测试多处匹配报错。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World\nHello World\nHello World", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": "World", "new_string": "Universe"}
            )

            assert "Error: old_string has 3 matches" in result
            assert "must be unique" in result

    def test_identical_strings_error(self):
        """测试 old_string 与 new_string 相同。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": "World", "new_string": "World"}
            )

            assert result == "Error: old_string and new_string are identical"

    def test_file_not_found(self):
        """测试文件不存在。"""
        tool = EditFileTool()
        result = tool.execute(
            {"path": "/nonexistent/path/file.txt", "old_string": "old", "new_string": "new"}
        )

        assert "Error: File not found" in result

    def test_special_characters_newline(self):
        """测试包含换行符的匹配和替换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {
                    "path": str(test_file),
                    "old_string": "Line 1\nLine 2",
                    "new_string": "Replaced Line",
                }
            )

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "Replaced Line\nLine 3"

    def test_special_characters_tab(self):
        """测试包含 tab 字符的匹配和替换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello\tWorld", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute({"path": str(test_file), "old_string": "\t", "new_string": " "})

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "Hello World"

    def test_special_characters_quotes(self):
        """测试包含引号的匹配和替换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text('He said "Hello"', encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": '"Hello"', "new_string": "'Hi'"}
            )

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "He said 'Hi'"

    def test_case_sensitive_match(self):
        """测试区分大小写的精确匹配。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello hello HELLO", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {"path": str(test_file), "old_string": "hello", "new_string": "hi"}
            )

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "Hello hi HELLO"

    def test_whitespace_preservation(self):
        """测试空白字符的精确匹配。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("  indented line\nnormal line", encoding="utf-8")

            tool = EditFileTool()
            result = tool.execute(
                {
                    "path": str(test_file),
                    "old_string": "  indented line",
                    "new_string": "fixed line",
                }
            )

            assert result == f"Successfully edited {test_file}"
            content = test_file.read_text(encoding="utf-8")
            assert content == "fixed line\nnormal line"

    def test_relative_path(self):
        """测试相对路径处理。"""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                test_file = Path("test.txt")
                test_file.write_text("Hello World", encoding="utf-8")

                tool = EditFileTool()
                result = tool.execute(
                    {"path": "test.txt", "old_string": "World", "new_string": "Universe"}
                )

                assert "Successfully edited" in result
                content = test_file.read_text(encoding="utf-8")
                assert content == "Hello Universe"
            finally:
                os.chdir(original_cwd)
