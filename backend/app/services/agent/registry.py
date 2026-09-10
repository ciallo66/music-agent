"""Agent 工具注册中心。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolOperation(str, Enum):
    """工具的操作类型，供运行时安全策略判断。"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


@dataclass(frozen=True)
class AgentTool:
    """一个白名单 Agent 工具。"""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    operation: ToolOperation = ToolOperation.READ

    def definition(self) -> dict[str, Any]:
        """转换为模型 API 使用的 function tool 定义。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """管理 Agent 可调用工具，拒绝未注册工具。"""

    def __init__(self) -> None:
        """初始化工具表；注册阶段完成后只按白名单名称调用。"""
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """注册工具，重复名称直接拒绝。"""
        if tool.name in self._tools:
            raise ValueError(f"工具已注册：{tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool | None:
        """按名称返回工具定义；未注册时返回 None。"""
        return self._tools.get(name)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """调用白名单工具。"""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"未知工具：{name}")
        return tool.handler(arguments)

    def definitions(self) -> list[dict[str, Any]]:
        """返回全部工具定义。"""
        return [tool.definition() for tool in self._tools.values()]

    def names(self) -> tuple[str, ...]:
        """返回已注册工具名称。"""
        return tuple(self._tools)
