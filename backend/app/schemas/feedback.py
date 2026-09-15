"""推荐反馈接口模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalog import SongSummary


class RecommendationFeedbackCreate(BaseModel):
    """提交推荐反馈。"""

    song_id: Annotated[int, Field(gt=0)]
    action: Annotated[str, Field(min_length=1, max_length=50)]

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RecommendationFeedbackResponse(BaseModel):
    """推荐反馈记录。"""

    song_id: int
    action: str
    created_at: datetime


class FeedbackStats(BaseModel):
    """反馈汇总统计。"""

    total: int
    liked_count: int
    disliked_count: int
    seen_count: int


class RecommendationFeedbackWithSong(RecommendationFeedbackResponse):
    """包含歌曲信息的推荐反馈。"""

    song: SongSummary


class FeedbackActionItem(BaseModel):
    """可用反馈动作。"""

    action: str
    label: str
    description: str


__all__ = [
    "RecommendationFeedbackCreate",
    "RecommendationFeedbackResponse",
    "FeedbackStats",
    "RecommendationFeedbackWithSong",
    "FeedbackActionItem",
]
