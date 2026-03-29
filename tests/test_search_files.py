"""Tests for search_files tool implementation (REQ-12)."""

import tempfile
from pathlib import Path

import pytest

from mastercoder.tools.search_files import SearchFilesTool


class TestSearchFiles:
    """Test cases for search_files tool."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = {
                "main.py": "def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()\n",
                "utils.py": "# TODO: Add error handling\ndef helper():\n    pass\n",
                "README.md": "# Project\n\nThis is a test project.\n",
                "subdir/other.py": "# FIXME: This needs work\ndef func():\n    pass\n",
                "binary.bin": b"\x00\x01\x02\x03\x04",
            }

            for filepath, content in test_files.items():
                full_path = Path(tmpdir) / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    full_path.write_bytes(content)
                else:
                    full_path.write_text(content)

            yield tmpdir

    def test_normal_search_returns_matches(self, temp_dir):
        """Test normal search returns matching lines."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "def"})

        assert "main.py:1:" in result
        assert "utils.py:2:" in result
        assert "def main():" in result or "def helper():" in result

    def test_regex_search(self, temp_dir):
        """Test regex pattern search."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "TODO|FIXME"})

        assert "TODO" in result
        assert "FIXME" in result

    def test_file_pattern_filter(self, temp_dir):
        """Test file_pattern filters files correctly."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "def", "file_pattern": "*.py"})

        assert ".py:" in result
        assert "README.md:" not in result

    def test_skip_binary_files(self, temp_dir):
        """Test binary files are skipped."""
        tool = SearchFilesTool()
        # Create a text pattern that would match in binary if read as text
        result = tool.execute({"path": temp_dir, "pattern": "anything"})

        # Binary file should not appear in results
        assert "binary.bin:" not in result

    def test_skip_excluded_directories(self, temp_dir):
        """Test excluded directories are skipped."""
        tool = SearchFilesTool()

        # Create .git directory with a file
        git_dir = Path(temp_dir) / ".git"
        git_dir.mkdir()
        git_file = git_dir / "config"
        git_file.write_text("[core]\n    repositoryformatversion = 0\n")

        result = tool.execute({"path": temp_dir, "pattern": "repositoryformatversion"})

        # .git directory should be excluded
        assert ".git:" not in result
        assert "repositoryformatversion" not in result

    def test_truncate_at_100_matches(self):
        """Test results truncate at 100 matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with 150 matching lines
            test_file = Path(tmpdir) / "large.py"
            lines = ["def func_{}(): pass".format(i) for i in range(150)]
            test_file.write_text("\n".join(lines))

            tool = SearchFilesTool()
            result = tool.execute({"path": tmpdir, "pattern": "def"})

            # Should have truncation message
            assert "more matches" in result
            # Count should be 50 remaining
            assert "50 more" in result

    def test_no_matches_found(self, temp_dir):
        """Test no matches returns appropriate message."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "NONEXISTENT_PATTERN"})

        assert "No matches found" in result
        assert "NONEXISTENT_PATTERN" in result

    def test_invalid_regex_pattern(self, temp_dir):
        """Test invalid regex returns error."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "[invalid"})

        assert "Error:" in result
        assert "Invalid regex pattern" in result

    def test_directory_not_found(self):
        """Test non-existent directory returns error."""
        tool = SearchFilesTool()
        result = tool.execute({"path": "/nonexistent/path", "pattern": "test"})

        assert "Error:" in result
        assert "Directory not found" in result

    def test_line_truncation(self):
        """Test long lines are truncated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with very long line
            test_file = Path(tmpdir) / "long.txt"
            long_line = "x" * 300
            test_file.write_text(f"short line\n{long_line}\n")

            tool = SearchFilesTool()
            result = tool.execute({"path": tmpdir, "pattern": "x"})

            # Long line should be truncated
            assert "..." in result

    def test_relative_path_in_output(self, temp_dir):
        """Test output uses relative paths."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "def"})

        # Should not contain full absolute path
        assert temp_dir not in result
        # Should contain relative filename
        assert "main.py:" in result or "utils.py:" in result

    def test_recursive_search(self, temp_dir):
        """Test recursive search in subdirectories."""
        tool = SearchFilesTool()
        result = tool.execute({"path": temp_dir, "pattern": "FIXME"})

        # Should find match in subdirectory
        assert "subdir" in result
        assert "other.py" in result

    def test_excluded_node_modules(self, temp_dir):
        """Test node_modules directory is excluded."""
        tool = SearchFilesTool()

        # Create node_modules directory
        node_dir = Path(temp_dir) / "node_modules"
        node_dir.mkdir()
        node_file = node_dir / "package.js"
        node_file.write_text("function test() { console.log('test'); }\n")

        result = tool.execute({"path": temp_dir, "pattern": "console"})

        # node_modules should be excluded
        assert "node_modules:" not in result
        assert "console" not in result

    def test_excluded_pycache(self, temp_dir):
        """Test __pycache__ directory is excluded."""
        tool = SearchFilesTool()

        # Create __pycache__ directory
        cache_dir = Path(temp_dir) / "__pycache__"
        cache_dir.mkdir()
        cache_file = cache_dir / "module.pyc"
        cache_file.write_text("compiled code here\n")

        result = tool.execute({"path": temp_dir, "pattern": "compiled"})

        # __pycache__ should be excluded
        assert "__pycache__:" not in result

    def test_excluded_venv(self, temp_dir):
        """Test .venv and venv directories are excluded."""
        tool = SearchFilesTool()

        # Create .venv directory
        venv_dir = Path(temp_dir) / ".venv"
        venv_dir.mkdir()
        venv_file = venv_dir / "activate"
        venv_file.write_text("VIRTUAL_ENV=/path/to/venv\n")

        result = tool.execute({"path": temp_dir, "pattern": "VIRTUAL_ENV"})

        # .venv should be excluded
        assert ".venv:" not in result

    def test_tool_name_and_description(self):
        """Test tool has correct name and description."""
        tool = SearchFilesTool()

        assert tool.name == "search_files"
        assert "Search for a pattern" in tool.description

    def test_parameters_schema(self):
        """Test parameters schema is correct."""
        tool = SearchFilesTool()
        params = tool.parameters

        assert params["type"] == "object"
        assert "path" in params["required"]
        assert "pattern" in params["required"]
        assert "file_pattern" not in params["required"]
