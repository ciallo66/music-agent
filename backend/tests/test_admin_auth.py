"""管理员角色、状态和独立登录接口测试。"""

from __future__ import annotations

from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.services.auth_service import AuthService
from fastapi.testclient import TestClient
from scripts.create_admin import create_admin_account
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_registration_cannot_elevate_role(client: TestClient) -> None:
    """普通注册请求不得接受角色或状态字段。"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "Hacker01",
            "password": "Abc123",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_regular_user_cannot_use_admin_login(client: TestClient) -> None:
    """普通用户使用管理员登录入口应返回403。"""
    payload = {"username": "Normal01", "password": "Abc123"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/admin/auth/login", json=payload)

    assert response.status_code == 403


def test_admin_login_and_admin_dependency(client: TestClient, db_session: Session) -> None:
    """管理员应能登录并通过实时管理员权限校验。"""
    AuthService(db_session).create_admin("Admin001", "Abc123")

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "Admin001", "password": "Abc123"},
    )

    assert response.status_code == 200
    assert settings.refresh_cookie_name in response.cookies
    access_token = response.json()["access_token"]
    current_admin = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert current_admin.status_code == 200
    assert current_admin.json()["role"] == UserRole.ADMIN.value


def test_disabled_user_loses_access_immediately(
    client: TestClient,
    db_session: Session,
) -> None:
    """账号禁用后旧Access Token和Refresh Token都应立即失效。"""
    payload = {"username": "Disable1", "password": "Abc123"}
    client.post("/api/v1/auth/register", json=payload)
    login_response = client.post("/api/v1/auth/login", json=payload)
    access_token = login_response.json()["access_token"]
    user = db_session.scalar(select(User).where(User.username == "Disable1"))
    assert user is not None
    user.status = UserStatus.DISABLED.value
    db_session.commit()

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    refresh_response = client.post("/api/v1/auth/refresh")

    assert current_user.status_code == 403
    assert refresh_response.status_code == 401


def test_admin_demotion_invalidates_admin_access(
    client: TestClient,
    db_session: Session,
) -> None:
    """管理员被降级后旧Access Token应立即失去管理员权限。"""
    admin = AuthService(db_session).create_admin("Demote01", "Abc123")
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "Demote01", "password": "Abc123"},
    )
    access_token = login_response.json()["access_token"]
    admin.role = UserRole.USER.value
    db_session.commit()

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403


def test_create_admin_script_uses_hash_and_admin_role(db_session: Session) -> None:
    """管理员脚本辅助函数应保存Argon2哈希和admin角色。"""
    create_admin_account(db_session, "Script01", "Abc123")

    user = db_session.scalar(select(User).where(User.username == "Script01"))
    assert user is not None
    assert user.role == UserRole.ADMIN.value
    assert user.status == UserStatus.ACTIVE.value
    assert user.password_hash != "Abc123"
    assert user.password_hash.startswith("$argon2id$")
