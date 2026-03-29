"""工具基类定义。"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具基类，所有工具必须实现此接口。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称。"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述。"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """参数定义（JSON Schema 格式）。"""
        pass

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> str:
        """执行工具。

        Args:
            params: 工具参数字典

        Returns:
            执行结果字符串
        """
        pass

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI tools 参数格式。

        Returns:
            OpenAI 工具定义字典
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
