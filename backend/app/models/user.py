"""用户表模型。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.play_record import PlayRecord
    from app.models.playlist import Playlist
    from app.models.recommendation_feedback import RecommendationFeedback
    from app.models.refresh_session import RefreshSession


class UserRole(str, Enum):
    """用户权限角色。"""

    USER = "user"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """用户账号状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"


class User(Base):
    """平台用户账号。"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER.value, server_default=UserRole.USER.value
    )
    status: Mapped[str] = mapped_column(
        String(20), default=UserStatus.ACTIVE.value, server_default=UserStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    playlists: Mapped[list[Playlist]] = relationship(back_populates="user")
    play_records: Mapped[list[PlayRecord]] = relationship(back_populates="user")
    refresh_sessions: Mapped[list[RefreshSession]] = relationship(back_populates="user")
    recommendation_feedback: Mapped[list[RecommendationFeedback]] = relationship(
        back_populates="user"
    )
