"""用户音乐画像统计所需的数据访问。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.artist import Artist
from app.models.favorite import Favorite
from app.models.play_record import PlayRecord
from app.models.song import Song


class ProfileRepository:
    """封装当前用户的播放、收藏和歌曲聚合查询。"""

    def __init__(self, db: Session) -> None:
        """绑定画像统计使用的数据库会话。"""
        self.db = db

    def total_plays(self, user_id: int) -> int:
        """统计用户播放记录总数。"""
        statement = select(func.count(PlayRecord.id)).where(PlayRecord.user_id == user_id)
        return int(self.db.scalar(statement) or 0)

    def unique_songs(self, user_id: int) -> int:
        """统计用户播放过的不同歌曲数。"""
        statement = select(func.count(distinct(PlayRecord.song_id))).where(
            PlayRecord.user_id == user_id
        )
        return int(self.db.scalar(statement) or 0)

    def favorite_count(self, user_id: int) -> int:
        """统计用户收藏数量。"""
        statement = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        return int(self.db.scalar(statement) or 0)

    def genre_distribution(self, user_id: int, limit: int) -> list[tuple[str, int]]:
        """按播放次数统计用户听过的歌曲风格。"""
        statement = (
            select(Song.genre, func.count(PlayRecord.id).label("count"))
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(PlayRecord.user_id == user_id, Song.genre.is_not(None))
            .group_by(Song.genre)
            .order_by(func.count(PlayRecord.id).desc(), Song.genre.asc())
            .limit(limit)
        )
        return [(str(name), int(count)) for name, count in self.db.execute(statement)]

    def top_artists(self, user_id: int, limit: int) -> list[tuple[str, int]]:
        """按播放次数统计用户听过最多的歌手。"""
        statement = (
            select(Artist.name, func.count(PlayRecord.id).label("count"))
            .join(Song, Song.artist_id == Artist.id)
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(PlayRecord.user_id == user_id)
            .group_by(Artist.id, Artist.name)
            .order_by(func.count(PlayRecord.id).desc(), Artist.name.asc())
            .limit(limit)
        )
        return [(str(name), int(count)) for name, count in self.db.execute(statement)]

    def play_trend(self, user_id: int, days: int) -> list[tuple[str, int]]:
        """返回最近若干天的每日播放次数。"""
        day = func.date_trunc("day", PlayRecord.played_at).label("day")
        statement = (
            select(day, func.count(PlayRecord.id).label("count"))
            .where(PlayRecord.user_id == user_id)
            .group_by(day)
            .order_by(day.desc())
            .limit(days)
        )
        rows = list(self.db.execute(statement))
        result: list[tuple[str, int]] = []
        for day_value, count in reversed(rows):
            if isinstance(day_value, datetime):
                date_value = day_value.date().isoformat()
            else:
                date_value = str(day_value)
            result.append((date_value, int(count)))
        return result

    def recent_plays(self, user_id: int, limit: int) -> list[PlayRecord]:
        """按时间倒序读取最近播放记录及歌曲歌手。"""
        statement = (
            select(PlayRecord)
            .options(joinedload(PlayRecord.song).joinedload(Song.artist))
            .where(PlayRecord.user_id == user_id)
            .order_by(PlayRecord.played_at.desc(), PlayRecord.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))


__all__ = ["ProfileRepository"]
