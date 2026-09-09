"""内容推荐和热门兜底业务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.catalog import SongSummary
from app.schemas.recommendation import RecommendationItem, RecommendationPage


class SongNotFoundError(Exception):
    """播放记录对应的歌曲不存在。"""


class RecommendationService:
    """根据真实用户行为生成可解释推荐。"""

    def __init__(self, db: Session) -> None:
        """绑定推荐仓储，保证推荐逻辑不直接操作数据库查询。"""
        self.repository = RecommendationRepository(db)

    def record_play(self, user_id: int, song_id: int) -> None:
        """校验歌曲存在后记录播放行为。"""
        if self.repository.get_song(song_id) is None:
            raise SongNotFoundError
        self.repository.record_play(user_id, song_id)

    def recommend(self, user_id: int | None, limit: int = 20) -> RecommendationPage:
        """登录用户按偏好推荐，游客直接使用热门歌曲兜底。"""
        if user_id is None:
            popular = self.repository.list_popular(set(), limit)
            return RecommendationPage(
                items=[self._item(song, "按平台热度推荐") for song in popular],
                strategy="popular_fallback",
            )
        excluded_ids = self.repository.engaged_song_ids(user_id)
        genres = self.repository.preferred_genres(user_id)
        profile = self.repository.feature_profile(user_id)
        candidates = self.repository.list_candidates(genres, excluded_ids, limit, profile)
        if candidates:
            return RecommendationPage(
                items=[
                    self._item(song, self._content_reason(song, profile)) for song in candidates
                ],
                strategy="content",
            )
        popular = self.repository.list_popular(excluded_ids, limit)
        return RecommendationPage(
            items=[self._item(song, "按平台热度推荐") for song in popular],
            strategy="popular_fallback",
        )

    @staticmethod
    def _item(song: object, reason: str) -> RecommendationItem:
        """将歌曲 ORM 对象转换为带理由的推荐项。"""
        song_summary = SongSummary.model_validate(song, from_attributes=True)
        return RecommendationItem(**song_summary.model_dump(), reason=reason)

    @staticmethod
    def _content_reason(song: object, profile: dict[str, float]) -> str:
        """生成基于风格和特征的可解释推荐理由。"""
        genre = getattr(song, "genre", None) or "未知"
        if profile and getattr(song, "energy", None) is not None:
            return f"符合你常听的{genre}风格，音乐特征接近你的偏好"
        return f"符合你常听的{genre}风格"
