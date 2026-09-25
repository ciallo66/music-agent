"""Agent 会话与消息模型。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ChatSession(Base):
    """隔离不同用户 Agent 对话的会话。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # 滚动摘要：把已经滑出窗口的历史压成要点，避免长对话"忘掉早期约束"。
    chat_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 摘要已经覆盖到哪条消息（chat_messages.id）。只增量压缩它之后的消息，
    # 因此不必每轮重算摘要——长对话下最多每折叠一批才调用一次模型。
    summarized_through_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """会话中的用户或 Agent 文本消息。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    # 本轮调用过的工具痕迹与实体清单（JSON 文本）。与 content 分开存的原因：
    # content 是给用户看的正文，不能混进 `tool:xxx` 这类内部标记；
    # 而 entity_notes 只回灌给模型的上下文，用来避免"第三首/就它"这类指代断裂。
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")


def encode_agent_notes(notes: list[str] | None) -> str | None:
    """把工具痕迹与实体清单编码成落库用的 JSON 文本；空值时返回 None。"""
    return json.dumps(notes, ensure_ascii=False) if notes else None


def decode_agent_notes(raw: str | None) -> list[str]:
    """把落库的 JSON 文本还原成痕迹列表；格式异常时返回空列表而不是抛错。"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]
