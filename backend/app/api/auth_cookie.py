"""认证 Cookie 的统一写入与清除工具。"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """以安全属性写入 Refresh Token Cookie。"""
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_minutes * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    """清除浏览器中的 Refresh Token Cookie。"""
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )
