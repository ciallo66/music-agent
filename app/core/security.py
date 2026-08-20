"""密码哈希和 JWT 签发、校验工具。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


class TokenValidationError(ValueError):
    """Token 无效、过期或类型不匹配。"""


@dataclass(frozen=True)
class TokenPayload:
    """经过签名和声明校验的 Token 数据。"""

    user_id: int
    token_type: str
    token_id: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedToken:
    """新签发的 Token 及其过期时间。"""

    value: str
    expires_at: datetime


def hash_password(password: str) -> str:
    """使用当前推荐的 Argon2 参数生成密码哈希。"""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码是否匹配数据库中的哈希。"""
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> IssuedToken:
    """为用户签发一小时有效的 Access Token。"""
    return _create_token(user_id, "access", settings.access_token_expire_minutes)


def create_refresh_token(user_id: int) -> IssuedToken:
    """为用户签发三天有效的 Refresh Token。"""
    return _create_token(user_id, "refresh", settings.refresh_token_expire_minutes)


def decode_token(token: str, expected_type: str) -> TokenPayload:
    """校验 JWT 签名、标准声明和 Token 类型。"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
        token_type = str(payload["type"])
        if token_type != expected_type:
            raise TokenValidationError("Token 类型不匹配")
        return TokenPayload(
            user_id=int(payload["sub"]),
            token_type=token_type,
            token_id=str(payload["jti"]),
            expires_at=datetime.fromtimestamp(int(payload["exp"]), timezone.utc),
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise TokenValidationError("Token 无效或已过期") from error


def hash_token(token: str) -> str:
    """生成 Refresh Token 的不可逆 SHA-256 摘要。"""
    return sha256(token.encode("utf-8")).hexdigest()


def _create_token(user_id: int, token_type: str, expires_minutes: int) -> IssuedToken:
    """使用统一声明格式签发指定类型的 JWT。"""
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": expires_at,
    }
    value = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return IssuedToken(value=value, expires_at=expires_at)
