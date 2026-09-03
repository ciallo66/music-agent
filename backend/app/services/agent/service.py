"""Agent 会话用例服务。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.repositories.chat_repository import ChatRepository
from app.services.agent.orchestrator import AgentOrchestrator


class AgentSessionNotFoundError(ValueError):
    """请求的 Agent 会话不存在或不属于当前用户。"""


@dataclass(frozen=True)
class AgentConversation:
    """Agent 对话所需的会话标识和历史消息。"""

    session_id: int
    history: list[dict[str, str]]


class AgentService:
    """协调会话隔离、历史读取和 Agent 编排。"""

    def __init__(self, db: Session, user_id: int) -> None:
        """绑定当前用户和会话仓储，确保历史消息按用户隔离。"""
        self.db = db
        self.user_id = user_id
        self.chats = ChatRepository(db)

    def get_or_create_conversation(self, session_id: int | None) -> AgentConversation:
        """读取当前用户会话；未提供会话 ID 时创建新会话。"""
        chat_session: ChatSession
        if session_id is None:
            chat_session = self.chats.create_session(self.user_id)
        else:
            existing_session = self.chats.get_session(session_id, self.user_id)
            if existing_session is None:
                raise AgentSessionNotFoundError
            chat_session = existing_session
        history = [
            {"role": item.role, "content": item.content}
            for item in self.chats.list_messages(chat_session.id)
        ]
        return AgentConversation(session_id=chat_session.id, history=history)

    def stream(self, conversation: AgentConversation, message: str) -> Iterator[str]:
        """启动指定会话的 Agent SSE 流。"""
        return AgentOrchestrator(
            self.db,
            self.user_id,
            conversation.session_id,
            conversation.history,
        ).stream(message)
