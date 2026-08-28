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
from app.models.user import User, UserRole, UserStatus
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


class AccountDisabledError(ValueError):
    """账号已被管理员禁用。"""


class AdminAccessDeniedError(ValueError):
    """账号不具备管理员权限。"""


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
        return self._create_user(username, password, UserRole.USER)

    def create_admin(self, username: str, password: str) -> User:
        """通过受信任的本地脚本创建管理员账号。"""
        return self._create_user(username, password, UserRole.ADMIN)

    def login(self, username: str, password: str) -> AuthTokens:
        """验证用户名和密码并创建双 Token 会话。"""
        user = self._authenticate(username, password)
        return self._issue_tokens(user.id)

    def login_admin(self, username: str, password: str) -> AuthTokens:
        """仅允许管理员从独立入口登录。"""
        user = self._authenticate(username, password)
        if user.role != UserRole.ADMIN.value:
            raise AdminAccessDeniedError
        return self._issue_tokens(user.id)

    def _create_user(self, username: str, password: str, role: UserRole) -> User:
        """按指定角色创建用户并统一处理唯一约束竞争。"""
        if self.users.get_by_username(username) is not None:
            raise UsernameAlreadyExistsError
        try:
            with self.db.begin_nested():
                user = self.users.create(username, hash_password(password), role)
            return user
        except IntegrityError as error:
            raise UsernameAlreadyExistsError from error

    def _authenticate(self, username: str, password: str) -> User:
        """验证账号密码和实时账号状态。"""
        user = self.users.get_by_username(username)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        if not verify_password(password, password_hash) or user is None:
            raise InvalidCredentialsError
        if user.status != UserStatus.ACTIVE.value:
            raise AccountDisabledError
        return user

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
        user = self.users.get_by_id(payload.user_id)
        if user is None:
            raise InvalidRefreshTokenError
        if user.status != UserStatus.ACTIVE.value:
            self.refresh_sessions.revoke_active_for_user(payload.user_id, now)
            raise AccountDisabledError
        if token_session.revoked_at is not None:
            self.refresh_sessions.revoke_active_for_user(payload.user_id, now)
            raise InvalidRefreshTokenError
        if token_session.expires_at <= now:
            self.refresh_sessions.revoke(token_session, now)
            raise InvalidRefreshTokenError

        self.refresh_sessions.revoke(token_session, now)
        return self._issue_tokens(payload.user_id)

    def logout(self, refresh_token: str | None) -> None:
        """撤销当前 Refresh Token；缺少或无效 Token 时保持幂等。"""
        if refresh_token is None:
            return
        token_session = self.refresh_sessions.get_by_hash(hash_token(refresh_token))
        if token_session is not None and token_session.revoked_at is None:
            self.refresh_sessions.revoke(token_session, datetime.now(timezone.utc))

    def get_user_from_access_token(self, access_token: str) -> User:
        """通过 Access Token 获取当前用户。"""
        try:
            payload = decode_token(access_token, "access")
        except TokenValidationError as error:
            raise InvalidCredentialsError from error
        user = self.users.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError
        if user.status != UserStatus.ACTIVE.value:
            raise AccountDisabledError
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
