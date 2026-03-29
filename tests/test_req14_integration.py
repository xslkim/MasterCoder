"""REQ-14 端到端集成测试 - 工具调用集成。

测试工具注册、工具调用执行引擎集成到对话循环的完整流程。
"""

import json
import pytest
from unittest.mock import patch

# 导入需要测试的模块
from mastercoder.tools.registry import ToolRegistry, register_all_tools
from mastercoder.tools.base import BaseTool
from mastercoder.tools.executor import ToolExecutor
from mastercoder.message_manager import MessageManager


class MockReadFileTool(BaseTool):
    """Mock read_file 工具。"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read",
                }
            },
            "required": ["path"],
        }

    def execute(self, params: dict) -> str:
        """执行读取文件。"""
        path = params.get("path", "")

        return f"File: {path}\n\n{content}"


class MockRunCommandTool(BaseTool):
    """Mock run_command 工具。"""

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Execute a shell command and return its output"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120, range: 1-600)",
                },
            },
            "required": ["command"],
        }

    def execute(self, params: dict) -> str:
        """执行命令。"""
        command = params.get("command", "")
        timeout = params.get("timeout", 120)

        # 确定使用的 shell
        if sys.platform == "win32":
            shell_cmd = ["cmd", "/c", command]
        else:
            shell_cmd = ["sh", "-c", command]

        # 执行命令
        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 处理输出
        stdout = result.stdout if result.stdout else "(empty)"
        stderr = result.stderr if result.stderr else "(empty)"

        # 截断过长的输出
        if len(stdout) > self.MAX_OUTPUT:
            stdout = stdout[: self.MAX_OUTPUT] + f"\n... (truncated, showing first {self.MAX_OUTPUT} chars)"
            if len(stderr) > 200:
                stderr = stderr[:self.MAX_OUTPUT] + "\n... (truncated, showing first 50000 chars)"

        return f"Exit code: {result.returncode}\n\nSTDOUT:\n{stdout}\n\nSTDOUT:\n{command} output\n\nSTDERR:\n{stderr}"

        return f"Successfully ran {command}"


class MockListFilesTool(BaseTool):
    """Mock list_files 工具。"""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory, optionally filtered by a glob pattern"

    @property
    def parameters(self) -> dict:
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

    def execute(self, params: dict) -> str:
        """执行列出文件。"""
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
