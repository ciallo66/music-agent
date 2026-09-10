"""Agent 会话用例服务。"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.models.tool_confirmation import ToolConfirmationStatus
from app.repositories.chat_repository import ChatRepository
from app.repositories.tool_confirmation_repository import ToolConfirmationRepository
from app.schemas.agent import ToolConfirmationDecision
from app.services.agent.orchestrator import AgentOrchestrator, ToolResolution
from app.services.agent.provider import ToolCall


class AgentSessionNotFoundError(ValueError):
    """请求的 Agent 会话不存在或不属于当前用户。"""


class AgentConfirmationError(ValueError):
    """待确认工具调用的处理请求无效。"""


logger = logging.getLogger(__name__)


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
        self.confirmations = ToolConfirmationRepository(db)

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

    def confirm(
        self, conversation: AgentConversation, decisions: list[ToolConfirmationDecision]
    ) -> Iterator[str]:
        """按用户决定执行或拒绝待确认调用，并继续本轮推理。

        参数一律以服务端登记的记录为准，客户端只能决定"同意/拒绝"。
        """
        pending = {
            record.id: record
            for record in self.confirmations.list_pending(conversation.session_id, self.user_id)
        }
        if not pending:
            raise AgentConfirmationError("没有待确认的操作")
        submitted = [decision.confirmation_id for decision in decisions]
        if len(set(submitted)) != len(submitted) or set(submitted) != set(pending):
            raise AgentConfirmationError("必须一次性处理当前全部待确认操作")
        resolutions: list[ToolResolution] = []
        for decision in decisions:
            record = pending[decision.confirmation_id]
            status = (
                ToolConfirmationStatus.CONFIRMED
                if decision.approved
                else ToolConfirmationStatus.REJECTED
            )
            if self.confirmations.consume(record.id, self.user_id, status) is None:
                raise AgentConfirmationError("该操作已被处理或已过期")
            logger.info(
                "Agent 待确认调用已处理：%s（编号 %s，%s）",
                record.tool_name,
                record.id,
                status.value,
            )
            resolutions.append(
                ToolResolution(
                    ToolCall(record.call_id, record.tool_name, dict(record.arguments)),
                    decision.approved,
                )
            )
        all_approved = all(item.approved for item in resolutions)
        message = "用户已确认执行该操作。" if all_approved else "用户已对该操作作出决定。"
        return AgentOrchestrator(
            self.db,
            self.user_id,
            conversation.session_id,
            conversation.history,
        ).stream(message, resolutions)
