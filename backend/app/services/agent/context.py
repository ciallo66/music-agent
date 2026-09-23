"""Agent 上下文窗口估算和历史消息压缩。"""

from __future__ import annotations

import json
from typing import Any


def estimate_tokens(value: object) -> int:
    """使用无额外依赖的保守估算计算消息 token 数。"""
    if isinstance(value, str):
        serialized = value
    else:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    return max(1, (len(serialized) + 3) // 4)


def serialize_tool_result(result: dict[str, Any], max_chars: int) -> str:
    """序列化工具结果并限制其长度，避免单次查询挤满上下文。"""
    if max_chars <= 0:
        raise ValueError("工具结果长度限制必须大于 0")
    serialized = json.dumps(result, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return serialized

    marker = "…[工具结果已截断]"
    preview_limit = max(0, max_chars - 64)
    compact = {
        "truncated": True,
        "preview": f"{serialized[:preview_limit]}{marker}",
    }
    compact_serialized = json.dumps(compact, ensure_ascii=False)
    if len(compact_serialized) <= max_chars:
        return compact_serialized
    return json.dumps({"truncated": True}, ensure_ascii=False)


def tool_notes_from_history(history: list[dict[str, Any]], limit: int) -> list[str]:
    """从历史消息里提取"调用过哪些工具"的简短记录。

    工具调用记录以 `tool:<名称>(<参数摘要>)` 的形式写在 assistant 消息上（见
    `build_history_message`）。这里只取最近 limit 条，用来提醒模型别重复查同一件事；
    不携带旧工具结果，避免旧数据挤占上下文并诱导模型复述旧答案。
    """
    if limit <= 0:
        return []
    notes: list[str] = []
    for message in history:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if line.startswith("tool:"):
                notes.append(line.strip()[len("tool:") :].strip())
    return [note for note in notes if note][-limit:]


TOOL_NOTE_PREFIX = "tool:"


def strip_tool_notes(text: str) -> str:
    """去掉助手正文末尾的工具痕迹行，得到用户可见的纯回答。

    工具痕迹（`tool:名称(参数)`）只给模型看，不能出现在界面上：
    它随助手消息落库，而会话读取与前端渲染都是原样展示，不做处理就会泄漏成气泡里的技术噪音。
    """
    kept = [line for line in text.splitlines() if not line.startswith(TOOL_NOTE_PREFIX)]
    return "\n".join(kept).rstrip()


def build_history_message(
    role: str, content: str, tools: list[str] | None = None
) -> dict[str, str]:
    """把一条存储消息转换成交给模型的 history 消息。

    助手消息若调用过工具，会在正文末尾追加 `tool:<名称>(<参数摘要>)` 记录：
    模型因此知道"这件事已经查过了"，而不需要把旧工具结果原文带进上下文。
    """
    text = content
    if role == "assistant" and tools:
        text = f"{content}\n" + "\n".join(f"tool:{note}" for note in tools)
    return {"role": role, "content": text}


def window_history(messages: list[dict[str, Any]], max_messages: int) -> list[dict[str, Any]]:
    """按条数对历史做滑动窗口，返回可直接拼进请求的历史。

    依据：主流对话产品给模型的是"最近若干轮 + 更早内容的摘要"，而不是无限堆历史。
    历史越长，模型越容易锚定在旧任务上（线上实测出现过复读上一轮答案、忽略当前提问）。
    这里保留最近 max_messages 条，并在窗口开头插入一行折叠说明；
    窗口首条若是 assistant，会一直丢弃到首条 user 为止，避免出现"没有问题的回答"。
    """
    if max_messages <= 0:
        raise ValueError("历史窗口大小必须大于 0")
    if not messages:
        return []

    kept = [dict(message) for message in messages[-max_messages:]]
    omitted = len(messages) - len(kept)

    while kept and kept[0].get("role") != "user":
        kept.pop(0)
        omitted += 1
    if not kept:
        return []

    if omitted <= 0:
        return kept
    head = {
        "role": "system",
        "content": f"更早的 {omitted} 条对话已折叠，仅作背景参考；请以用户当前消息为准。",
    }
    return [head, *kept]


def compact_messages(
    messages: list[dict[str, Any]], max_tokens: int, current_turn_index: int
) -> tuple[list[dict[str, Any]], int]:
    """保留当前轮消息并从最旧历史开始压缩上下文。

    这里不引入特定模型 tokenizer，而是使用稳定的字符估算；实际请求仍由模型服务
    决定最终 token 数。返回值同时给出当前轮在新列表中的起始下标，避免后续工具
    调用时误删本轮 assistant/tool 消息。
    """
    if max_tokens <= 0:
        raise ValueError("上下文 token 预算必须大于 0")
    if not messages:
        return [], 0

    has_system = messages[0].get("role") == "system"
    history_start = 1 if has_system else 0
    turn_start = max(history_start, min(current_turn_index, len(messages)))
    system = [dict(messages[0])] if has_system else []
    history = messages[history_start:turn_start]
    active = [dict(message) for message in messages[turn_start:]]

    active_budget = max(1, max_tokens - estimate_tokens(system))
    active = _fit_active_messages(active, active_budget)
    prefix = list(system)
    available = max(0, max_tokens - estimate_tokens(prefix + active))
    kept_history: list[dict[str, Any]] = []
    omitted = 0
    for message in reversed(history):
        if estimate_tokens([*prefix, message, *kept_history, *active]) <= max_tokens:
            kept_history.insert(0, dict(message))
        else:
            omitted += 1

    if omitted:
        notice = {
            "role": "system",
            "content": f"较早的 {omitted} 条对话已省略，请以当前问题和保留上下文为准。",
        }
        if estimate_tokens(
            [*prefix, notice, *kept_history, *active]
        ) <= max_tokens or available >= estimate_tokens(notice):
            prefix.append(notice)

    result = prefix + kept_history + active
    return result, len(prefix) + len(kept_history)


def _fit_active_messages(messages: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
    """优先截断工具结果，保证当前轮仍能发送给模型。"""
    if estimate_tokens(messages) <= max_tokens:
        return messages

    suffix = "\n[上下文已截断]"
    for role in ("tool", "assistant", "user"):
        for message in messages:
            if message.get("role") != role or not isinstance(message.get("content"), str):
                continue
            if estimate_tokens(messages) <= max_tokens:
                return messages
            content = str(message["content"])
            excess_chars = max(32, (estimate_tokens(messages) - max_tokens) * 4)
            target_length = max(0, len(content) - excess_chars)
            if target_length <= len(suffix):
                message["content"] = suffix[:target_length]
            else:
                message["content"] = content[: target_length - len(suffix)] + suffix

    return messages
