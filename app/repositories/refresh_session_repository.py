"""Refresh Token 会话数据访问。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_session import RefreshSession


class RefreshSessionRepository:
    """封装 Refresh Token 会话的查询和状态变更。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话。"""
        self.db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshSession:
        """保存新 Refresh Token 的摘要。"""
        session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_hash(self, token_hash: str) -> RefreshSession | None:
        """按 Token 摘要查询会话。"""
        statement = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        return self.db.scalar(statement)

    def revoke(self, session: RefreshSession, revoked_at: datetime) -> None:
        """撤销指定 Refresh Token 会话。"""
        session.revoked_at = revoked_at
        self.db.flush()

    def revoke_active_for_user(self, user_id: int, revoked_at: datetime) -> None:
        """撤销用户的全部有效 Refresh Token 会话。"""
        statement = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        self.db.execute(statement)
