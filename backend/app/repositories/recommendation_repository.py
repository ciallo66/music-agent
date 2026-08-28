"""推荐所需的歌曲和用户行为查询。"""

from __future__ import annotations

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session, joinedload

from app.models.favorite import Favorite
from app.models.play_record import PlayRecord
from app.models.song import Song


class RecommendationRepository:
    """封装推荐候选歌曲和用户偏好查询。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_song(self, song_id: int) -> Song | None:
        """按主键查询歌曲，供播放记录业务校验使用。"""
        return self.db.get(Song, song_id)

    def record_play(self, user_id: int, song_id: int) -> None:
        """新增一条播放记录并刷新主键。"""
        self.db.add(PlayRecord(user_id=user_id, song_id=song_id))
        self.db.flush()

    def preferred_genres(self, user_id: int, limit: int = 3) -> list[str]:
        """按收藏和播放行为统计用户偏好风格。"""
        favorite_genres = (
            select(Song.genre.label("genre"), func.count().label("weight"))
            .join(Favorite, Favorite.song_id == Song.id)
            .where(Favorite.user_id == user_id, Song.genre.is_not(None))
            .group_by(Song.genre)
        )
        played_genres = (
            select(Song.genre.label("genre"), func.count().label("weight"))
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(PlayRecord.user_id == user_id, Song.genre.is_not(None))
            .group_by(Song.genre)
        )
        rows = self.db.execute(union_all(favorite_genres, played_genres)).all()
        totals: dict[str, int] = {}
        for genre, weight in rows:
            totals[genre] = totals.get(genre, 0) + int(weight)
        return [
            genre
            for genre, _ in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        ]

    def engaged_song_ids(self, user_id: int) -> set[int]:
        """返回用户已收藏或播放过的歌曲。"""
        favorite_ids = select(Favorite.song_id).where(Favorite.user_id == user_id)
        played_ids = select(PlayRecord.song_id).where(PlayRecord.user_id == user_id)
        return set(self.db.scalars(favorite_ids.union(played_ids)).all())

    def feature_profile(self, user_id: int) -> dict[str, float]:
        """计算用户已收藏或播放歌曲的平均音乐特征。"""
        engaged_ids = self.engaged_song_ids(user_id)
        if not engaged_ids:
            return {}
        fields = (Song.bpm, Song.energy, Song.valence, Song.danceability)
        values = self.db.execute(
            select(*(func.avg(field) for field in fields)).where(Song.id.in_(engaged_ids))
        ).one()
        names = ("bpm", "energy", "valence", "danceability")
        return {
            name: float(value)
            for name, value in zip(names, values, strict=False)
            if value is not None
        }

    def list_candidates(
        self,
        genres: list[str],
        excluded_ids: set[int],
        limit: int,
        profile: dict[str, float] | None = None,
    ) -> list[Song]:
        """按偏好风格和热度返回候选歌曲。"""
        conditions = [Song.genre.in_(genres)]
        if excluded_ids:
            conditions.append(Song.id.not_in(excluded_ids))
        score = Song.popularity.desc()
        if profile:
            distances = [func.abs(Song.bpm - profile["bpm"]) / 180] if "bpm" in profile else []
            distances.extend(
                func.abs(getattr(Song, key) - profile[key])
                for key in ("energy", "valence", "danceability")
                if key in profile
            )
            if distances:
                score = (Song.popularity - sum(distances) * 100).desc()
        statement = (
            select(Song)
            .options(joinedload(Song.artist))
            .where(*conditions)
            .order_by(score, Song.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def list_popular(self, excluded_ids: set[int], limit: int) -> list[Song]:
        """按热度返回冷启动候选歌曲。"""
        conditions = [Song.id.not_in(excluded_ids)] if excluded_ids else []
        statement = (
            select(Song)
            .options(joinedload(Song.artist))
            .where(*conditions)
            .order_by(Song.popularity.desc(), Song.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))
