"""run_command 工具实现。"""

import subprocess
import sys
from typing import Any

from mastercoder.tools.base import BaseTool


class RunCommandTool(BaseTool):
    """运行命令工具。"""

    DEFAULT_TIMEOUT = 120
    MAX_OUTPUT = 50000

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Execute a shell command and return its output"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {self.DEFAULT_TIMEOUT}, range: 1-600)",
                },
            },
            "required": ["command"],
        }

    def execute(self, params: dict[str, Any]) -> str:
        """执行命令。

        Args:
            params: 参数字典，包含 command 和可选的 timeout

        Returns:
            命令输出或错误信息
        """
        command = params.get("command", "")
        timeout = params.get("timeout", self.DEFAULT_TIMEOUT)

        # 检查命令是否为空
        if not command.strip():
            return "Error: Command cannot be empty"

        # 验证超时范围
        if not (1 <= timeout <= 600):
            timeout = self.DEFAULT_TIMEOUT

        # 确定使用的 shell
        if sys.platform == "win32":
            shell_cmd = ["cmd", "/c", command]
        else:
            shell_cmd = ["sh", "-c", command]

        try:
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
                stdout = (
                    stdout[: self.MAX_OUTPUT]
                    + f"\n... (truncated, showing first {self.MAX_OUTPUT} chars)"
                )
            if len(stderr) > self.MAX_OUTPUT:
                stderr = (
                    stderr[: self.MAX_OUTPUT]
                    + f"\n... (truncated, showing first {self.MAX_OUTPUT} chars)"
                )

            return f"Exit code: {result.returncode}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except FileNotFoundError:
            return "Error: Shell not available"
        except Exception as e:
            return f"Error: Command execution failed: {e}"
