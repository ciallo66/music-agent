"""用户音乐画像与听歌统计业务编排。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.catalog import SongSummary
from app.schemas.profile import (
    ActiveHourItem,
    InterestDistributionItem,
    MusicDistributionItem,
    MusicFeatureProfile,
    MusicProfileResponse,
    PlayTrendItem,
    PreferenceChangeItem,
    RecentPlayItem,
)

logger = logging.getLogger(__name__)


class ProfileService:
    """编排当前用户的音乐画像统计。"""

    def __init__(self, db: Session) -> None:
        """绑定画像和推荐仓储，供统计用例组合读取。"""
        self.repository = ProfileRepository(db)
        self.recommendations = RecommendationRepository(db)

    def get_music_profile(self, user_id: int) -> MusicProfileResponse:
        """返回用户画像、分布统计、趋势和最近播放。"""
        feature_values = self.recommendations.feature_profile(user_id)
        feature_profile = MusicFeatureProfile(
            average_bpm=feature_values.get("bpm"),
            average_energy=feature_values.get("energy"),
            average_valence=feature_values.get("valence"),
            average_danceability=feature_values.get("danceability"),
        )
        return MusicProfileResponse(
            total_plays=self.repository.total_plays(user_id),
            unique_songs=self.repository.unique_songs(user_id),
            favorite_count=self.repository.favorite_count(user_id),
            preferred_genres=self.recommendations.preferred_genres(user_id, limit=5),
            feature_profile=feature_profile,
            genre_distribution=[
                MusicDistributionItem(name=name, count=count)
                for name, count in self.repository.genre_distribution(user_id, limit=8)
            ],
            top_artists=[
                MusicDistributionItem(name=name, count=count)
                for name, count in self.repository.top_artists(user_id, limit=8)
            ],
            play_trend=[
                PlayTrendItem(date=date, count=count)
                for date, count in self.repository.play_trend(user_id, days=30)
            ],
            recent_plays=[
                RecentPlayItem(
                    played_at=record.played_at,
                    song=SongSummary.model_validate(record.song),
                )
                for record in self.repository.recent_plays(user_id, limit=10)
            ],
            preference_change=[
                PreferenceChangeItem(direction=direction, detail=detail)
                for direction, detail in self.repository.preference_change(user_id)
            ],
            active_hours=[
                ActiveHourItem(hour=hour, label=f"{hour:02d}:00", weight=weight)
                for hour, weight in self.repository.active_hours(user_id)
            ],
            favorite_trend=[
                PlayTrendItem(date=date, count=count)
                for date, count in self.repository.favorite_trend(user_id, days=14)
            ],
            interest_distribution=[
                InterestDistributionItem(label=label, weight=weight)
                for label, weight in self.repository.interest_distribution(user_id, limit=8)
            ],
            agent_interpretation=self._generate_interpretation(user_id, feature_profile),
        )

    def _generate_interpretation(
        self, user_id: int, feature_profile: MusicFeatureProfile
    ) -> str | None:
        """使用 DeepSeek 解释用户的画像。"""
        from app.services.agent.provider import DeepSeekProvider, LLMProviderError

        genres = self.recommendations.preferred_genres(user_id, limit=5)
        if not genres:
            return None
        genre_distribution = self.repository.genre_distribution(user_id, limit=5)
        total_plays = self.repository.total_plays(user_id)
        prompt = (
            f"你是一个音乐分析助手。根据以下用户画像，用中文用一段话(50-80字)总结"
            f"用户的音乐偏好和特点，突出一个关键变化趋势。\n"
            f"偏好风格: {', '.join(genres)}\n"
            f"风格分布: {genre_distribution}\n"
            f"累计互动: {total_plays} 次\n"
            f"平均特征: BPM={feature_profile.average_bpm}, "
            f"Energy={feature_profile.average_energy}, "
            f"Valence={feature_profile.average_valence}, "
            f"Danceability={feature_profile.average_danceability}"
        )
        try:
            response = DeepSeekProvider().complete(
                messages=[{"role": "user", "content": prompt}],
                tools=[],
            )
            return response.content
        except LLMProviderError as error:
            logger.warning("生成用户画像解读失败：%s", error)
            return None
