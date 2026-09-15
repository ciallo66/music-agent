"""内容推荐和热门兜底业务。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.catalog import SongSummary
from app.schemas.recommendation import (
    RecommendationItem,
    RecommendationPage,
    StructuredRecommendationCard,
    StructuredRecommendationItem,
)


class SongNotFoundError(Exception):
    """播放记录对应的歌曲不存在。"""


class RecommendationService:
    """根据真实用户行为生成可解释推荐。"""

    def __init__(self, db: Session) -> None:
        """绑定推荐仓储，保证推荐逻辑不直接操作数据库查询。"""
        self.repository = RecommendationRepository(db)
        self.feedback = FeedbackRepository(db)

    def record_play(self, user_id: int, song_id: int) -> None:
        """校验歌曲存在后记录播放行为。"""
        if self.repository.get_song(song_id) is None:
            raise SongNotFoundError
        self.repository.record_play(user_id, song_id)

    def get_feedback_actions(self) -> list[dict[str, str]]:
        """返回可用反馈动作列表。"""
        return [
            {"action": "like", "label": "喜欢", "description": "这首歌符合你的口味"},
            {"action": "dislike", "label": "不喜欢", "description": "这首歌不符合你的口味"},
            {"action": "seen", "label": "已看过", "description": "你已知道这首歌，建议换一批"},
            {"action": "similar", "label": "类似更多", "description": "希望看到更多相似内容"},
            {"action": "less", "label": "少点此类", "description": "减少此类型风格的推荐"},
        ]

    def record_feedback(self, user_id: int, song_id: int, action: str) -> None:
        """记录用户反馈；不喜欢将从后续推荐中排除。"""
        if self.repository.get_song(song_id) is None:
            raise SongNotFoundError
        valid_actions = {
            *self.feedback.valid_actions(),
            "like",
            "dislike",
            "seen",
            "similar",
            "less",
        }
        if action not in valid_actions:
            raise ValueError(f"不支持的反馈类型：{action}")
        self.feedback.record(user_id, song_id, action)

    def recommend(self, user_id: int | None, limit: int = 20) -> RecommendationPage:
        """登录用户按偏好推荐，游客直接使用热门歌曲兜底。"""
        if user_id is None:
            popular = self.repository.list_popular(set(), limit)
            return RecommendationPage(
                items=[self._item(song, "按平台热度推荐") for song in popular],
                strategy="popular_fallback",
            )
        disliked_ids = self.feedback.disliked_ids(user_id)
        excluded_ids = self.repository.engaged_song_ids(user_id) | disliked_ids
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

    def recommend_cards(
        self, user_id: int | None, limit: int = 20
    ) -> list[StructuredRecommendationCard]:
        """生成结构化推荐结果卡片。"""
        if user_id is None:
            popular = self.repository.list_popular(set(), limit)
            return [
                self._build_card(
                    title="热门推荐",
                    songs=popular,
                    reason="平台热门歌曲，适合初次探索",
                    tags=["热门", "热门"],
                    scenario="放松",
                )
            ]
        disliked_ids = self.feedback.disliked_ids(user_id)
        excluded_ids = self.repository.engaged_song_ids(user_id) | disliked_ids
        genres = self.repository.preferred_genres(user_id)
        profile = self.repository.feature_profile(user_id)
        candidates = self.repository.list_candidates(genres, excluded_ids, limit, profile)
        if candidates:
            return [
                self._build_card(
                    title="按你的口味",
                    songs=candidates,
                    reason="基于你的常听风格与音乐特征偏好",
                    tags=genres or ["个性化"],
                    scenario="放松",
                    profile=profile,
                )
            ]
        popular = self.repository.list_popular(excluded_ids, limit)
        return [
            self._build_card(
                title="热门推荐",
                songs=popular,
                reason="暂时没有足够偏好数据，使用平台热门兜底",
                tags=["热门"],
                scenario="放松",
                profile=profile,
            )
        ]

    def _build_card(
        self,
        title: str,
        songs: Sequence[object],
        reason: str,
        tags: list[str],
        scenario: str,
        profile: dict[str, float] | None = None,
    ) -> StructuredRecommendationCard:
        """把歌曲列表拼成结构化推荐卡片。"""
        items: list[StructuredRecommendationItem] = []
        for song in songs:
            summary = SongSummary.model_validate(song, from_attributes=True)
            match_score = self._match_score(song, profile)
            items.append(
                StructuredRecommendationItem(
                    **summary.model_dump(),
                    reason=self._content_reason(song, profile),
                    match_score=match_score,
                )
            )
        return StructuredRecommendationCard(
            title=title,
            items=items,
            reason=reason,
            tags=tags,
            scenario=scenario,
        )

    @staticmethod
    def _match_score(song: object, profile: dict[str, float] | None) -> float:
        """根据音乐特征与用户偏好的距离计算匹配分。"""
        if not profile:
            return 0.7
        score = 0.0
        total = 0.0
        for field in ("energy", "valence", "danceability", "bpm"):
            value = getattr(song, field, None)
            target = profile.get(field)
            if value is None or target is None:
                continue
            score += 1 - abs(value - target)
            total += 1
        if total == 0:
            return 0.7
        return max(0.0, min(1.0, score / total))

    @staticmethod
    def _item(song: object, reason: str) -> RecommendationItem:
        """将歌曲 ORM 对象转换为带理由的推荐项。"""
        song_summary = SongSummary.model_validate(song, from_attributes=True)
        return RecommendationItem(**song_summary.model_dump(), reason=reason)

    @staticmethod
    def _content_reason(song: object, profile: dict[str, float] | None) -> str:
        """生成基于风格和特征的可解释推荐理由。"""
        genre = getattr(song, "genre", None) or "未知"
        if profile and getattr(song, "energy", None) is not None:
            return f"符合你常听的{genre}风格，音乐特征接近你的偏好"
        return f"符合你常听的{genre}风格"
