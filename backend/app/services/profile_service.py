"""用户音乐画像与听歌统计业务编排。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.catalog import SongSummary
from app.schemas.profile import (
    MusicDistributionItem,
    MusicFeatureProfile,
    MusicProfileResponse,
    PlayTrendItem,
    RecentPlayItem,
)


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
        )
