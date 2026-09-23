"""Agent 历史窗口、工具痕迹与待确认过期的测试。

这些用例对应线上实测到的问题：模型锚定在旧任务上复读上一轮答案、
忽略用户当前提问；以及过期未处理的确认记录长期挂在 pending。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.models.chat import ChatSession
from app.models.tool_confirmation import ToolConfirmation, ToolConfirmationStatus
from app.models.user import User
from app.repositories.tool_confirmation_repository import ToolConfirmationRepository
from app.services.agent.context import (
    build_history_message,
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


def test_history_message_appends_tool_notes_only_for_assistant() -> None:
    """工具痕迹附在助手消息末尾，用户消息不受影响。"""
    assistant = build_history_message("assistant", "查到了 931 首", ["search_songs(limit=20)"])
    user = build_history_message("user", "库里有几首歌", ["search_songs(limit=20)"])

    assert assistant["content"].endswith("tool:search_songs(limit=20)")
    assert "tool:" not in user["content"]


def test_tool_notes_from_history_returns_recent_notes() -> None:
    """只取最近若干条工具痕迹，且按出现顺序排列。"""
    history = [
        build_history_message("assistant", "答1", ["search_songs()"]),
        build_history_message("assistant", "答2", ["analyze_song(song_id=1)", "search_web()"]),
    ]

    notes = tool_notes_from_history(history, limit=2)

    # 返回的是去掉 `tool:` 前缀后的记录，按出现顺序排列
    assert notes == ["analyze_song(song_id=1)", "search_web()"]


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
