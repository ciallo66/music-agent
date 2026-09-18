"""管理后台接口测试：概览统计与账号管理。"""

from __future__ import annotations

from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PASSWORD = "Abcd1234"


def _make_user(db: Session, username: str, role: UserRole = UserRole.USER) -> User:
    """直接写库创建账号，避免依赖注册接口的额外校验。"""
    user = User(
        username=username,
        password_hash=hash_password(PASSWORD),
        role=role.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _login(client: TestClient, username: str) -> dict[str, str]:
    """以普通登录接口登录，返回认证头。"""
    response = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_overview_requires_admin(client: TestClient, db_session: Session) -> None:
    """普通用户访问后台统计应被拒绝。"""
    _make_user(db_session, "PlainUser")
    headers = _login(client, "PlainUser")

    response = client.get("/api/v1/admin/overview", headers=headers)

    assert response.status_code == 403


def test_overview_returns_counts(client: TestClient, db_session: Session) -> None:
    """管理员可以拿到计数与流派分布。"""
    _make_user(db_session, "RootAdmin", UserRole.ADMIN)
    headers = _login(client, "RootAdmin")

    response = client.get("/api/v1/admin/overview", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["songs"] >= 0
    assert body["users"] >= 1
    assert body["admins"] >= 1
    assert isinstance(body["genre_distribution"], list)


def test_list_users_filters_by_keyword(client: TestClient, db_session: Session) -> None:
    """账号列表支持按用户名搜索。"""
    _make_user(db_session, "RootAdmin", UserRole.ADMIN)
    _make_user(db_session, "SearchTarget")
    headers = _login(client, "RootAdmin")

    response = client.get("/api/v1/admin/users", params={"keyword": "Search"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "SearchTarget"
    assert body["items"][0]["role"] == "user"


def test_update_user_role_and_status(client: TestClient, db_session: Session) -> None:
    """管理员可以调整角色与状态。"""
    _make_user(db_session, "RootAdmin", UserRole.ADMIN)
    target = _make_user(db_session, "PromoteMe")
    headers = _login(client, "RootAdmin")

    response = client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"role": "admin", "status": "disabled"},
        headers=headers,
    )

    assert response.status_code == 200
    row = next(item for item in response.json()["items"] if item["id"] == target.id)
    assert row["role"] == "admin"
    assert row["status"] == "disabled"


def test_cannot_demote_last_admin(client: TestClient, db_session: Session) -> None:
    """只剩一个管理员时不允许降级，避免后台失去入口。"""
    admin = _make_user(db_session, "OnlyAdmin", UserRole.ADMIN)
    headers = _login(client, "OnlyAdmin")

    response = client.patch(
        f"/api/v1/admin/users/{admin.id}", json={"role": "user"}, headers=headers
    )

    assert response.status_code == 400
    assert "管理员" in response.json()["detail"]


def test_update_unknown_user_returns_404(client: TestClient, db_session: Session) -> None:
    """对不存在的账号操作返回 404。"""
    _make_user(db_session, "RootAdmin", UserRole.ADMIN)
    headers = _login(client, "RootAdmin")

    response = client.patch(
        "/api/v1/admin/users/999999", json={"status": "disabled"}, headers=headers
    )

    assert response.status_code == 404


def test_invalid_role_returns_400(client: TestClient, db_session: Session) -> None:
    """非法角色值返回 400 而不是落库。"""
    _make_user(db_session, "RootAdmin", UserRole.ADMIN)
    target = _make_user(db_session, "KeepUser")
    headers = _login(client, "RootAdmin")

    response = client.patch(
        f"/api/v1/admin/users/{target.id}", json={"role": "superuser"}, headers=headers
    )

    assert response.status_code == 400
