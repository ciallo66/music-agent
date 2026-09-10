"""Agent 高风险工具调用的待确认记录。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ToolConfirmationStatus(str, Enum):
    """待确认记录的状态。"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ToolConfirmation(Base):
    """服务端保存的高风险调用：参数以服务端记录为准，只能确认一次。"""

    __tablename__ = "tool_confirmations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected')",
            name="ck_tool_confirmations_status",
        ),
        Index("ix_tool_confirmations_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    call_id: Mapped[str] = mapped_column(String(64))
    tool_name: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(20))
    arguments: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, server_default="{}")
    reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(20),
        default=ToolConfirmationStatus.PENDING.value,
        server_default=ToolConfirmationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
