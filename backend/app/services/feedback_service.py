"""推荐反馈业务逻辑。"""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy.orm import Session

from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import (
    FeedbackActionItem,
    FeedbackStats,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
)


class FeedbackNotFoundError(Exception):
    """用户没有对该歌曲的反馈记录。"""


class InvalidFeedbackActionError(ValueError):
    """提交的反馈类型不被支持。"""


class FeedbackService:
    """编排推荐反馈的记录、删除和查询。"""

    ACTIONS: ClassVar[list[tuple[str, str, str]]] = [
        ("like", "喜欢", "这首歌符合你的口味"),
        ("dislike", "不喜欢", "这首歌不符合你的口味"),
        ("seen", "已看过", "你已知道这首歌，建议换一批"),
        ("similar", "类似更多", "希望看到更多相替内容"),
        ("less", "少点此类", "减少此类型风格的推荐"),
    ]

    def __init__(self, db: Session) -> None:
        """绑定反馈仓储，负责校验和业务编排。"""
        self.repository = FeedbackRepository(db)

    def list_actions(self) -> list[FeedbackActionItem]:
        """返回所有可用反馈类型。"""
        return [
            FeedbackActionItem(action=action, label=label, description=description)
            for action, label, description in self.ACTIONS
        ]

    def record_feedback(
        self, user_id: int, payload: RecommendationFeedbackCreate
    ) -> RecommendationFeedbackResponse:
        """记录或更新用户反馈。"""
        valid_actions = {action for action, _, _ in self.ACTIONS}
        if payload.action not in valid_actions:
            raise InvalidFeedbackActionError(f"不支持的反馈类型：{payload.action}")
        feedback = self.repository.record(user_id, payload.song_id, payload.action)
        return RecommendationFeedbackResponse.model_validate(feedback, from_attributes=True)

    def remove_feedback(self, user_id: int, song_id: int) -> None:
        """删除用户反馈。"""
        if not self.repository.remove(user_id, song_id):
            raise FeedbackNotFoundError

    def get_stats(self, user_id: int) -> FeedbackStats:
        """返回当前用户的反馈汇总。"""
        return FeedbackStats(
            total=self.repository.feedback_count(user_id),
            liked_count=self.repository.action_count(user_id, "like"),
            disliked_count=self.repository.action_count(user_id, "dislike"),
            seen_count=self.repository.action_count(user_id, "seen"),
        )


__all__ = ["FeedbackService", "FeedbackNotFoundError", "InvalidFeedbackActionError"]
