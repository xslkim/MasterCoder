"""Tests for REQ-08 read_file tool."""

import os
import tempfile
from pathlib import Path

from mastercoder.tools.read_file import ReadFileTool


class TestReadFileTool:
    """Test cases for read_file tool implementation."""

    def test_read_normal_text_file(self):
        """Test reading a normal text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!\nThis is a test file.")
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert result.startswith("File:")
            assert "Hello, World!" in result
            assert "This is a test file." in result
        finally:
            os.unlink(temp_path)

    def test_read_file_with_relative_path(self):
        """Test reading a file using relative path."""
        # Create a temporary file in current directory
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create a subdirectory and file
            subdir = Path("subdir")
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("Content in subdirectory")

            try:
                tool = ReadFileTool()
                result = tool.execute({"path": "subdir/test.txt"})

                assert "Content in subdirectory" in result
                assert "File:" in result
            finally:
                os.chdir(original_cwd)

    def test_file_not_found(self):
        """Test error handling for non-existent file."""
        tool = ReadFileTool()
        result = tool.execute({"path": "/nonexistent/path/to/file.txt"})

        assert result.startswith("Error: File not found:")
        assert "/nonexistent/path/to/file.txt" in result

    def test_permission_denied(self):
        """Test error handling for permission denied."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Secret content")
            temp_path = f.name

        try:
            # Remove read permissions
            os.chmod(temp_path, 0o000)

            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert result.startswith("Error: Permission denied:")
            assert temp_path in result
        finally:
            # Restore permissions before deletion
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)

    def test_binary_file_detection(self):
        """Test detection of binary files (containing null bytes)."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"Binary\x00content\x00here")
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert result.startswith("Error: Cannot read binary file:")
            assert temp_path in result
        finally:
            os.unlink(temp_path)

    def test_file_too_large(self):
        """Test rejection of files larger than 1MB."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            # Write 1.1 MB of data
            chunk = b"x" * 1024  # 1KB chunk
            for _ in range(1100):  # 1.1 MB
                f.write(chunk)
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert result.startswith("Error: File too large (>1MB):")
            assert temp_path in result
        finally:
            os.unlink(temp_path)

    def test_read_python_file(self):
        """Test reading a Python source file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write('"""A test Python file."""\n\ndef hello():\n    print("Hello")\n')
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert "def hello():" in result
            assert 'print("Hello")' in result
        finally:
            os.unlink(temp_path)

    def test_utf8_decoding_with_special_characters(self):
        """Test reading file with UTF-8 special characters."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("中文测试\nEmoji: 🎉\nSpecial: éàü")
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            assert "中文测试" in result
            assert "🎉" in result
            assert "éàü" in result
        finally:
            os.unlink(temp_path)

    def test_return_format(self):
        """Test that return format matches specification."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = tool.execute({"path": temp_path})

            # Format: "File: <绝对路径>\n\n<文件内容>"
            lines = result.split("\n")
            assert lines[0].startswith("File:")
            assert os.path.isabs(lines[0].replace("File: ", "").strip())
            assert lines[1] == ""  # Empty line after path
            assert "Test content" in result
        finally:
            os.unlink(temp_path)

    def test_tool_name_and_description(self):
        """Test that tool has correct name and description."""
        tool = ReadFileTool()

        assert tool.name == "read_file"
        assert "Read the contents of a file" in tool.description

    def test_tool_parameters_schema(self):
        """Test that tool parameters schema is correctly defined."""
        tool = ReadFileTool()
        params = tool.parameters

        assert params["type"] == "object"
        assert "path" in params["properties"]
        assert params["properties"]["path"]["type"] == "string"
        assert "required" in params
        assert "path" in params["required"]
