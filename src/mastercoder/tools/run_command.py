"""REQ-13: run_command 工具实现。"""

import os
import subprocess
import sys
from typing import Any

from . import BaseTool


class RunCommandTool(BaseTool):
    """执行 shell 命令的工具。"""

    MAX_OUTPUT_LENGTH = 50000
    DEFAULT_TIMEOUT = 120
    MIN_TIMEOUT = 1
    MAX_TIMEOUT = 600

    @property
    def name(self) -> str:
        """工具名称。"""
        return "run_command"

    @property
    def description(self) -> str:
        """工具描述。"""
        return "Execute a shell command and return its output"

    @property
    def parameters(self) -> dict[str, Any]:
        """参数定义（JSON Schema 格式）。"""
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
                    "default": self.DEFAULT_TIMEOUT,
                    "minimum": self.MIN_TIMEOUT,
                    "maximum": self.MAX_TIMEOUT,
                },
            },
            "required": ["command"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行 shell 命令。

        Args:
            params: 工具参数，包含：
                - command: 要执行的命令
                - timeout: 超时时间（秒）

        Returns:
            执行结果字符串，包含 exit code、stdout 和 stderr
        """
        command = params.get("command", "")
        timeout = params.get("timeout", self.DEFAULT_TIMEOUT)

        # 验证命令不为空
        if not command or not command.strip():
            return "Error: Command cannot be empty"

        # 验证并修正 timeout 范围
        if not isinstance(timeout, int) or timeout < self.MIN_TIMEOUT or timeout > self.MAX_TIMEOUT:
            timeout = self.DEFAULT_TIMEOUT

        # 检查 shell 是否可用
        try:
            if sys.platform == "win32":
                shell = os.environ.get("COMSPEC", "cmd.exe")
                if not os.path.exists(shell):
                    return "Error: Shell not available"
            else:
                shell = "/bin/sh"
                if not os.path.exists(shell):
                    return "Error: Shell not available"
        except Exception:
            return "Error: Shell not available"

        try:
            # 执行命令
            # 在 Windows 上使用 cmd /c，在 Linux/Mac 上使用 sh -c
            if sys.platform == "win32":
                process = subprocess.Popen(
                    ["cmd", "/c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.getcwd(),
                )
            else:
                process = subprocess.Popen(
                    ["/bin/sh", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.getcwd(),
                )

            try:
                # 读取输出，限制长度
                stdout_bytes = b""
                stderr_bytes = b""
                stdout_truncated = False
                stderr_truncated = False

                # 使用 communicate 并设置超时
                try:
                    stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # 超时后强制终止进程
                    process.kill()
                    process.communicate()  # 清理
                    return f"Error: Command timed out after {timeout} seconds"

                # 截断输出（如果超过 50000 字节）
                if len(stdout_bytes) > self.MAX_OUTPUT_LENGTH:
                    stdout_bytes = stdout_bytes[: self.MAX_OUTPUT_LENGTH]
                    stdout_truncated = True

                if len(stderr_bytes) > self.MAX_OUTPUT_LENGTH:
                    stderr_bytes = stderr_bytes[: self.MAX_OUTPUT_LENGTH]
                    stderr_truncated = True

                # 解码输出
                try:
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                except Exception:
                    stdout = stdout_bytes.decode("latin-1", errors="replace")

                try:
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                except Exception:
                    stderr = stderr_bytes.decode("latin-1", errors="replace")

                # 添加截断标记
                if stdout_truncated:
                    stdout += "\n... (truncated, showing first 50000 chars)"
                if stderr_truncated:
                    stderr += "\n... (truncated, showing first 50000 chars)"

                # 格式化输出
                result = f"Exit code: {process.returncode}\n\n"
                result += "STDOUT:\n"
                result += stdout.strip() if stdout.strip() else "(empty)"
                result += "\n\nSTDERR:\n"
                result += stderr.strip() if stderr.strip() else "(empty)"

                return result

            except Exception as e:
                return f"Error: Command execution failed: {str(e)}"

        except FileNotFoundError:
            return "Error: Shell not available"
        except Exception as e:
            return f"Error: Command execution failed: {str(e)}"
