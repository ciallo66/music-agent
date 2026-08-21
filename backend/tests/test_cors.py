"""浏览器前后端分离所需的 CORS 配置测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_local_frontend_preflight_is_allowed(client: TestClient) -> None:
    """本地 Vite 页面应能携带认证 Cookie 调用后端。"""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
