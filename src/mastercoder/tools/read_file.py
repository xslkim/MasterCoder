"""read_file 工具实现。"""

from typing import Any
from pathlib import Path

from mastercoder.tools.base import BaseTool


class ReadFileTool(BaseTool):
    """读取文件工具。"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path and return its text content"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read (absolute or relative to working directory)",
                }
            },
            "required": ["path"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行读取文件。

        Args:
            params: 参数字典，包含 path

        Returns:
            文件内容或错误信息
        """
        path = params.get("path", "")

        # 解析路径
        try:
            file_path = Path(path).resolve()
        except Exception as e:
            return f"Error: Invalid path: {e}"

        # 检查文件是否存在
        if not file_path.exists():
            return f"Error: File not found: {path}"

        # 检查是否为文件
        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        # 检查文件大小（1MB 限制）
        try:
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB
                return f"Error: File too large (>1MB): {path}"
        except OSError as e:
            return f"Error: Cannot access file: {e}"

        # 检查是否为二进制文件
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return f"Error: Cannot read binary file: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Cannot read file: {e}"

        # 读取文件内容
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return f"File: {file_path}\n\n{content}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {path}"
        except OSError as e:
            return f"Error: Read failed: {e}"
