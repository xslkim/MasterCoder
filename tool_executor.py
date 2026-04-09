"""
REQ-07: 工具调用执行引擎

实现工具调用的执行引擎，处理AI返回的tool_calls，执行工具并返回结果。
"""

import json
from typing import Dict, Any, List, Optional


class ToolRegistry:
    """工具注册器，管理可用工具的注册和查找。"""

    def __init__(self):
        """初始化工具注册器"""
        self._tools: Dict[str, Any] = {}

    def register(self, name: str, tool: Any) -> None:
        """注册工具"""
        self._tools[name] = tool

    def get(self, name: str) -> Optional[Any]:
        """获取工具，若不存在则返回 None"""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools


class ToolExecutor:
    """工具调用执行引擎，处理AI返回的tool_calls，管理用户确认流程，执行工具并返回结果。"""

    MAX_NESTED_DEPTH = 20

    def __init__(
        self,
        registry: ToolRegistry,
        message_manager: Any,
        api_client: Any,
        auto_approve: bool = False,
    ):
        """初始化工具执行器"""
        self.registry = registry
        self.message_manager = message_manager
        self.api_client = api_client
        self.auto_approve = auto_approve
        self._nested_depth = 0

    def _display_tool_call_info(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """显示工具调用信息"""
        print(f"\nTool call: {tool_name}")
        print("Arguments:")
        for key, value in arguments.items():
            print(f"  {key}: {repr(value)}")
        print()

    def _get_user_confirmation(self) -> str:
        """获取用户确认：返回 'Y', 'N', 或 'A'"""
        while True:
            try:
                choice = input("[Y]es / [N]o / [A]lways > ").strip().upper()

                if choice in ["Y", "YES", ""]:
                    return "Y"
                elif choice in ["N", "NO"]:
                    return "N"
                elif choice in ["A", "ALWAYS"]:
                    return "A"
                else:
                    print("Invalid choice. Please enter Y, N, or A.")
            except EOFError:
                return "N"

    def _execute_single_tool(self, tool_call: Dict[str, Any]) -> str:
        """执行单个工具调用，返回结果字符串"""
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")
        arguments_str = function_info.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str) if arguments_str else {}
        except json.JSONDecodeError as e:
            return f"Error: Invalid tool arguments: {str(e)}"

        tool = self.registry.get(tool_name)
        if tool is None:
            return f"Error: Unknown tool: {tool_name}"

        try:
            result = tool.execute(arguments)
            return str(result) if result is not None else ""
        except Exception as e:
            return f"Error: Tool execution failed: {str(e)}"

    def _process_tool_call_with_confirmation(self, tool_call: Dict[str, Any]) -> str:
        """处理单个工具调用（含用户确认）"""
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")
        arguments_str = function_info.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str) if arguments_str else {}
        except json.JSONDecodeError:
            arguments = {}

        if not self.auto_approve:
            self._display_tool_call_info(tool_name, arguments)
            choice = self._get_user_confirmation()

            if choice == "N":
                return "Tool call was rejected by user"
            elif choice == "A":
                self.auto_approve = True

        return self._execute_single_tool(tool_call)

    def _process_tool_calls_batch(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理一批工具调用，返回工具结果消息列表"""
        tool_messages = []

        for tool_call in tool_calls:
            result = self._process_tool_call_with_confirmation(tool_call)

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result,
            }
            tool_messages.append(tool_message)

        return tool_messages

    def execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]], assistant_content: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """执行工具调用并处理后续API调用"""
        if self._nested_depth == 0:
            self._nested_depth = 1

        if self._nested_depth > self.MAX_NESTED_DEPTH:
            return {
                "content": f"Error: Maximum tool call depth ({self.MAX_NESTED_DEPTH}) exceeded. Please provide a final response.",
                "tool_calls": None,
            }

        self.message_manager.add_message(
            role="assistant", content=assistant_content, tool_calls=tool_calls
        )

        tool_messages = self._process_tool_calls_batch(tool_calls)

        for tool_msg in tool_messages:
            self.message_manager.add_message(
                role=tool_msg["role"],
                content=tool_msg["content"],
                tool_call_id=tool_msg["tool_call_id"],
            )

        messages = self.message_manager.get_messages()
        api_response = self.api_client.call_api(messages)

        if api_response.get("tool_calls"):
            self._nested_depth += 1

            result = self.execute_tool_calls(
                tool_calls=api_response["tool_calls"], assistant_content=api_response.get("content")
            )

            self._nested_depth -= 1

            return result
        else:
            return api_response

    def reset(self) -> None:
        """重置执行器状态"""
        self._nested_depth = 0
