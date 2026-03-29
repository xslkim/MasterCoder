"""Tool registry for managing and registering tools."""

from typing import Any


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance with name, description, parameters, and execute method

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Any:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_openai_tools_schema(self) -> list[dict]:
        """
        Get all tools in OpenAI tools parameter format.

        Returns:
            List of tool schemas in OpenAI format
        """
        schemas = []
        for tool in self._tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            schemas.append(schema)
        return schemas

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())


# Global registry instance
_global_registry = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: Any) -> None:
    """
    Register a tool in the global registry.

    Args:
        tool: Tool instance to register
    """
    get_registry().register(tool)
