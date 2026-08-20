"""认证接口的 Pydantic 请求与响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

Username = Annotated[str, Field(min_length=6, max_length=18)]
Password = Annotated[SecretStr, Field(min_length=6, max_length=18)]


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    username: Username
    password: Password


class LoginRequest(BaseModel):
    """用户登录请求。"""

    username: Username
    password: Password


class UserResponse(BaseModel):
    """可安全返回给前端的用户信息。"""

    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseModel):
    """Access Token 响应。"""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
