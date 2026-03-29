"""list_files 工具实现。"""

from typing import Any
from pathlib import Path

from mastercoder.tools.base import BaseTool


class ListFilesTool(BaseTool):
    """列出文件工具。"""

    MAX_RESULTS = 500

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory, optionally filtered by a glob pattern"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (default: *)",
                },
            },
            "required": ["path"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行列出文件。

        Args:
            params: 参数字典，包含 path 和可选的 pattern

        Returns:
            文件列表或错误信息
        """
        path = params.get("path", "")
        pattern = params.get("pattern", "*")

        # 解析路径
        try:
            dir_path = Path(path).resolve()
        except Exception as e:
            return f"Error: Invalid path: {e}"

        # 检查路径是否存在
        if not dir_path.exists():
            return f"Error: Directory not found: {path}"

        # 检查是否为目录
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        # 列出文件
        try:
            # 使用 glob 匹配
            if pattern.startswith("**/"):
                # 递归匹配
                matches = list(dir_path.glob(pattern))
            else:
                # 非递归匹配
                matches = list(dir_path.glob(pattern))

            # 排序
            matches.sort(key=lambda p: str(p).lower())

            # 限制结果数量
            truncated = False
            if len(matches) > self.MAX_RESULTS:
                matches = matches[: self.MAX_RESULTS]
                truncated = True

            # 格式化输出
            lines = []
            for match in matches:
                rel_path = match.relative_to(dir_path)
                if match.is_dir():
                    lines.append(f"{rel_path}/")
                else:
                    lines.append(str(rel_path))

            result = f"Directory: {dir_path}\n\n" + "\n".join(lines)

            if truncated:
                remaining = len(matches) - self.MAX_RESULTS
                result += f"\n... and {remaining} more items"

            return result

        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Cannot list directory: {e}"
