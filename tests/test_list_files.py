"""Tests for list_files tool (REQ-11)."""

import os
from pathlib import Path

import pytest

from mastercoder.tools.list_files import list_files


class TestListFiles:
    """Test list_files tool functionality."""

    def test_list_files_basic(self, tmp_path: Path):
        """Test listing directory contents."""
        # Create test files and directories
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        result = list_files(path=str(tmp_path))

        assert result.startswith(f"Directory: {tmp_path}")
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir/" in result  # Directory should have / suffix
        assert "file3.txt" not in result  # Non-recursive by default

    def test_list_files_glob_pattern(self, tmp_path: Path):
        """Test glob pattern filtering."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "file3.md").write_text("content3")
        (tmp_path / "subdir").mkdir()

        result = list_files(path=str(tmp_path), pattern="*.py")

        assert "file2.py" in result
        assert "file1.txt" not in result
        assert "file3.md" not in result
        assert "subdir/" not in result

    def test_list_files_recursive_pattern(self, tmp_path: Path):
        """Test recursive glob pattern with **."""
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.py").write_text("content2")
        (tmp_path / "subdir" / "file3.txt").write_text("content3")
        (tmp_path / "subdir" / "nested").mkdir()
        (tmp_path / "subdir" / "nested" / "file4.py").write_text("content4")

        result = list_files(path=str(tmp_path), pattern="**/*.py")

        assert "file1.py" in result
        assert "subdir/file2.py" in result
        assert "subdir/nested/file4.py" in result
        assert "file3.txt" not in result

    def test_list_files_directory_suffix(self, tmp_path: Path):
        """Test that directories have / suffix."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "mydir").mkdir()
        (tmp_path / "anotherdir").mkdir()

        result = list_files(path=str(tmp_path))

        assert "mydir/" in result
        assert "anotherdir/" in result
        assert "file.txt" in result
        # Ensure files don't have / suffix
        assert "file.txt/" not in result

    def test_list_files_sorted(self, tmp_path: Path):
        """Test that results are sorted alphabetically."""
        (tmp_path / "zebra.txt").write_text("content")
        (tmp_path / "alpha.txt").write_text("content")
        (tmp_path / "beta.txt").write_text("content")

        result = list_files(path=str(tmp_path))
        lines = result.split("\n")

        # Find the file lines (after the header)
        file_lines = [line for line in lines if line.strip() and not line.startswith("Directory:")]
        assert file_lines[0] == "alpha.txt"
        assert file_lines[1] == "beta.txt"
        assert file_lines[2] == "zebra.txt"

    def test_list_files_truncation(self, tmp_path: Path):
        """Test truncation when more than 500 items."""
        # Create 600 files
        for i in range(600):
            (tmp_path / f"file_{i:03d}.txt").write_text(f"content{i}")

        result = list_files(path=str(tmp_path))
        lines = result.split("\n")

        # Count non-empty lines excluding header
        file_lines = [line for line in lines if line.strip() and not line.startswith("Directory:")]

        # Should have 500 files + truncation message
        assert len(file_lines) == 501
        assert "... and 100 more items" in result

    def test_list_files_directory_not_found(self):
        """Test error when directory doesn't exist."""
        result = list_files(path="/nonexistent/directory/path")

        assert result.startswith("Error: Directory not found:")
        assert "/nonexistent/directory/path" in result

    def test_list_files_not_a_directory(self, tmp_path: Path):
        """Test error when path is not a directory."""
        file_path = tmp_path / "notadir.txt"
        file_path.write_text("content")

        result = list_files(path=str(file_path))

        assert result.startswith("Error: Not a directory:")
        assert str(file_path) in result

    def test_list_files_permission_denied(self, tmp_path: Path):
        """Test error when permission denied."""
        # Skip on Windows as permission handling differs
        if os.name == "nt":
            pytest.skip("Permission test not reliable on Windows")

        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()

        # Remove read permissions
        os.chmod(restricted_dir, 0o000)

        try:
            result = list_files(path=str(restricted_dir))
            assert result.startswith("Error: Permission denied:")
            assert str(restricted_dir) in result
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)

    def test_list_files_empty_directory(self, tmp_path: Path):
        """Test listing empty directory."""
        result = list_files(path=str(tmp_path))

        assert result.startswith(f"Directory: {tmp_path}")
        # Should just have the header, no files listed
        lines = [
            line
            for line in result.split("\n")
            if line.strip() and not line.startswith("Directory:")
        ]
        assert len(lines) == 0

    def test_list_files_with_subdirectories(self, tmp_path: Path):
        """Test that subdirectories are listed but not their contents."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()
        (tmp_path / "subdir1" / "nested.txt").write_text("nested")

        result = list_files(path=str(tmp_path), pattern="*")

        assert "file.txt" in result
        assert "subdir1/" in result
        assert "subdir2/" in result
        assert "nested.txt" not in result  # Should not show contents of subdirs
