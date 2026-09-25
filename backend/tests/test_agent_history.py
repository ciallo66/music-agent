"""Agent 历史窗口、工具痕迹与待确认过期的测试。

这些用例对应线上实测到的问题：模型锚定在旧任务上复读上一轮答案、
忽略用户当前提问；以及过期未处理的确认记录长期挂在 pending。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.models.chat import ChatSession, decode_agent_notes, encode_agent_notes
from app.models.tool_confirmation import ToolConfirmation, ToolConfirmationStatus
from app.models.user import User
from app.repositories.tool_confirmation_repository import ToolConfirmationRepository
from app.services.agent.context import (
    build_history_message,
    extract_entities,
    format_tool_note,
    strip_tool_notes,
    tool_notes_from_history,
    window_history,
)
from app.services.agent.orchestrator import CONFIRMATION_ACK_MESSAGE, SYSTEM_PROMPT


def test_system_prompt_requires_following_the_current_message() -> None:
    """提示词必须明确要求以当前消息为准，并允许话题切换（线上问题的根因）。"""
    assert "只回答用户当前这一条消息" in SYSTEM_PROMPT
    assert "不要把上一轮的结果继续端上来" in SYSTEM_PROMPT
    assert "不要复述你已经给过的回答" in SYSTEM_PROMPT
    # 系统消息（确认回执）不能被当成用户的新提问
    assert "（系统消息）" in SYSTEM_PROMPT
    assert CONFIRMATION_ACK_MESSAGE.startswith("（系统消息）")


def test_window_history_keeps_recent_messages_and_marks_omissions() -> None:
    """历史按条数做滑动窗口，更早的折叠成一行说明。"""
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"第{index}条"}
        for index in range(10)
    ]

    windowed = window_history(history, max_messages=4)

    # 一行折叠说明 + 最近 4 条
    assert len(windowed) == 5
    assert windowed[0]["role"] == "system"
    assert "6 条对话已折叠" in str(windowed[0]["content"])
    assert [item["content"] for item in windowed[1:]] == ["第6条", "第7条", "第8条", "第9条"]


def test_window_history_never_starts_with_assistant_message() -> None:
    """窗口首条不能是 assistant，否则会出现「没有问题的回答」。"""
    history = [
        {"role": "user", "content": "问1"},
        {"role": "assistant", "content": "答1"},
        {"role": "user", "content": "问2"},
        {"role": "assistant", "content": "答2"},
    ]

    windowed = window_history(history, max_messages=3)

    assert windowed[0]["role"] == "system"
    assert windowed[1]["role"] == "user"
    kept = [item["content"] for item in windowed if item["role"] != "system"]
    # 窗口取最近 3 条（答1/问2/答2），但首条是 assistant，因此连带丢弃到首条 user
    assert kept == ["问1", "答1", "问2", "答2"][-2:]


def test_window_history_short_history_is_untouched() -> None:
    """历史未超出窗口时不加任何说明。"""
    history = [{"role": "user", "content": "问"}, {"role": "assistant", "content": "答"}]

    assert window_history(history, max_messages=20) == history


def test_history_message_attaches_notes_as_separate_field() -> None:
    """工具痕迹以独立字段回灌，绝不混进给用户看的正文。"""
    notes = encode_agent_notes(["search_songs(limit=20)"])
    assistant = build_history_message("assistant", "查到了 931 首", notes)
    user = build_history_message("user", "库里有几首歌", notes)

    assert assistant["content"] == "查到了 931 首"
    assert assistant["agent_notes"] == notes
    assert "tool:" not in assistant["content"]
    assert "agent_notes" not in user


def test_tool_notes_from_history_returns_recent_notes() -> None:
    """只取最近若干条工具痕迹，且按出现顺序排列。"""
    history = [
        build_history_message("assistant", "答1", encode_agent_notes(["search_songs()"])),
        build_history_message(
            "assistant",
            "答2",
            encode_agent_notes(["analyze_song(song_id=1)", "search_web()"]),
        ),
    ]

    notes = tool_notes_from_history(history, limit=2)

    assert notes == ["analyze_song(song_id=1)", "search_web()"]


def test_extract_entities_from_song_list() -> None:
    """歌曲列表要抽出 `id|标题|歌手`，供下一轮"第三首/就它"指代使用。"""
    result = {
        "items": [
            {"id": 1, "title": "All the Small Things", "artist": {"name": "blink-182"}},
            {"id": 2, "title": "Patterns in the Ivy", "artist": {"name": "Opeth"}},
            {"id": 3, "title": "Dry Hands", "artist": {"name": "C418"}},
            {"id": 4, "title": "超出上限的歌", "artist": {"name": "X"}},
        ]
    }

    entities = extract_entities(result)

    assert entities == [
        "1|All the Small Things|blink-182",
        "2|Patterns in the Ivy|Opeth",
        "3|Dry Hands|C418",
    ]


def test_extract_entities_from_playlists() -> None:
    """歌单列表同样要留 id 与名称（用户会说"加到那个歌单"）。"""
    entities = extract_entities({"playlists": [{"id": 7, "name": "夜晚通勤"}]})

    assert entities == ["7|夜晚通勤"]


def test_extract_entities_returns_empty_for_other_results() -> None:
    """没有可指代实体的结果（如品味分析）不产生清单。"""
    assert extract_entities({"genres": ["摇滚", "爵士"]}) == []
    assert extract_entities({}) == []


def test_format_tool_note_includes_arguments_and_entities() -> None:
    """痕迹行 = 工具名 + 关键参数 + 实体清单。"""
    note = format_tool_note(
        "search_songs",
        {"genre": "摇滚", "limit": 20},
        {"items": [{"id": 1, "title": "歌名", "artist": {"name": "歌手"}}]},
    )

    assert note.startswith("search_songs(")
    assert 'genre="摇滚"' in note
    assert "entities:[1|歌名|歌手]" in note


def test_agent_notes_encode_decode_roundtrip() -> None:
    """落库编码与读回解码必须一致；异常格式不抛错。"""
    assert encode_agent_notes([]) is None
    assert decode_agent_notes(None) == []
    assert decode_agent_notes("这不是 JSON") == []
    assert decode_agent_notes('{"a":1}') == []
    raw = encode_agent_notes(["tool:search_songs()", "tool:list_playlists()"])
    assert decode_agent_notes(raw) == ["tool:search_songs()", "tool:list_playlists()"]


def test_tool_notes_skip_non_string_content() -> None:
    """历史里出现非字符串内容（如仅工具调用的助手消息）时不报错。"""
    history: list[dict[str, Any]] = [
        {"role": "assistant", "content": None},
        {"role": "user", "content": "问题"},
    ]

    assert tool_notes_from_history(history, limit=5) == []


def test_tool_notes_are_stripped_from_user_visible_content() -> None:
    """工具痕迹只给模型看，界面上必须剥掉（否则刷新后气泡里会露出 tool:xxx）。"""
    stored = "库里共 931 首。\ntool:search_songs(limit=20)\ntool:analyze_song(song_id=1)"

    visible = strip_tool_notes(stored)

    assert visible == "库里共 931 首。"
    assert "tool:" not in visible


def test_strip_tool_notes_keeps_plain_answers_intact() -> None:
    """没有痕迹行的回答原样返回，不做多余改动。"""
    assert strip_tool_notes("这是一条普通回答。") == "这是一条普通回答。"


def test_expire_outdated_marks_stale_pending_records(db_session: Any) -> None:
    """过期未处理的确认记录要收敛为 expired，不再挂在 pending。"""
    user = User(username="history-test-user", password_hash="x", role="user")
    db_session.add(user)
    db_session.flush()
    chat_session = ChatSession(user_id=user.id)
    db_session.add(chat_session)
    db_session.flush()

    stale = ToolConfirmation(
        session_id=chat_session.id,
        user_id=user.id,
        call_id="call-stale",
        tool_name="create_playlist",
        operation="write",
        arguments={"name": "旧歌单"},
        reason="测试",
        status=ToolConfirmationStatus.PENDING.value,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    fresh = ToolConfirmation(
        session_id=chat_session.id,
        user_id=user.id,
        call_id="call-fresh",
        tool_name="create_playlist",
        operation="write",
        arguments={"name": "新歌单"},
        reason="测试",
        status=ToolConfirmationStatus.PENDING.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add_all([stale, fresh])
    db_session.flush()

    expired_count = ToolConfirmationRepository(db_session).expire_outdated()

    assert expired_count == 1
    db_session.refresh(stale)
    db_session.refresh(fresh)
    assert stale.status == ToolConfirmationStatus.EXPIRED.value
    assert fresh.status == ToolConfirmationStatus.PENDING.value


def test_history_window_config_has_safe_defaults() -> None:
    """默认窗口要足够小以抑制"锚定"，又不至于把上下文砍到无法对话。"""
    assert 4 <= settings.agent_history_max_messages <= 40
    assert 0 <= settings.agent_history_tool_notes <= settings.agent_history_max_messages
