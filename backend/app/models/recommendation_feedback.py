"""推荐反馈记录模型。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.user import User


class RecommendationFeedback(Base):
    """用户对推荐歌曲的反馈行为（喜欢、不喜欢、已看过等）。"""

    __tablename__ = "recommendation_feedback"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), primary_key=True)
    action: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="recommendation_feedback")
    song: Mapped[Song] = relationship(back_populates="recommendation_feedback")
