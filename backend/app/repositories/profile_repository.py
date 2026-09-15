"""用户音乐画像统计所需的数据访问。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import distinct, func, select, union_all
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

    def active_hours(self, user_id: int) -> list[tuple[int, float]]:
        """按小时统计用户播放分布，返回 (hour, weight)。"""
        hour_expr = func.extract("hour", PlayRecord.played_at).label("hour")
        statement = (
            select(hour_expr, func.count(PlayRecord.id).label("weight"))
            .where(PlayRecord.user_id == user_id)
            .group_by(hour_expr)
            .order_by(hour_expr)
        )
        rows = list(self.db.execute(statement))
        total = max(1, sum(int(weight) for _, weight in rows))
        return [(int(hour), round(int(weight) / total, 4)) for hour, weight in rows]

    def favorite_trend(self, user_id: int, days: int = 14) -> list[tuple[str, int]]:
        """按日期统计用户最近收藏趋势。"""
        day = func.date_trunc("day", Favorite.created_at).label("day")
        statement = (
            select(day, func.count(Favorite.id).label("count"))
            .where(Favorite.user_id == user_id)
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

    def interest_distribution(self, user_id: int, limit: int = 8) -> list[tuple[str, float]]:
        """根据播放和收藏行为统计兴趣主题分布（风格 + 乐器）。"""
        genre_stmt = (
            select(Song.genre.label("label"), func.count(PlayRecord.id).label("weight"))
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(PlayRecord.user_id == user_id, Song.genre.is_not(None))
            .group_by(Song.genre)
        )
        fav_genre_stmt = (
            select(Song.genre.label("label"), func.count(Favorite.id).label("weight"))
            .join(Favorite, Favorite.song_id == Song.id)
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(Favorite.user_id == user_id, Song.genre.is_not(None))
            .group_by(Song.genre)
        )
        rows = list(self.db.execute(union_all(genre_stmt, fav_genre_stmt)))
        totals: dict[str, int] = {}
        for label, weight in rows:
            key = str(label)
            totals[key] = totals.get(key, 0) + int(weight)
        sorted_items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        total = max(1, sum(weight for _, weight in sorted_items))
        return [(label, round(weight / total, 4)) for label, weight in sorted_items]

    def preference_change(self, user_id: int) -> list[tuple[str, str]]:
        """比较最近7天与更早期间的风格变化，返回 (direction, detail)。"""
        from datetime import date, timedelta

        today = date.today()
        recent_start = today - timedelta(days=7)
        recent_stmt = (
            select(Song.genre, func.count(PlayRecord.id).label("count"))
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(
                PlayRecord.user_id == user_id,
                Song.genre.is_not(None),
                PlayRecord.played_at >= recent_start,
            )
            .group_by(Song.genre)
            .order_by(func.count(PlayRecord.id).desc())
            .limit(5)
        )
        older_stmt = (
            select(Song.genre, func.count(PlayRecord.id).label("count"))
            .join(PlayRecord, PlayRecord.song_id == Song.id)
            .where(
                PlayRecord.user_id == user_id,
                Song.genre.is_not(None),
                PlayRecord.played_at < recent_start,
            )
            .group_by(Song.genre)
            .order_by(func.count(PlayRecord.id).desc())
            .limit(5)
        )
        recent = {name: count for name, count in self.db.execute(recent_stmt)}
        older = {name: count for name, count in self.db.execute(older_stmt)}
        changes: list[tuple[str, str]] = []
        for genre in recent:
            if genre not in older or recent[genre] > older.get(genre, 0):
                changes.append(("上升", f"最近7天{genre}收听次数增加"))
            else:
                changes.append(("下降", f"最近7天{genre}收听次数减少"))
        for genre in older:
            if genre not in recent and older[genre] > 3:
                changes.append(("衰减", f"较早期间常听{genre}，近期未再出现"))
        return changes[:5]


__all__ = ["ProfileRepository"]
