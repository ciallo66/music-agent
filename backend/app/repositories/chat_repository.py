"""Agent 会话数据访问。"""

from __future__ import annotations

from sqlalchemy import select
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

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        """追加一条消息并刷新主键。"""
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.flush()
        return message
