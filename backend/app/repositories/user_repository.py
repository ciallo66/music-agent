"""用户数据访问。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    """封装用户表查询和写入。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话。"""
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """按主键查询用户。"""
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        """按区分大小写的用户名精确查询用户。"""
        statement = select(User).where(User.username == username)
        return self.db.scalar(statement)

    def create(
        self,
        username: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """创建用户并刷新数据库生成字段。"""
        user = User(username=username, password_hash=password_hash, role=role.value)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
