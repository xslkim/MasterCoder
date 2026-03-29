"""
Unit tests for write_file tool (REQ-09)
"""

import os
import tempfile
import shutil

from src.write_file import write_file


class TestWriteFile:
    """Test suite for write_file tool"""

    def setup_method(self):
        """Create a temporary directory for each test"""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up the temporary directory after each test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_create_new_file(self):
        """Test creating a new file with content"""
        file_path = os.path.join(self.test_dir, "test.txt")
        content = "Hello, World!"

        result = write_file(path=file_path, content=content)

        # Check file exists
        assert os.path.exists(file_path)

        # Check file content
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == content

        # Check return message
        assert "Successfully wrote" in result
        assert "bytes to" in result
        assert file_path in result

        # Verify byte count
        expected_bytes = len(content.encode("utf-8"))
        assert str(expected_bytes) in result

    def test_create_file_with_parent_directory(self):
        """Test creating a file when parent directory doesn't exist"""
        file_path = os.path.join(self.test_dir, "subdir1", "subdir2", "test.txt")
        content = "Nested file content"

        write_file(path=file_path, content=content)

        # Check file and parent directories exist
        assert os.path.exists(file_path)
        assert os.path.isdir(os.path.join(self.test_dir, "subdir1"))
        assert os.path.isdir(os.path.join(self.test_dir, "subdir1", "subdir2"))

        # Check file content
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_overwrite_existing_file(self):
        """Test overwriting an existing file"""
        file_path = os.path.join(self.test_dir, "existing.txt")

        # Create initial file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Initial content")

        # Overwrite with new content
        new_content = "New content"
        result = write_file(path=file_path, content=new_content)

        # Check file has new content
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == new_content

        # Check return message
        assert "Successfully wrote" in result

    def test_path_is_directory_error(self):
        """Test error when path points to an existing directory"""
        dir_path = os.path.join(self.test_dir, "testdir")
        os.makedirs(dir_path)

        result = write_file(path=dir_path, content="content")

        # Check error message
        assert result.startswith("Error: Path is a directory:")
        assert dir_path in result

    def test_permission_denied_error(self):
        """Test error when write permission is denied"""
        # Create a read-only directory
        readonly_dir = os.path.join(self.test_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o555)

        try:
            file_path = os.path.join(readonly_dir, "test.txt")
            result = write_file(path=file_path, content="content")

            # Check error message
            assert "Error:" in result
            # Could be permission denied or write failed
            assert "Permission denied" in result or "Write failed" in result
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)

    def test_utf8_encoding_multibyte(self):
        """Test writing UTF-8 content with multibyte characters"""
        file_path = os.path.join(self.test_dir, "utf8.txt")
        content = "Hello 世界 🌍"

        result = write_file(path=file_path, content=content)

        # Check file content
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == content

        # Verify byte count is correct (not character count)
        actual_bytes = len(content.encode("utf-8"))
        assert str(actual_bytes) in result

        # Verify actual file size
        file_size = os.path.getsize(file_path)
        assert file_size == actual_bytes

    def test_relative_path_resolution(self):
        """Test that relative paths are resolved correctly"""
        # Change to test directory
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)

            relative_path = "relative_test.txt"
            content = "Relative path test"

            result = write_file(path=relative_path, content=content)

            # Check file exists
            assert os.path.exists(relative_path)

            # Check absolute path in result
            abs_path = os.path.abspath(relative_path)
            assert abs_path in result
        finally:
            os.chdir(original_cwd)

    def test_empty_content(self):
        """Test writing empty content"""
        file_path = os.path.join(self.test_dir, "empty.txt")
        content = ""

        result = write_file(path=file_path, content=content)

        # Check file exists
        assert os.path.exists(file_path)

        # Check file is empty
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == ""

        # Check byte count is 0
        assert "0 bytes" in result

    def test_symlink_handling(self):
        """Test writing to a path that is a symlink (should follow symlink)"""
        # Create a regular file
        actual_file = os.path.join(self.test_dir, "actual.txt")
        with open(actual_file, "w", encoding="utf-8") as f:
            f.write("Original")

        # Create a symlink to it
        symlink_path = os.path.join(self.test_dir, "link.txt")
        os.symlink(actual_file, symlink_path)

        # Write through the symlink
        new_content = "Through symlink"
        result = write_file(path=symlink_path, content=new_content)

        # Check operation succeeded
        assert "Successfully wrote" in result

        # Verify the resolved target file has the new content
        # The implementation resolves symlinks, so we read from the resolved path
        resolved_path = os.path.realpath(symlink_path)
        with open(resolved_path, "r", encoding="utf-8") as f:
            actual_content = f.read()
            assert actual_content == new_content
