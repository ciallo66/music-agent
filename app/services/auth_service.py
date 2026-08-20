"""用户注册、登录和双 Token 轮换业务逻辑。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_session_repository import RefreshSessionRepository
from app.repositories.user_repository import UserRepository

DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Ik7gAKOy4uUCJED3Z2er6A$"
    "PLMRLgcu+nLr2wZHGltYg4RvlxCRgiUO3LBERutmd9k"
)


class UsernameAlreadyExistsError(ValueError):
    """注册用户名已被占用。"""


class InvalidCredentialsError(ValueError):
    """用户名或密码不正确。"""


class InvalidRefreshTokenError(ValueError):
    """Refresh Token 无效、过期或已撤销。"""


class UserNotFoundError(ValueError):
    """Token 对应的用户不存在。"""


@dataclass(frozen=True)
class AuthTokens:
    """登录或刷新后返回的双 Token。"""

    access_token: str
    refresh_token: str


class AuthService:
    """协调用户仓储、密码哈希和 Token 会话。"""

    def __init__(self, db: Session) -> None:
        """绑定数据库会话和认证仓储。"""
        self.db = db
        self.users = UserRepository(db)
        self.refresh_sessions = RefreshSessionRepository(db)

    def register(self, username: str, password: str) -> User:
        """注册新用户并只持久化密码哈希。"""
        if self.users.get_by_username(username) is not None:
            raise UsernameAlreadyExistsError
        try:
            user = self.users.create(username, hash_password(password))
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as error:
            self.db.rollback()
            raise UsernameAlreadyExistsError from error

    def login(self, username: str, password: str) -> AuthTokens:
        """验证用户名和密码并创建双 Token 会话。"""
        user = self.users.get_by_username(username)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        if not verify_password(password, password_hash) or user is None:
            raise InvalidCredentialsError
        tokens = self._issue_tokens(user.id)
        self.db.commit()
        return tokens

    def refresh(self, refresh_token: str) -> AuthTokens:
        """校验并轮换 Refresh Token，同时签发新 Access Token。"""
        try:
            payload = decode_token(refresh_token, "refresh")
        except TokenValidationError as error:
            raise InvalidRefreshTokenError from error

        token_session = self.refresh_sessions.get_by_hash(hash_token(refresh_token))
        now = datetime.now(timezone.utc)
        if token_session is None or token_session.user_id != payload.user_id:
            raise InvalidRefreshTokenError
        if token_session.revoked_at is not None:
            self.refresh_sessions.revoke_active_for_user(payload.user_id, now)
            self.db.commit()
            raise InvalidRefreshTokenError
        if token_session.expires_at <= now:
            self.refresh_sessions.revoke(token_session, now)
            self.db.commit()
            raise InvalidRefreshTokenError

        self.refresh_sessions.revoke(token_session, now)
        tokens = self._issue_tokens(payload.user_id)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str | None) -> None:
        """撤销当前 Refresh Token；缺少或无效 Token 时保持幂等。"""
        if refresh_token is None:
            return
        token_session = self.refresh_sessions.get_by_hash(hash_token(refresh_token))
        if token_session is not None and token_session.revoked_at is None:
            self.refresh_sessions.revoke(token_session, datetime.now(timezone.utc))
            self.db.commit()

    def get_user_from_access_token(self, access_token: str) -> User:
        """通过 Access Token 获取当前用户。"""
        try:
            payload = decode_token(access_token, "access")
        except TokenValidationError as error:
            raise InvalidCredentialsError from error
        user = self.users.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError
        return user

    def _issue_tokens(self, user_id: int) -> AuthTokens:
        """签发双 Token 并保存 Refresh Token 摘要。"""
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        self.refresh_sessions.create(
            user_id,
            hash_token(refresh_token.value),
            refresh_token.expires_at,
        )
        return AuthTokens(
            access_token=access_token.value,
            refresh_token=refresh_token.value,
        )
