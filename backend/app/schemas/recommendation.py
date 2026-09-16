"""推荐接口响应模型。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalog import SongSummary


class RecommendationItem(SongSummary):
    """带有真实推荐依据的歌曲。"""

    reason: str


class RecommendationPage(BaseModel):
    """当前用户推荐结果。"""

    items: list[RecommendationItem]
    strategy: str


class StructuredRecommendationItem(SongSummary):
    """结构化推荐条目：包含匹配分和推荐理由。"""

    reason: str
    match_score: Annotated[float, Field(ge=0.0, le=1.0)] | None


class StructuredRecommendationCard(BaseModel):
    """结构化推荐结果卡片。"""

    title: str
    items: list[StructuredRecommendationItem]
    reason: str = ""
    tags: list[str] = []
    scenario: str = ""
    feedback_actions: list[str] = ["like", "dislike", "seen"]

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "RecommendationItem",
    "RecommendationPage",
    "StructuredRecommendationItem",
    "StructuredRecommendationCard",
]
