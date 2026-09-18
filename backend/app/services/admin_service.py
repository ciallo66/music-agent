"""管理后台业务编排：概览统计与账号管理。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import (
    AdminCountItem,
    AdminOverview,
    AdminUserItem,
    AdminUserPage,
)


class AdminUserNotFoundError(LookupError):
    """目标账号不存在。"""


class AdminValidationError(ValueError):
    """传入的角色或状态不合法。"""


class AdminService:
    """后台管理用例。"""

    def __init__(self, db: Session) -> None:
        """绑定仓储。"""
        self.repository = AdminRepository(db)
        self.db = db

    def overview(self) -> AdminOverview:
        """汇总后台首页计数与流派分布。"""
        counts = self.repository.overview_counts()
        distribution = [
            AdminCountItem(label=genre, count=count)
            for genre, count in self.repository.genre_distribution()
        ]
        return AdminOverview(
            songs=counts["songs"],
            artists=counts["artists"],
            users=counts["users"],
            admins=counts["admins"],
            playlists=counts["playlists"],
            feedback=counts["feedback"],
            favorites=counts["favorites"],
            plays=counts["plays"],
            knowledge=counts["knowledge"],
            import_jobs=counts["import_jobs"],
            songs_with_embedding=counts["songs_with_embedding"],
            songs_with_audio_features=counts["songs_with_audio_features"],
            genre_distribution=distribution,
        )

    def list_users(self, *, keyword: str = "", page: int = 1, page_size: int = 20) -> AdminUserPage:
        """分页列出账号，并附带各自的互动计数。"""
        users, total = self.repository.list_users(
            keyword=keyword.strip(), page=page, page_size=page_size
        )
        counters = self.repository.counts_for_users([user.id for user in users])
        items = [
            AdminUserItem(
                id=user.id,
                username=user.username,
                role=user.role,
                status=user.status,
                created_at=user.created_at,
                favorites=counters[user.id]["favorites"],
                playlists=counters[user.id]["playlists"],
                feedback=counters[user.id]["feedback"],
            )
            for user in users
        ]
        return AdminUserPage(items=items, total=total, page=page, page_size=page_size)

    def update_user(self, user_id: int, *, role: str | None, status: str | None) -> User:
        """修改账号角色或状态；不允许把最后一个管理员降级。"""
        user = self.repository.get_user(user_id)
        if user is None:
            raise AdminUserNotFoundError(user_id)

        if role is not None:
            if role not in {item.value for item in UserRole}:
                raise AdminValidationError(f"不支持的角色：{role}")
            if user.role == UserRole.ADMIN.value and role != UserRole.ADMIN.value:
                remaining = self.repository.admin_count()
                if remaining <= 1:
                    raise AdminValidationError("至少保留一个管理员，不能降级最后一个管理员")
            user.role = role

        if status is not None:
            if status not in {item.value for item in UserStatus}:
                raise AdminValidationError(f"不支持的状态：{status}")
            user.status = status

        self.db.flush()
        return user
