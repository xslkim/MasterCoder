"""list_files tool implementation (REQ-11)."""

import glob
import os


def list_files(path: str, pattern: str = "*") -> str:
    """List files in a directory, optionally filtered by a glob pattern.

    Args:
        path: Target directory path
        pattern: Glob filter pattern (default "*" for all files in current directory)

    Returns:
        Formatted string with directory path and file list, or error message
    """
    # Validate path exists
    if not os.path.exists(path):
        return f"Error: Directory not found: {path}"

    # Validate path is a directory
    if not os.path.isdir(path):
        return f"Error: Not a directory: {path}"

    # Check read permissions
    if not os.access(path, os.R_OK):
        return f"Error: Permission denied: {path}"

    try:
        # Use glob to match files
        # For ** patterns, we need recursive=True
        recursive = "**" in pattern

        # Build the full glob pattern
        full_pattern = os.path.join(path, pattern)

        # Get all matches
        if recursive:
            # Don't follow symlinks to avoid cycles
            matches = glob.glob(full_pattern, recursive=True)
        else:
            matches = glob.glob(full_pattern)

        # Convert to relative paths and categorize
        items = []
        for match in matches:
            # Get relative path from the target directory
            rel_path = os.path.relpath(match, path)

            # Skip the directory itself (when pattern matches the dir)
            if rel_path == ".":
                continue

            # Add / suffix for directories
            if os.path.isdir(match):
                rel_path += "/"

            items.append(rel_path)

        # Sort alphabetically (directories and files mixed)
        items.sort()

        # Truncate to 500 items
        max_items = 500
        if len(items) > max_items:
            displayed_items = items[:max_items]
            remaining = len(items) - max_items
            result_lines = displayed_items + [f"... and {remaining} more items"]
        else:
            result_lines = items

        # Format output
        output = f"Directory: {os.path.abspath(path)}\n"
        if result_lines:
            output += "\n" + "\n".join(result_lines)

        return output

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {str(e)}"
