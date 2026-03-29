"""Implementation of search_files tool (REQ-12)."""

import os
import re
from pathlib import Path
from typing import List, Tuple


# Excluded directories (defined as constant for maintainability)
EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# Maximum number of matches to return
MAX_MATCHES = 100

# Maximum line length before truncation
MAX_LINE_LENGTH = 200


class SearchFilesTool:
    """Tool for searching pattern in file contents within a directory."""

    name = "search_files"
    description = "Search for a pattern in file contents within a directory"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The root directory path to search in"
            },
            "pattern": {
                "type": "string",
                "description": "Search pattern (supports regular expressions)"
            },
            "file_pattern": {
                "type": "string",
                "description": "File name filter glob, defaults to '*' (all files)"
            }
        },
        "required": ["path", "pattern"]
    }

    def execute(self, params: dict) -> str:
        """
        Execute the search_files tool.

        Args:
            params: Dictionary containing:
                - path: Root directory path to search
                - pattern: Regex pattern to search for
                - file_pattern: Optional glob pattern for file filtering

        Returns:
            Search results or error message
        """
        path = params.get("path", "")
        pattern = params.get("pattern", "")
        file_pattern = params.get("file_pattern", "*")

        # Validate directory exists
        if not os.path.exists(path):
            return f"Error: Directory not found: {path}"

        if not os.path.isdir(path):
            return f"Error: Directory not found: {path}"

        # Compile regex pattern upfront (per review checklist)
        try:
            regex = re.compile(pattern)
        except re.error:
            return f"Error: Invalid regex pattern: {pattern}"

        # Collect all matches
        matches: List[Tuple[str, int, str]] = []
        root_path = Path(path).resolve()

        try:
            matches = self._search_directory(root_path, regex, file_pattern)
        except Exception as e:
            return f"Error: Search failed: {str(e)}"

        # Format results
        if not matches:
            return f"No matches found for pattern '{pattern}' in {path}"

        # Build output
        output_lines = []
        for relative_path, line_num, line_content in matches[:MAX_MATCHES]:
            # Truncate long lines
            if len(line_content) > MAX_LINE_LENGTH:
                line_content = line_content[:MAX_LINE_LENGTH] + "..."
            output_lines.append(f"{relative_path}:{line_num}: {line_content}")

        result = "\n".join(output_lines)

        # Add truncation message if needed
        if len(matches) > MAX_MATCHES:
            remaining = len(matches) - MAX_MATCHES
            result += f"\n... and {remaining} more matches"

        return result

    def _search_directory(
        self, root_path: Path, regex: re.Pattern, file_pattern: str
    ) -> List[Tuple[str, int, str]]:
        """
        Recursively search directory for pattern matches.

        Args:
            root_path: Root directory path
            regex: Compiled regex pattern
            file_pattern: Glob pattern for file filtering

        Returns:
            List of tuples (relative_path, line_number, line_content)
        """
        matches = []

        # Use glob to find matching files
        for file_path in root_path.rglob(file_pattern):
            # Skip if not a file
            if not file_path.is_file():
                continue

            # Skip if any parent directory is in excluded list
            if self._is_in_excluded_dir(file_path, root_path):
                continue

            # Skip binary files
            if self._is_binary_file(file_path):
                continue

            # Search in file
            file_matches = self._search_file(file_path, root_path, regex)
            matches.extend(file_matches)

        return matches

    def _is_in_excluded_dir(self, file_path: Path, root_path: Path) -> bool:
        """
        Check if file is in an excluded directory.

        Args:
            file_path: Path to check
            root_path: Root directory path

        Returns:
            True if file is in excluded directory
        """
        try:
            relative = file_path.relative_to(root_path)
            for part in relative.parts[:-1]:  # Exclude filename itself
                if part in EXCLUDED_DIRS:
                    return True
        except ValueError:
            pass
        return False

    def _is_binary_file(self, file_path: Path) -> bool:
        """
        Check if file is binary by checking for null bytes.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be binary
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except (IOError, OSError):
            return True

    def _search_file(
        self, file_path: Path, root_path: Path, regex: re.Pattern
    ) -> List[Tuple[str, int, str]]:
        """
        Search for pattern in a single file.

        Args:
            file_path: Path to file
            root_path: Root directory for relative path
            regex: Compiled regex pattern

        Returns:
            List of (relative_path, line_number, line_content) tuples
        """
        matches = []

        try:
            # Read file line by line (per review checklist)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                relative_path = file_path.relative_to(root_path)
                for line_num, line in enumerate(f, start=1):
                    if regex.search(line):
                        # Strip trailing whitespace/newline
                        line_content = line.rstrip()
                        matches.append((str(relative_path), line_num, line_content))
        except (IOError, OSError):
            # Skip files we can't read
            pass

        return matches
