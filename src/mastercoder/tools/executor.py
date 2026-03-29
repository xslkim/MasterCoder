"""工具调用执行引擎。"""

import json
import sys
from typing import Any

from mastercoder.tools.registry import ToolRegistry


class ToolExecutor:
    """工具执行引擎，处理工具调用的确认、执行和结果回传。"""

    def __init__(self, registry: ToolRegistry, auto_approve: bool = False) -> None:
        """初始化工具执行引擎。

        Args:
            registry: 工具注册器
            auto_approve: 是否自动批准工具调用
        """
        self._registry = registry
        self.auto_approve = auto_approve

    def execute_tool(self, tool_call: dict[str, Any]) -> dict[str, str]:
        """执行单个工具调用。

        Args:
            tool_call: 工具调用对象，包含 id 和 function 信息

        Returns:
            包含 tool_call_id 和 content 的字典
        """
        tool_call_id = tool_call.get("id", "")
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")
        arguments_str = function_info.get("arguments", "{}")

        # 用户确认
        if not self.auto_approve:
            approved = self._confirm_tool_call(tool_name, arguments_str)
            if not approved:
                return {
                    "tool_call_id": tool_call_id,
                    "content": "Tool call was rejected by user",
                }

        # 显示执行状态
        print(f"\n[Executing: {tool_name}...]", file=sys.stderr)

        # 执行工具
        result = self._execute_tool_internal(tool_name, arguments_str)

        # 显示完成状态
        if result.startswith("Error:"):
            print(f"[Failed: {tool_name}] {result[:100]}", file=sys.stderr)
        else:
            # 结果摘要（前 100 字符）
            summary = result[:100] + "..." if len(result) > 100 else result
            print(f"[Done: {tool_name}] {summary}", file=sys.stderr)

        return {
            "tool_call_id": tool_call_id,
            "content": result,
        }

    def execute_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, str]]:
        """执行多个工具调用。

        Args:
            tool_calls: 工具调用列表

        Returns:
            结果列表
        """
        results = []
        for tool_call in tool_calls:
            result = self.execute_tool(tool_call)
            results.append(result)
        return results

    def _confirm_tool_call(self, tool_name: str, arguments_str: str) -> bool:
        """确认工具调用。

        Args:
            tool_name: 工具名称
            arguments_str: 参数 JSON 字符串

        Returns:
            是否批准执行
        """
        # 解析参数以显示
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}

        # 显示工具调用信息
        print(f"\nTool call: {tool_name}", file=sys.stderr)
        print("Arguments:", file=sys.stderr)
        for key, value in arguments.items():
            print(f"  {key}: {value}", file=sys.stderr)

        # 等待用户确认
        while True:
            try:
                response = input("[Y]es / [N]o / [A]lways > ").strip().lower()

                if response in ["y", "yes", ""]:
                    return True
                elif response in ["n", "no"]:
                    return False
                elif response in ["a", "always"]:
                    self.auto_approve = True
                    return True
                else:
                    print("Invalid input. Please enter Y, N, or A.", file=sys.stderr)
            except (EOFError, KeyboardInterrupt):
                return False

    def _execute_tool_internal(self, tool_name: str, arguments_str: str) -> str:
        """内部执行工具。

        Args:
            tool_name: 工具名称
            arguments_str: 参数 JSON 字符串

        Returns:
            执行结果字符串
        """
        # 查找工具
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            return f"Error: Unknown tool: {tool_name}"

        # 解析参数
        try:
            params = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            return f"Error: Invalid tool arguments: {e}"

        # 执行工具
        try:
            result = tool.execute(params)
            return result
        except Exception as e:
            return f"Error: Tool execution failed: {e}"
