"""歌曲标签表模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.associations import SongTag


class Tag(Base):
    """用于分类和推荐的歌曲标签。"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    song_links: Mapped[list[SongTag]] = relationship(back_populates="tag")
