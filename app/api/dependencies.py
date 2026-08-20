"""API 通用依赖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService, InvalidCredentialsError, UserNotFoundError

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
    except (InvalidCredentialsError, UserNotFoundError) as error:
        raise _unauthorized_error() from error


def _unauthorized_error() -> HTTPException:
    """构造统一的未认证响应。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证信息无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
