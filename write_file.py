"""
write_file tool implementation (REQ-09)

This module provides a tool for creating or overwriting files with UTF-8 content.
"""

import os
import tempfile
from pathlib import Path


def write_file(path: str, content: str) -> str:
    """
    Create a new file or overwrite an existing file with the given content.

    Args:
        path: Target file path (can be relative or absolute)
        content: Content to write to the file (UTF-8 encoded)

    Returns:
        Success message with byte count and absolute path, or error message
    """
    try:
        # Convert to Path object for easier manipulation
        file_path = Path(path)

        # Resolve relative paths to absolute paths based on current working directory
        if not file_path.is_absolute():
            file_path = file_path.absolute()

        # Check if the original path (before following symlinks) is a directory
        if file_path.exists() and file_path.is_dir():
            return f"Error: Path is a directory: {file_path}"

        # Store the original path for the return message
        original_path_for_message = str(file_path)

        # If the path is a symlink, resolve it to the target file
        # This ensures we write to the actual file, not replace the symlink
        if file_path.is_symlink():
            file_path = file_path.resolve()

        # Get the parent directory of the resolved path
        parent_dir = file_path.parent
        if not parent_dir.exists():
            # Use os.makedirs with mode 0755 for secure directory creation
            os.makedirs(parent_dir, mode=0o755)

        # Encode content to UTF-8 to get actual byte count
        content_bytes = content.encode("utf-8")
        byte_count = len(content_bytes)

        # Write to a temporary file first, then rename for atomicity
        # This ensures the operation is as atomic as possible
        temp_fd = None
        temp_path = None
        try:
            # Create temp file in the same directory as the target to ensure same filesystem
            temp_fd, temp_path = tempfile.mkstemp(
                dir=parent_dir, prefix=".tmp_write_", suffix=".tmp"
            )

            # Write content to temp file
            with os.fdopen(temp_fd, "wb") as f:
                f.write(content_bytes)
                temp_fd = None  # Already closed by fdopen

            # Atomic rename (on POSIX systems)
            # os.rename will atomically replace the target file
            os.rename(temp_path, str(file_path))
            temp_path = None  # Successfully moved

        except Exception:
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise
        finally:
            # Close temp_fd if still open
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass

        return f"Successfully wrote {byte_count} bytes to {original_path_for_message}"

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except OSError as e:
        # Handle disk space and other IO errors
        return f"Error: Write failed: {str(e)}"
    except Exception as e:
        # Catch any other unexpected errors
        return f"Error: Write failed: {str(e)}"
