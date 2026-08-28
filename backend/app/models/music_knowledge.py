"""音乐知识库切片模型。"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MusicKnowledge(Base):
    """用于音乐知识检索的文本切片及可选向量。"""

    __tablename__ = "music_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(512))
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
