"""用户音乐画像与听歌统计响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.catalog import SongSummary


class MusicFeatureProfile(BaseModel):
    """用户已参与歌曲的平均音乐特征。"""

    average_bpm: float | None
    average_energy: float | None
    average_valence: float | None
    average_danceability: float | None


class MusicDistributionItem(BaseModel):
    """风格或歌手的统计项。"""

    name: str
    count: int


class PlayTrendItem(BaseModel):
    """按日期聚合的播放次数。"""

    date: str
    count: int


class RecentPlayItem(BaseModel):
    """最近播放记录及其歌曲信息。"""

    played_at: datetime
    song: SongSummary


class PreferenceChangeItem(BaseModel):
    """偏好变化项。"""

    direction: str
    detail: str


class ActiveHourItem(BaseModel):
    """活跃小时统计。"""

    hour: int
    label: str
    weight: float


class InterestDistributionItem(BaseModel):
    """兴趣主题分布。"""

    label: str
    weight: float


class MusicProfileResponse(BaseModel):
    """当前用户的音乐画像和听歌统计。"""

    total_plays: int
    unique_songs: int
    favorite_count: int
    preferred_genres: list[str]
    feature_profile: MusicFeatureProfile
    genre_distribution: list[MusicDistributionItem]
    top_artists: list[MusicDistributionItem]
    play_trend: list[PlayTrendItem]
    recent_plays: list[RecentPlayItem]
    preference_change: list[PreferenceChangeItem] | None = None
    active_hours: list[ActiveHourItem] | None = None
    favorite_trend: list[PlayTrendItem] | None = None
    agent_interpretation: str | None = None
    interest_distribution: list[InterestDistributionItem] | None = None
