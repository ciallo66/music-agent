"""推荐反馈所需的数据访问。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.recommendation_feedback import RecommendationFeedback


class FeedbackRepository:
    """封装推荐反馈的增删查。"""

    def __init__(self, db: Session) -> None:
        """绑定反馈使用的数据库会话。"""
        self.db = db

    def record(self, user_id: int, song_id: int, action: str) -> RecommendationFeedback:
        """记录或更新用户对推荐歌曲的反馈。"""
        existing = self.get(user_id, song_id)
        if existing:
            existing.action = action
            return existing
        feedback = RecommendationFeedback(user_id=user_id, song_id=song_id, action=action)
        self.db.add(feedback)
        self.db.flush()
        return feedback

    def get(self, user_id: int, song_id: int) -> RecommendationFeedback | None:
        """查询用户对某首歌的反馈。"""
        return self.db.get(RecommendationFeedback, (user_id, song_id))

    def remove(self, user_id: int, song_id: int) -> bool:
        """删除用户对某首歌的反馈。"""
        existing = self.get(user_id, song_id)
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.flush()
        return True

    def disliked_ids(self, user_id: int) -> set[int]:
        """返回用户标记不喜欢的歌曲 ID。"""
        statement = select(RecommendationFeedback.song_id).where(
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.action == "dislike",
        )
        return set(self.db.scalars(statement).all())

    def liked_ids(self, user_id: int) -> set[int]:
        """返回用户标记喜欢的歌曲 ID。"""
        statement = select(RecommendationFeedback.song_id).where(
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.action == "like",
        )
        return set(self.db.scalars(statement).all())

    def feedback_count(self, user_id: int) -> int:
        """统计用户反馈总数。"""
        statement = select(func.count(RecommendationFeedback.user_id)).where(
            RecommendationFeedback.user_id == user_id
        )
        return int(self.db.scalar(statement) or 0)

    def action_count(self, user_id: int, action: str) -> int:
        """统计用户某类反馈的数量。"""
        statement = select(func.count(RecommendationFeedback.user_id)).where(
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.action == action,
        )
        return int(self.db.scalar(statement) or 0)

    def valid_actions(self) -> list[str]:
        """返回有效的反馈类型。"""
        return ["like", "dislike", "seen", "similar", "less"]

    def has_feedback_on_recommendation(
        self, user_id: int, song_id: int
    ) -> RecommendationFeedback | None:
        """查询用户对推荐歌的反馈。"""
        return self.get(user_id, song_id)


__all__ = ["FeedbackRepository"]
