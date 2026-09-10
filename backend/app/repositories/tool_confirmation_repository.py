"""待确认工具调用的数据访问。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.tool_confirmation import ToolConfirmation, ToolConfirmationStatus


class ToolConfirmationRepository:
    """保存并原子消费高风险工具调用的待确认记录。"""

    def __init__(self, db: Session) -> None:
        """保存请求级数据库会话，后续读写都复用该会话。"""
        self.db = db

    def create(
        self,
        *,
        session_id: int,
        user_id: int,
        call_id: str,
        tool_name: str,
        operation: str,
        arguments: dict[str, Any],
        reason: str,
        ttl_seconds: int,
    ) -> ToolConfirmation:
        """登记一条待用户确认的调用。"""
        record = ToolConfirmation(
            session_id=session_id,
            user_id=user_id,
            call_id=call_id,
            tool_name=tool_name,
            operation=operation,
            arguments=dict(arguments),
            reason=reason,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list_pending(self, session_id: int, user_id: int) -> list[ToolConfirmation]:
        """读取该会话中未过期且尚未处理的待确认记录。"""
        statement = (
            select(ToolConfirmation)
            .where(
                ToolConfirmation.session_id == session_id,
                ToolConfirmation.user_id == user_id,
                ToolConfirmation.status == ToolConfirmationStatus.PENDING.value,
                ToolConfirmation.expires_at > func.now(),
            )
            .order_by(ToolConfirmation.id)
        )
        return list(self.db.scalars(statement))

    def consume(
        self, confirmation_id: int, user_id: int, status: ToolConfirmationStatus
    ) -> ToolConfirmation | None:
        """把记录原子地置为终态；已处理或已过期时返回 None（防重复确认）。"""
        statement = (
            update(ToolConfirmation)
            .where(
                ToolConfirmation.id == confirmation_id,
                ToolConfirmation.user_id == user_id,
                ToolConfirmation.status == ToolConfirmationStatus.PENDING.value,
                ToolConfirmation.expires_at > func.now(),
            )
            .values(status=status.value, decided_at=func.now())
            .returning(ToolConfirmation.id)
            .execution_options(synchronize_session=False)
        )
        updated_id = self.db.scalar(statement)
        if updated_id is None:
            return None
        return self.db.get(ToolConfirmation, updated_id)
