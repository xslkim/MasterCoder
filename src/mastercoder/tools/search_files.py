"""search_files 工具实现。"""

import re
from typing import Any
from pathlib import Path

from mastercoder.tools.base import BaseTool


class SearchFilesTool(BaseTool):
    """搜索文件内容工具。"""

    MAX_RESULTS = 100
    EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return "Search for a pattern in file contents within a directory"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The root directory path to search",
                },
                "pattern": {
                    "type": "string",
                    "description": "The search pattern (supports regex)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (default: *)",
                },
            },
            "required": ["path", "pattern"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行搜索文件内容。

        Args:
            params: 参数字典，包含 path, pattern 和可选的 file_pattern

        Returns:
            搜索结果或错误信息
        """
        path = params.get("path", "")
        pattern = params.get("pattern", "")
        file_pattern = params.get("file_pattern", "*")

        # 解析路径
        try:
            root_path = Path(path).resolve()
        except Exception as e:
            return f"Error: Invalid path: {e}"

        # 检查路径是否存在
        if not root_path.exists():
            return f"Error: Directory not found: {path}"

        # 检查是否为目录
        if not root_path.is_dir():
            return f"Error: Not a directory: {path}"

        # 编译正则表达式
        try:
            regex = re.compile(pattern)
        except re.error:
            return f"Error: Invalid regex pattern: {pattern}"

        # 搜索文件
        try:
            matches = []
            for file_path in root_path.rglob(file_pattern):
                # 跳过排除的目录
                if any(excluded in file_path.parts for excluded in self.EXCLUDED_DIRS):
                    continue

                # 跳过目录
                if not file_path.is_file():
                    continue

                # 跳过二进制文件
                try:
                    with open(file_path, "rb") as f:
                        chunk = f.read(8192)
                        if b"\x00" in chunk:
                            continue
                except (PermissionError, OSError):
                    continue

                # 搜索匹配
                try:
                    with open(file_path, encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = file_path.relative_to(root_path)
                                # 截断过长的行
                                display_line = line.rstrip()
                                if len(display_line) > 200:
                                    display_line = display_line[:200] + "..."
                                matches.append(f"{rel_path}:{line_num}: {display_line}")

                                if len(matches) >= self.MAX_RESULTS:
                                    break
                except (PermissionError, OSError, UnicodeDecodeError):
                    continue

                if len(matches) >= self.MAX_RESULTS:
                    break

            if not matches:
                return f"No matches found for pattern '{pattern}' in {path}"

            result = "\n".join(matches)

            if len(matches) >= self.MAX_RESULTS:
                result += f"\n... and {self.MAX_RESULTS} more matches"

            return result

        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Search failed: {e}"
