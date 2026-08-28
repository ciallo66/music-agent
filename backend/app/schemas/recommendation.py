"""推荐接口响应模型。"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.catalog import SongSummary


class RecommendationItem(SongSummary):
    """带有真实推荐依据的歌曲。"""

    reason: str


class RecommendationPage(BaseModel):
    """当前用户推荐结果。"""

    items: list[RecommendationItem]
    strategy: str
