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

    def expire_outdated(self, session_id: int | None = None) -> int:
        """把已过期但仍为 pending 的记录置为 expired，返回处理条数。

        过期记录本来就会被 `list_pending` 过滤、不会被执行，这里做的是**状态收敛**：
        让"还在等用户确认"与"早就过期了"在数据上区分开，
        避免残留的 pending 在排查或会话恢复时被误读。
        """
        conditions = [
            ToolConfirmation.status == ToolConfirmationStatus.PENDING.value,
            ToolConfirmation.expires_at <= func.now(),
        ]
        if session_id is not None:
            conditions.append(ToolConfirmation.session_id == session_id)
        statement = (
            update(ToolConfirmation)
            .where(*conditions)
            .values(status=ToolConfirmationStatus.EXPIRED.value)
            .execution_options(synchronize_session=False)
        )
        result = self.db.execute(statement)
        self.db.flush()
        # CursorResult 才有 rowcount；类型标注里 Result 不声明该属性，这里做一次窄化。
        return int(getattr(result, "rowcount", 0) or 0)

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
