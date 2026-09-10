"""Agent 工具调用的运行时安全策略。

身份和权限一律由服务端决定：工具处理器通过构造注入拿到当前登录用户，
不接受模型传入的身份字段；因此这里的策略只做三件事——
拦截身份参数、按操作类型判断是否需要用户确认、其余放行。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.services.agent.registry import AgentTool, ToolOperation

# 这些字段代表"谁在操作"，只能由服务端根据登录态确定，禁止由模型填写。
IDENTITY_ARGUMENT_KEYS = frozenset({"user_id", "owner_id", "account_id", "session_id"})


class ToolDecision(str, Enum):
    """一次工具调用的处置结论。"""

    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class ToolPolicyResult:
    """策略判定结果：结论 + 给模型或前端看的说明。"""

    decision: ToolDecision
    reason: str = ""


def evaluate_tool_call(
    tool: AgentTool, arguments: dict[str, Any], *, confirmed: bool = False
) -> ToolPolicyResult:
    """判定一次工具调用能否直接执行。

    - 参数里出现身份字段：拒绝（身份由服务端注入，模型无权指定）；
    - 只读操作：直接执行；
    - 写/删操作：需要用户确认，除非本次调用已被用户确认过。
    """
    forbidden = sorted(IDENTITY_ARGUMENT_KEYS.intersection(arguments))
    if forbidden:
        return ToolPolicyResult(
            ToolDecision.DENY,
            f"参数不允许包含身份字段：{', '.join(forbidden)}",
        )
    undeclared = sorted(set(arguments) - set(tool.parameters.get("properties", {})))
    if undeclared:
        return ToolPolicyResult(
            ToolDecision.DENY,
            f"参数包含工具未声明的字段：{', '.join(undeclared)}",
        )
    if tool.operation is ToolOperation.READ or confirmed:
        return ToolPolicyResult(ToolDecision.ALLOW)
    return ToolPolicyResult(ToolDecision.CONFIRM, f"{tool.operation.value} 操作需要用户确认")
