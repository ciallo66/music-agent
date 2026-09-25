"""Agent 上下文窗口估算和历史消息压缩。"""

from __future__ import annotations

import json
from typing import Any

from app.models.chat import decode_agent_notes, encode_agent_notes


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


TOOL_NOTE_PREFIX = "tool:"

# 每次工具调用最多保留多少个实体（歌曲/歌单）进历史。
# 依据：主流做法是「旧工具结果整体清理，只留最近少量实体」——留多了会挤占上下文，
# 留少了"把第三首加进歌单"这类指代会断。3 个够覆盖常见的"第一/二/三首"。
MAX_ENTITIES_PER_CALL = 3

# 可能承载"列表型实体"的结果字段及其标题/歌手字段名。
ENTITY_LIST_KEYS: tuple[tuple[str, str, str], ...] = (
    ("items", "title", "artist"),
    ("songs", "title", "artist"),
    ("matches", "title", "artist"),
)


def _entity_line(item: dict[str, Any], title_key: str, artist_key: str) -> str | None:
    """把一条结果渲染成 `id|标题|歌手`；没有标题时返回 None。"""
    title = item.get(title_key) or item.get("name")
    if not title:
        return None
    artist = item.get(artist_key)
    if isinstance(artist, dict):
        artist = artist.get("name")
    parts = [str(item.get("id", "")), str(title)]
    if artist:
        parts.append(str(artist))
    return "|".join(parts)


def extract_entities(result: dict[str, Any]) -> list[str]:
    """从工具结果里抽取"用户可能接着指代"的实体，格式 `id|标题|歌手`。

    只抽歌曲与歌单：这两类是用户会接着说"就它/第三首/加到那个歌单"的对象。
    其它字段（BPM、情绪标签等）不复述——它们不是指代目标，留多了只会误导模型复读。
    """
    for key, title_key, artist_key in ENTITY_LIST_KEYS:
        raw_items = result.get(key)
        if not isinstance(raw_items, list):
            continue
        lines = [
            _entity_line(item, title_key, artist_key)
            for item in raw_items[:MAX_ENTITIES_PER_CALL]
            if isinstance(item, dict)
        ]
        found = [line for line in lines if line]
        if found:
            return found

    # 歌单列表：用户会说"加到那个歌单"，所以同样要留 id 与名称
    raw_playlists = result.get("playlists")
    if isinstance(raw_playlists, list):
        return [
            f"{item.get('id', '')}|{item['name']}"
            for item in raw_playlists[:MAX_ENTITIES_PER_CALL]
            if isinstance(item, dict) and item.get("name")
        ]
    return []


def tool_notes_from_history(history: list[dict[str, Any]], limit: int) -> list[str]:
    """从历史的 `agent_notes` 字段里取最近的工具痕迹与实体清单。

    每条形如 `tool:search_songs(query="摇滚") -> entities:[1|歌名|歌手]`。
    这里只回灌这些痕迹，不回灌旧工具结果原文——既避免旧数据挤占上下文、
    也避免诱导模型复述上一轮的答案。
    """
    if limit <= 0:
        return []
    notes: list[str] = []
    for message in history:
        notes.extend(decode_agent_notes(message.get("agent_notes")))
    return notes[-limit:]


def build_history_message(role: str, content: str, notes: str | None = None) -> dict[str, Any]:
    """把一条存储消息转换成交给模型的 history 消息。

    `notes` 是本轮工具痕迹与实体清单（JSON 文本），作为独立字段随消息传给模型：
    content 保持"给用户看的正文"不变，不会被内部标记污染。
    """
    message: dict[str, Any] = {"role": role, "content": content}
    if role == "assistant" and notes:
        message["agent_notes"] = notes
    return message


def format_tool_note(
    name: str, arguments: dict[str, Any], result: dict[str, Any] | None = None
) -> str:
    """生成一行工具痕迹：名称 + 关键参数 +（可选）实体清单。"""
    parts: list[str] = []
    for key, value in list(arguments.items())[:4]:
        rendered = json.dumps(value, ensure_ascii=False)
        if len(rendered) > 40:
            rendered = rendered[:40] + "…"
        parts.append(f"{key}={rendered}")
    note = f"{name}({', '.join(parts)})" if parts else f"{name}()"
    entities = extract_entities(result) if result else []
    if entities:
        note += " -> entities:[" + "; ".join(entities) + "]"
    return note


def strip_tool_notes(text: str) -> str:
    """去掉正文里的工具痕迹行，得到用户可见的纯回答。

    痕迹现在单独存在 `agent_notes` 列里，正常不会再混进正文；
    这个函数保留为兜底：老数据（修复前落库的消息）里可能已被写入 `tool:` 行。
    """
    kept = [line for line in text.splitlines() if not line.startswith(TOOL_NOTE_PREFIX)]
    return "\n".join(kept).rstrip()


def encode_notes(notes: list[str]) -> str | None:
    """把工具痕迹列表编码成落库用的 JSON 文本；空列表返回 None。"""
    return encode_agent_notes(notes)


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
