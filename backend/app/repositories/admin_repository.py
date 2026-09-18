"""管理后台的数据访问：库表计数与账号分页。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.artist import Artist
from app.models.chat import ChatSession
from app.models.favorite import Favorite
from app.models.import_job import ImportJob
from app.models.music_knowledge import MusicKnowledge
from app.models.play_record import PlayRecord
from app.models.playlist import Playlist
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.song import Song
from app.models.user import User, UserRole


class AdminRepository:
    """管理后台只读统计与账号查询。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话。"""
        self.db = db

    def _count(self, model: type[object], *conditions: object) -> int:
        """统计一张表的行数，可附带过滤条件。"""
        statement = select(func.count()).select_from(model)  # type: ignore[arg-type]
        if conditions:
            statement = statement.where(*conditions)  # type: ignore[arg-type]
        return int(self.db.scalar(statement) or 0)

    def overview_counts(self) -> dict[str, int]:
        """返回后台首页需要的核心计数。"""
        return {
            "songs": self._count(Song),
            "artists": self._count(Artist),
            "users": self._count(User),
            "admins": self._count(User, User.role == UserRole.ADMIN),
            "playlists": self._count(Playlist),
            "feedback": self._count(RecommendationFeedback),
            "favorites": self._count(Favorite),
            "plays": self._count(PlayRecord),
            "knowledge": self._count(MusicKnowledge),
            "import_jobs": self._count(ImportJob),
            "chat_sessions": self._count(ChatSession),
            "songs_with_embedding": self._count(Song, Song.embedding.is_not(None)),
            "songs_with_audio_features": self._count(Song, Song.bpm.is_not(None)),
        }

    def genre_distribution(self, limit: int = 8) -> list[tuple[str, int]]:
        """按流派分组计数，用于后台看分布是否失衡。"""
        rows = self.db.execute(
            select(Song.genre, func.count())
            .where(Song.genre.is_not(None))
            .group_by(Song.genre)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [(str(genre), int(count)) for genre, count in rows]

    def list_users(self, *, keyword: str, page: int, page_size: int) -> tuple[list[User], int]:
        """按关键字分页查询账号。"""
        statement = select(User)
        if keyword:
            statement = statement.where(or_(User.username.ilike(f"%{keyword}%")))
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        rows = self.db.scalars(
            statement.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(rows), total

    def get_user(self, user_id: int) -> User | None:
        """按主键读取账号。"""
        return self.db.get(User, user_id)

    def admin_count(self) -> int:
        """管理员数量，用于校验不能降级最后一个管理员。"""
        return self._count(User, User.role == UserRole.ADMIN.value)

    def counts_for_users(self, user_ids: list[int]) -> dict[int, dict[str, int]]:
        """批量取每个账号的收藏/歌单/反馈数量，避免逐行查询。"""
        result: dict[int, dict[str, int]] = {
            user_id: {"favorites": 0, "playlists": 0, "feedback": 0} for user_id in user_ids
        }
        if not user_ids:
            return result
        if user_ids:
            fav_rows = self.db.execute(
                select(Favorite.user_id, func.count())
                .where(Favorite.user_id.in_(user_ids))
                .group_by(Favorite.user_id)
            ).all()
            for user_id, count in fav_rows:
                result[int(user_id)]["favorites"] = int(count)

            playlist_rows = self.db.execute(
                select(Playlist.user_id, func.count())
                .where(Playlist.user_id.in_(user_ids))
                .group_by(Playlist.user_id)
            ).all()
            for user_id, count in playlist_rows:
                result[int(user_id)]["playlists"] = int(count)

            feedback_rows = self.db.execute(
                select(RecommendationFeedback.user_id, func.count())
                .where(RecommendationFeedback.user_id.in_(user_ids))
                .group_by(RecommendationFeedback.user_id)
            ).all()
            for user_id, count in feedback_rows:
                result[int(user_id)]["feedback"] = int(count)
        return result
