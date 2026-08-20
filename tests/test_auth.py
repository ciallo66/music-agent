"""双 Token 认证接口集成测试。"""

from __future__ import annotations

from collections.abc import Generator

import jwt
import pytest
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """在外层事务中提供可回滚的测试数据库会话。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """让FastAPI请求复用可回滚的测试会话。"""

    def override_get_db() -> Generator[Session, None, None]:
        """返回当前测试数据库会话。"""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_register_hashes_password(client: TestClient, db_session: Session) -> None:
    """注册应只保存Argon2哈希且响应不泄露密码字段。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "Player01", "password": "Abc123"},
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id", "username", "created_at"}
    user = db_session.scalar(select(User).where(User.username == "Player01"))
    assert user is not None
    assert user.password_hash != "Abc123"
    assert user.password_hash.startswith("$argon2id$")


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("short", "Abc123"),
        ("a" * 19, "Abc123"),
        ("Player01", "12345"),
        ("Player01", "a" * 19),
    ],
)
def test_register_validates_lengths(
    client: TestClient,
    username: str,
    password: str,
) -> None:
    """Pydantic应拒绝用户名或密码长度超出6到18位。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )

    assert response.status_code == 422


def test_username_is_case_sensitive(client: TestClient) -> None:
    """仅大小写不同的用户名应被视为不同账号。"""
    first = client.post(
        "/api/v1/auth/register",
        json={"username": "CaseUser", "password": "Abc123"},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"username": "caseuser", "password": "Abc123"},
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_duplicate_username_returns_conflict(client: TestClient) -> None:
    """完全相同的用户名重复注册应返回409。"""
    payload = {"username": "Repeat01", "password": "Abc123"}

    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_cookie_and_current_user(client: TestClient) -> None:
    """登录应返回Access Token、写入安全Cookie并允许读取当前用户。"""
    payload = {"username": "Login001", "password": "PassWord"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    claims = jwt.decode(
        body["access_token"],
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 3600
    refresh_claims = jwt.decode(
        client.cookies[settings.refresh_cookie_name],
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert refresh_claims["type"] == "refresh"
    assert refresh_claims["exp"] - refresh_claims["iat"] == 259200

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["username"] == "Login001"


def test_wrong_password_returns_unauthorized(client: TestClient) -> None:
    """错误密码应统一返回401。"""
    client.post(
        "/api/v1/auth/register",
        json={"username": "Wrong001", "password": "Correct1"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "Wrong001", "password": "WrongPwd"},
    )

    assert response.status_code == 401


def test_refresh_rotates_cookie_and_rejects_reuse(client: TestClient) -> None:
    """刷新应轮换Cookie，并拒绝再次使用已撤销Token。"""
    payload = {"username": "Rotate01", "password": "Abc123"}
    client.post("/api/v1/auth/register", json=payload)
    client.post("/api/v1/auth/login", json=payload)
    old_refresh_token = client.cookies.get(settings.refresh_cookie_name)
    assert old_refresh_token is not None

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert client.cookies.get(settings.refresh_cookie_name) != old_refresh_token
    reuse_client = TestClient(app)
    reuse_client.cookies.set(
        settings.refresh_cookie_name,
        old_refresh_token,
        path="/api/v1/auth",
    )
    try:
        reuse_response = reuse_client.post("/api/v1/auth/refresh")
        assert reuse_response.status_code == 401
        clear_cookie = reuse_response.headers["set-cookie"].lower()
        assert f"{settings.refresh_cookie_name}=" in clear_cookie
        assert "max-age=0" in clear_cookie
        assert "path=/api/v1/auth" in clear_cookie
    finally:
        reuse_client.close()


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    """退出登录应清除Cookie并使原Refresh Token失效。"""
    payload = {"username": "Logout01", "password": "Abc123"}
    client.post("/api/v1/auth/register", json=payload)
    client.post("/api/v1/auth/login", json=payload)
    refresh_token = client.cookies.get(settings.refresh_cookie_name)
    assert refresh_token is not None

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.cookies.get(settings.refresh_cookie_name) is None
    client.cookies.set(
        settings.refresh_cookie_name,
        refresh_token,
        path="/api/v1/auth",
    )
    assert client.post("/api/v1/auth/refresh").status_code == 401
