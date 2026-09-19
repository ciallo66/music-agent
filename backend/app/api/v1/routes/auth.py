"""用户注册、登录和双 Token 认证路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth_cookie import clear_refresh_cookie, set_refresh_cookie
from app.api.dependencies import can_manage_data, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.auth_service import (
    AccountDisabledError,
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UsernameAlreadyExistsError,
)

router = APIRouter()


def _user_response(user: User) -> UserResponse:
    """把用户模型转成响应，并标注「能否改动后台数据」。

    能力由服务端判定：角色为 admin 且不是演示账号。前端用它决定后台按钮
    是否可点，避免演示访客点下去才收到 403。
    """
    return UserResponse.model_validate(
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at,
            "can_manage_data": can_manage_data(user),
        }
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    """校验注册请求并创建用户。"""
    try:
        user = AuthService(db).register(payload.username, payload.password.get_secret_value())
    except UsernameAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在") from error
    return _user_response(user)


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccessTokenResponse:
    """验证账号密码并返回 Access Token、写入 Refresh Cookie。"""
    try:
        tokens = AuthService(db).login(payload.username, payload.password.get_secret_value())
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        ) from error
    except AccountDisabledError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用") from error
    set_refresh_cookie(response, tokens.refresh_token)
    return _access_response(tokens.access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccessTokenResponse | Response:
    """读取 HttpOnly Cookie 并轮换双 Token。"""
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Refresh Token")
    try:
        tokens = AuthService(db).refresh(refresh_token)
    except (InvalidRefreshTokenError, AccountDisabledError):
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Refresh Token 无效或已过期"},
        )
        clear_refresh_cookie(error_response)
        return error_response
    set_refresh_cookie(response, tokens.refresh_token)
    return _access_response(tokens.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """撤销当前 Refresh Token 并清除 Cookie。"""
    AuthService(db).logout(request.cookies.get(settings.refresh_cookie_name))
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """返回 Access Token 对应的当前用户。"""
    return _user_response(current_user)


def _access_response(access_token: str) -> AccessTokenResponse:
    """构造统一的 Access Token 响应。"""
    return AccessTokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
