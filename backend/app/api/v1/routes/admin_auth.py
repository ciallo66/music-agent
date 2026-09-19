"""独立管理员登录和身份确认路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.auth_cookie import set_refresh_cookie
from app.api.dependencies import can_manage_data, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, UserResponse
from app.services.auth_service import (
    AccountDisabledError,
    AdminAccessDeniedError,
    AuthService,
    InvalidCredentialsError,
)

router = APIRouter()


@router.post("/login", response_model=AccessTokenResponse)
def admin_login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccessTokenResponse:
    """仅允许有效管理员登录并签发双Token。"""
    try:
        tokens = AuthService(db).login_admin(
            payload.username,
            payload.password.get_secret_value(),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        ) from error
    except AccountDisabledError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用") from error
    except AdminAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限"
        ) from error
    set_refresh_cookie(response, tokens.refresh_token)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def read_current_admin(admin: Annotated[User, Depends(require_admin)]) -> UserResponse:
    """返回当前管理员身份并验证实时权限（含能否改动后台数据）。"""
    return UserResponse.model_validate(
        {
            "id": admin.id,
            "username": admin.username,
            "role": admin.role,
            "status": admin.status,
            "created_at": admin.created_at,
            "can_manage_data": can_manage_data(admin),
        }
    )
