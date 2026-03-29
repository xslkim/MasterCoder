"""write_file 工具实现。"""

from typing import Any
from pathlib import Path

from mastercoder.tools.base import BaseTool


class WriteFileTool(BaseTool):
    """写入文件工具。"""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create a new file or overwrite an existing file with the given content"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行写入文件。

        Args:
            params: 参数字典，包含 path 和 content

        Returns:
            成功信息或错误信息
        """
        path = params.get("path", "")
        content = params.get("content", "")

        # 解析路径
        try:
            file_path = Path(path).resolve()
        except Exception as e:
            return f"Error: Invalid path: {e}"

        # 检查路径是否为目录
        if file_path.exists() and file_path.is_dir():
            return f"Error: Path is a directory: {path}"

        # 创建父目录
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Cannot create directory: {e}"

        # 写入文件
        try:
            # 计算字节数
            content_bytes = content.encode("utf-8")
            byte_count = len(content_bytes)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote {byte_count} bytes to {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Write failed: {e}"
