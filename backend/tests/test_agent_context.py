"""Agent 上下文预算测试。"""

from __future__ import annotations

import json
from typing import Any

from app.services.agent.context import compact_messages, serialize_tool_result


def test_compact_messages_keeps_current_turn_and_drops_old_history() -> None:
    """上下文超预算时应优先保留当前问题和最新可用信息。"""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "系统规则"},
        {"role": "user", "content": "很早的问题 " * 80},
        {"role": "assistant", "content": "很早的回答 " * 80},
        {"role": "user", "content": "当前问题"},
    ]

    compacted, current_turn_index = compact_messages(messages, max_tokens=80, current_turn_index=3)

    assert compacted[current_turn_index] == {"role": "user", "content": "当前问题"}
    assert all("很早" not in str(message) for message in compacted)


def test_compact_messages_truncates_large_tool_output() -> None:
    """单个工具结果过大时应截断内容而不是删除当前轮。"""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "系统规则"},
        {"role": "user", "content": "分析歌曲"},
        {"role": "assistant", "content": None, "tool_calls": []},
        {"role": "tool", "content": "工具结果 " * 500},
    ]

    compacted, current_turn_index = compact_messages(messages, max_tokens=80, current_turn_index=1)

    assert compacted[current_turn_index]["role"] == "user"
    tool_message = next(message for message in compacted if message["role"] == "tool")
    assert "上下文已截断" in tool_message["content"]


def test_serialize_tool_result_respects_limit() -> None:
    """工具结果序列化后不能超过配置的字符上限。"""
    serialized = serialize_tool_result({"items": ["结果"] * 100}, max_chars=80)

    assert len(serialized) <= 80
    assert json.loads(serialized)["truncated"] is True
