"""认证接口的 Pydantic 请求与响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

Username = Annotated[str, Field(min_length=4, max_length=18)]
Password = Annotated[SecretStr, Field(min_length=4, max_length=18)]


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    username: Username
    password: Password

    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    """用户登录请求。"""

    username: Username
    password: Password

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """可安全返回给前端的用户信息。"""

    id: int
    username: str
    role: str
    status: str
    created_at: datetime
    # 能否改动后台数据：角色是 admin 且不是演示账号。
    # 前端据此把后台操作按钮置为只读，避免访客点了才收到 403。
    can_manage_data: bool = False

    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseModel):
    """Access Token 响应。"""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
