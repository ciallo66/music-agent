"""API 通用依赖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import (
    AccountDisabledError,
    AuthService,
    InvalidCredentialsError,
    UserNotFoundError,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """校验 Bearer Access Token 并返回当前用户。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized_error()
    try:
        return AuthService(db).get_user_from_access_token(credentials.credentials)
    except AccountDisabledError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用") from error
    except (InvalidCredentialsError, UserNotFoundError) as error:
        raise _unauthorized_error() from error


def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """尝试读取当前用户；公开接口未登录时返回匿名状态。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return AuthService(db).get_user_from_access_token(credentials.credentials)
    except (AccountDisabledError, InvalidCredentialsError, UserNotFoundError):
        return None


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """要求当前有效用户具备管理员角色。"""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


def _unauthorized_error() -> HTTPException:
    """构造统一的未认证响应。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证信息无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
