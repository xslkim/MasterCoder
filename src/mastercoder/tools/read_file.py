"""Read file tool implementation for REQ-08."""

import os
from pathlib import Path


class ReadFileTool:
    """Tool to read file contents and return them to AI."""

    name = "read_file"
    description = "Read the contents of a file at the given path and return its text content"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file path to read (absolute or relative to working directory)",
            }
        },
        "required": ["path"],
    }

    # Maximum file size: 1MB
    MAX_FILE_SIZE = 1024 * 1024

    # Number of bytes to check for binary detection
    BINARY_CHECK_SIZE = 8192

    def execute(self, params: dict) -> str:
        """
        Execute the read_file tool.

        Args:
            params: Dictionary containing 'path' key with file path

        Returns:
            File content with format "File: <path>\\n\\n<content>" or error message
        """
        path = params.get("path", "")

        # Resolve to absolute path
        try:
            abs_path = Path(path).resolve()
        except (OSError, ValueError):
            return f"Error: Invalid path: {path}"

        path_str = str(abs_path)

        # Check if file exists
        if not abs_path.exists():
            return f"Error: File not found: {path_str}"

        # Check if it's a file (not a directory)
        if not abs_path.is_file():
            return f"Error: Path is not a file: {path_str}"

        # Check file size before reading
        try:
            file_size = abs_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return f"Error: File too large (>1MB): {path_str}"
        except OSError:
            return f"Error: Cannot access file: {path_str}"

        # Check read permissions
        if not os.access(path_str, os.R_OK):
            return f"Error: Permission denied: {path_str}"

        # Check for binary content (null bytes)
        try:
            with open(path_str, "rb") as f:
                chunk = f.read(self.BINARY_CHECK_SIZE)
                if b"\x00" in chunk:
                    return f"Error: Cannot read binary file: {path_str}"
        except IOError:
            return f"Error: Permission denied: {path_str}"

        # Read file content with UTF-8 encoding
        try:
            with open(path_str, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with a fallback encoding
            try:
                with open(path_str, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception:
                return f"Error: Cannot decode file: {path_str}"
        except IOError:
            return f"Error: Permission denied: {path_str}"
        except Exception as e:
            return f"Error: Read failed: {str(e)}"

        # Return formatted result
        return f"File: {path_str}\n\n{content}"
