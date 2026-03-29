"""edit_file 工具实现。"""

from typing import Any
from pathlib import Path

from mastercoder.tools.base import BaseTool


class EditFileTool(BaseTool):
    """编辑文件工具。"""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Make a targeted edit to a file by replacing an exact string match with new content"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The new string to replace with",
                },
            },
            "required": ["path", "old_string", "new_string"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行编辑文件。

        Args:
            params: 参数字典，包含 path, old_string, new_string

        Returns:
            成功信息或错误信息
        """
        path = params.get("path", "")
        old_string = params.get("old_string", "")
        new_string = params.get("new_string", "")

        # 检查 old_string 和 new_string 是否相同
        if old_string == new_string:
            return "Error: old_string and new_string are identical"

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

        # 读取文件内容
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Cannot read file: {e}"

        # 查找匹配
        count = content.count(old_string)

        if count == 0:
            return "Error: old_string not found in file"

        if count > 1:
            return f"Error: old_string has {count} matches, must be unique. Add more surrounding context to old_string to make it unique"

        # 执行替换
        new_content = content.replace(old_string, new_string, 1)

        # 写回文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully edited {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except OSError as e:
            return f"Error: Write failed: {e}"
