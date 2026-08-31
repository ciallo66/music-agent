"""管理员数据导入任务接口测试。"""

from __future__ import annotations

from app.services.auth_service import AuthService
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    """创建管理员并返回访问令牌。"""
    AuthService(db).create_admin("ImportAdmin", "Abc123")
    db.commit()
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "ImportAdmin", "password": "Abc123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_import_routes_require_admin(client: TestClient) -> None:
    """未登录用户不能查看或创建导入任务。"""
    assert client.get("/api/v1/admin/imports").status_code == 401
    assert client.post("/api/v1/admin/imports/jamendo", json={}).status_code == 401


def test_create_and_query_import_job(client: TestClient, db_session: Session, monkeypatch) -> None:
    """管理员可创建任务，活动任务并发请求返回 409。"""
    from app.api.v1.routes import admin_imports
    from app.services import import_job_service

    headers = _admin_headers(client, db_session)
    monkeypatch.setattr(import_job_service.settings, "jamendo_client_id", "test-client")
    monkeypatch.setattr(admin_imports, "run_jamendo_import_job", lambda job_id: None)

    created = client.post(
        "/api/v1/admin/imports/jamendo",
        json={"limit": 100, "batch_size": 50},
        headers=headers,
    )
    assert created.status_code == 202
    assert created.json()["status"] == "pending"
    duplicate = client.post(
        "/api/v1/admin/imports/jamendo",
        json={"limit": 100, "batch_size": 50},
        headers=headers,
    )
    assert duplicate.status_code == 409

    job_id = created.json()["id"]
    assert client.get(f"/api/v1/admin/imports/{job_id}", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/imports", headers=headers).json()[0]["id"] == job_id
