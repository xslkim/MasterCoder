"""REQ-10: edit_file 工具实现。"""

from pathlib import Path


class EditFileTool:
    """edit_file 工具 - 对已有文件进行精确的局部编辑（基于搜索替换）。"""

    name = "edit_file"
    description = (
        "Make a targeted edit to a file by replacing an exact string match with new content"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要编辑的文件路径"},
            "old_string": {"type": "string", "description": "要被替换的原始字符串（必须精确匹配）"},
            "new_string": {"type": "string", "description": "替换后的新字符串"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    def execute(self, params: dict) -> str:
        """
        执行文件编辑操作。

        Args:
            params: 包含 path, old_string, new_string 的参数字典

        Returns:
            执行结果字符串
        """
        path = params.get("path", "")
        old_string = params.get("old_string", "")
        new_string = params.get("new_string", "")

        # 检查 old_string 和 new_string 是否相同
        if old_string == new_string:
            return "Error: old_string and new_string are identical"

        # 解析路径（支持相对路径）
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        file_path = file_path.resolve()

        # 检查文件是否存在
        if not file_path.exists():
            return f"Error: File not found: {path}"

        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        try:
            # 读取文件内容
            content = file_path.read_text(encoding="utf-8")

            # 查找 old_string 的所有匹配
            match_count = content.count(old_string)

            # 未找到匹配
            if match_count == 0:
                return "Error: old_string not found in file"

            # 多处匹配
            if match_count > 1:
                return f"Error: old_string has {match_count} matches, must be unique. Add more surrounding context to old_string to make it unique"

            # 执行替换（纯字符串匹配，非正则）
            new_content = content.replace(old_string, new_string, 1)

            # 写回文件（完整覆写）
            file_path.write_text(new_content, encoding="utf-8")

            return f"Successfully edited {file_path}"

        except PermissionError:
            return f"Error: Permission denied: {path}"
        except UnicodeDecodeError:
            return f"Error: Cannot read file as UTF-8: {path}"
        except Exception as e:
            return f"Error: Edit failed: {str(e)}"
