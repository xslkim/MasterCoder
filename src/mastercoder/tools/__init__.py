"""MasterCoder 工具模块。"""

from typing import Any


class BaseTool:
    """工具基类。"""

    @property
    def name(self) -> str:
        """工具名称。"""
        raise NotImplementedError

    @property
    def description(self) -> str:
        """工具描述。"""
        raise NotImplementedError

    @property
    def parameters(self) -> dict[str, Any]:
        """参数定义（JSON Schema 格式）。"""
        raise NotImplementedError

    def execute(self, params: dict[str, Any]) -> str:
        """执行工具。

        Args:
            params: 工具参数

        Returns:
            执行结果字符串
        """
        raise NotImplementedError


__all__ = ["BaseTool"]
