"""API 通用依赖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import (
    AccountDisabledError,
    AuthService,
    InvalidCredentialsError,
    UserNotFoundError,
)

bearer_scheme = HTTPBearer(auto_error=False)

# 演示账号试图写库时统一返回的中文提示。
DEMO_READONLY_DETAIL = "演示账号为只读，不能修改数据"


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


def block_demo_writes(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """要求当前登录用户不是演示账号，用于保护所有写操作接口。

    演示账号（用户名由 DEMO_USERNAME 配置，默认 demo，比较时不区分大小写）登录后
    仍可读取全部数据，但任何会落库的请求都在进入业务逻辑前被拒绝，避免演示环境
    的数据被匿名访客改动。
    """
    demo_username = settings.demo_username.strip()
    if demo_username and current_user.username.casefold() == demo_username.casefold():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=DEMO_READONLY_DETAIL)
    return current_user


def require_real_admin(current_user: Annotated[User, Depends(require_admin)]) -> User:
    """要求「真实管理员」：有管理员角色，且不是演示账号。

    演示账号为了能展示管理后台而被赋予 admin 角色，因此后台里所有会改数据的入口
    都必须用这个依赖，而不是只用 require_admin —— 否则访客可以借演示账号改动数据。
    """
    return block_demo_writes(current_user)


def _unauthorized_error() -> HTTPException:
    """构造统一的未认证响应。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证信息无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
