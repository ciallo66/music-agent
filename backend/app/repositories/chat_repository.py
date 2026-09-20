"""Agent 会话数据访问。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession


class ChatRepository:
    """封装用户会话隔离和消息读写。"""

    def __init__(self, db: Session) -> None:
        """保存请求级数据库会话，后续读写都复用该会话。"""
        self.db = db

    def create_session(self, user_id: int) -> ChatSession:
        """创建当前用户的新会话。"""
        session = ChatSession(user_id=user_id)
        self.db.add(session)
        self.db.flush()
        return session

    def get_session(self, session_id: int, user_id: int) -> ChatSession | None:
        """读取属于当前用户的会话。"""
        statement = select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
        return self.db.scalar(statement)

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        """按创建顺序读取会话消息。"""
        statement = (
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)
        )
        return list(self.db.scalars(statement))

    def list_sessions(
        self, user_id: int, limit: int = 30
    ) -> list[tuple[ChatSession, int, int | None]]:
        """按最近活跃倒序列出当前用户的会话，并带上消息条数与最后一条消息 ID。

        会话本身没有更新时间的列，所以用「最后一条消息的 id」代表活跃度：
        id 越大说明越新，且不依赖额外的写入。
        """
        statement = (
            select(
                ChatSession,
                func.count(ChatMessage.id),
                func.max(ChatMessage.id),
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .order_by(func.max(ChatMessage.id).desc().nullslast(), ChatSession.id.desc())
            .limit(limit)
        )
        return [(row[0], row[1], row[2]) for row in self.db.execute(statement)]

    def first_user_messages(self, session_ids: list[int]) -> dict[int, str]:
        """取每个会话的第一条用户消息，用作会话标题。"""
        if not session_ids:
            return {}
        statement = (
            select(ChatMessage.session_id, ChatMessage.content)
            .where(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.session_id, ChatMessage.id)
        )
        titles: dict[int, str] = {}
        for session_id, content in self.db.execute(statement):
            titles.setdefault(session_id, content)
        return titles

    def delete_session(self, session_id: int, user_id: int) -> bool:
        """删除属于当前用户的会话及其消息，返回是否删掉了记录。"""
        session = self.get_session(session_id, user_id)
        if session is None:
            return False
        self.db.delete(session)
        self.db.flush()
        return True

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        """追加一条消息并刷新主键。"""
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.flush()
        return message
