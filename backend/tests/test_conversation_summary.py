"""滚动摘要测试。

对应的问题：历史窗口一裁，用户最初提的限制条件就没了，长对话里"接着刚才的条件再筛"
会答偏。这里验证摘要的触发条件、增量行为，以及两个必须防住的坑：
① 摘要为空时不能静默丢历史（推理模型会把 max_tokens 全花在思考上，实测 300/900 都不够）；
② 摘要调用失败不能影响本轮回答。
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.services.agent.conversation_summary import (
    SUMMARY_MAX_TOKENS,
    ConversationSummarizer,
)
from app.services.agent.provider import LLMProviderError, ModelResponse


class _RecordingProvider:
    """记录调用参数的假模型，避免测试发真实请求。"""

    def __init__(self, content: str | None = "摘要要点", raises: bool = False) -> None:
        """保存待返回内容或失败开关。"""
        self.content = content
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int | None = None,
        disable_reasoning: bool = False,
    ) -> ModelResponse:
        """记录入参并返回预设结果。"""
        self.calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "disable_reasoning": disable_reasoning,
            }
        )
        if self.raises:
            raise LLMProviderError("模型不可用")
        return ModelResponse(content=self.content, tool_calls=[])


def _make_session(db: Any, message_count: int) -> ChatSession:
    """建一个带 N 条消息的会话，便于触发窗口与折叠阈值。"""
    user = User(username=f"summary-user-{message_count}", password_hash="x", role="user")
    db.add(user)
    db.flush()
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.flush()
    for index in range(message_count):
        db.add(
            ChatMessage(
                session_id=session.id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"第{index}条消息",
            )
        )
    db.flush()
    return session


def test_short_conversation_is_not_summarized(db_session: Any) -> None:
    """历史没超过窗口时不做任何压缩，也不调用模型。"""
    session = _make_session(db_session, settings.agent_history_max_messages)
    provider = _RecordingProvider()

    summary, recent = ConversationSummarizer(db_session, provider).prepare(session)

    assert summary is None
    assert len(recent) == settings.agent_history_max_messages
    assert provider.calls == []


def test_long_conversation_triggers_summary(db_session: Any) -> None:
    """超过 窗口 + 折叠阈值 时压缩，并只保留最近一窗口的原文。"""
    total = settings.agent_history_max_messages + settings.agent_summary_fold_batch + 2
    session = _make_session(db_session, total)
    provider = _RecordingProvider(content="用户要器乐为主的舒缓歌曲；结论：Dry Hands 更慢")

    summary, recent = ConversationSummarizer(db_session, provider).prepare(session)

    assert summary is not None and "Dry Hands" in summary
    assert len(recent) == settings.agent_history_max_messages
    # 摘要请求必须给足 max_tokens 并关闭思考链：否则思考会吃光额度、正文返回空（已实测）
    assert provider.calls[0]["max_tokens"] == SUMMARY_MAX_TOKENS
    assert provider.calls[0]["max_tokens"] >= 2000
    assert provider.calls[0]["disable_reasoning"] is True
    # 摘要落库，供后续增量使用
    assert session.chat_summary == summary
    assert session.summarized_through_id is not None


def test_summary_is_incremental(db_session: Any) -> None:
    """已经摘要过的部分不再重复送入模型（增量压缩）。"""
    total = settings.agent_history_max_messages + settings.agent_summary_fold_batch + 2
    session = _make_session(db_session, total)
    provider = _RecordingProvider()
    summarizer = ConversationSummarizer(db_session, provider)

    summarizer.prepare(session)
    assert len(provider.calls) == 1

    # 再问一轮（只多一条消息，滑出窗口的内容不够一批）→ 不应再次调用模型
    db_session.add(ChatMessage(session_id=session.id, role="user", content="再问一句"))
    db_session.flush()
    summarizer.prepare(session)

    assert len(provider.calls) == 1


def test_empty_summary_falls_back_to_full_history(db_session: Any) -> None:
    """摘要为空时必须退回原窗口行为，而不是把历史摘要成空。"""
    total = settings.agent_history_max_messages + settings.agent_summary_fold_batch + 2
    session = _make_session(db_session, total)
    provider = _RecordingProvider(content="")

    summary, recent = ConversationSummarizer(db_session, provider).prepare(session)

    assert summary is None
    # 退回未裁剪的历史，保证模型仍能看到内容
    assert len(recent) == total
    assert session.chat_summary is None


def test_summary_failure_does_not_break_turn(db_session: Any) -> None:
    """模型调用失败时同样退回，不影响本轮回答。"""
    total = settings.agent_history_max_messages + settings.agent_summary_fold_batch + 2
    session = _make_session(db_session, total)
    provider = _RecordingProvider(raises=True)

    summary, recent = ConversationSummarizer(db_session, provider).prepare(session)

    assert summary is None
    assert len(recent) == total
    assert session.summarized_through_id is None


def test_folded_transcript_excludes_system_messages(db_session: Any) -> None:
    """送入摘要的只有用户与助手文本，不包含系统消息。"""
    total = settings.agent_history_max_messages + settings.agent_summary_fold_batch + 2
    session = _make_session(db_session, total)
    db_session.add(ChatMessage(session_id=session.id, role="system", content="（系统消息）确认"))
    db_session.flush()
    provider = _RecordingProvider()

    ConversationSummarizer(db_session, provider).prepare(session)

    prompt = provider.calls[0]["messages"][-1]["content"]
    assert "（系统消息）确认" not in prompt
    assert "第0条消息" in prompt
