"""用户表模型。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.play_record import PlayRecord
    from app.models.playlist import Playlist
    from app.models.refresh_session import RefreshSession


class User(Base):
    """平台用户账号。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    playlists: Mapped[list[Playlist]] = relationship(back_populates="user")
    play_records: Mapped[list[PlayRecord]] = relationship(back_populates="user")
    refresh_sessions: Mapped[list[RefreshSession]] = relationship(back_populates="user")
