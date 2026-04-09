"""
REQ-06: Tool Definition and Registration Framework

This module provides the base Tool interface and a registry for managing tools.
"""

from typing import Any, Optional
from abc import ABC, abstractmethod


class Tool(ABC):
    """Abstract base class defining the tool interface"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (e.g., 'read_file')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for AI understanding"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """Parameter definitions in JSON Schema format"""
        pass

    @abstractmethod
    def execute(self, params: dict) -> str:
        """Execute the tool with given parameters

        Args:
            params: Dictionary of parameters

        Returns:
            Execution result as string
        """
        pass


# Global tool registry
_registry: dict[str, Tool] = {}


def reset_registry() -> None:
    """Reset the tool registry (useful for testing)"""
    global _registry
    _registry = {}


def register_tool(tool: Tool) -> None:
    """Register a tool instance

    Args:
        tool: Tool instance to register

    Raises:
        ValueError: If a tool with the same name is already registered
    """
    if tool.name in _registry:
        raise ValueError(f"Tool already registered: {tool.name}")
    _registry[tool.name] = tool


def get_tool(name: str) -> Optional[Tool]:
    """Get a registered tool by name

    Args:
        name: Tool name

    Returns:
        Tool instance or None if not found
    """
    return _registry.get(name)


def get_openai_tools_schema() -> list[dict[str, Any]]:
    """Get all registered tools in OpenAI tools parameter format

    Returns:
        List of tool definitions in OpenAI format
    """
    schema = []
    for tool in _registry.values():
        tool_def = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        schema.append(tool_def)
    return schema
