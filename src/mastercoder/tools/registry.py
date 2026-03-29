"""工具注册器。"""

from typing import Any
from mastercoder.tools.base import BaseTool


class ToolRegistry:
    """工具注册器，管理所有已注册的工具。"""

    def __init__(self) -> None:
        """初始化工具注册器。"""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具。

        Args:
            tool: 工具实例

        Raises:
            ValueError: 工具名称已存在
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """获取工具。

        Args:
            name: 工具名称

        Returns:
            工具实例，不存在则返回 None
        """
        return self._tools.get(name)

    def get_openai_tools_schema(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI tools 参数格式。

        Returns:
            OpenAI tools 参数数组
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称。

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())


def register_all_tools(registry: ToolRegistry) -> None:
    """注册所有工具。

    Args:
        registry: 工具注册器实例
    """
    # 延迟导入以避免循环依赖
    from mastercoder.tools.read_file import ReadFileTool
    from mastercoder.tools.write_file import WriteFileTool
    from mastercoder.tools.edit_file import EditFileTool
    from mastercoder.tools.list_files import ListFilesTool
    from mastercoder.tools.search_files import SearchFilesTool
    from mastercoder.tools.run_command import RunCommandTool

    # 注册所有 6 个工具
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(ListFilesTool())
    registry.register(SearchFilesTool())
    registry.register(RunCommandTool())
