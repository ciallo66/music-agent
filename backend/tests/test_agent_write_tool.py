"""写工具（创建歌单）的确认、落库与重试策略测试。"""

from __future__ import annotations

import json
from typing import Any

from app.models.playlist import Playlist
from app.services.agent.music_tools import MusicAgentTools
from app.services.agent.policy import ToolDecision, evaluate_tool_call
from app.services.agent.provider import (
    DeepSeekProvider,
    ModelResponse,
    ModelStreamUpdate,
    ToolCall,
)
from app.services.agent.registry import ToolOperation, ToolRegistry
from app.services.library_service import LibraryService
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录测试用户，返回带令牌的请求头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _current_user_id(client: TestClient, headers: dict[str, str]) -> int:
    """读取当前登录用户的主键，用于核对落库归属。"""
    return int(client.get("/api/v1/auth/me", headers=headers).json()["id"])


def _patch_stream(monkeypatch: Any, tool_call: ToolCall) -> None:
    """让模型首轮要求一次写操作，之后返回最终文本。"""
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(response=ModelResponse(None, [tool_call]))
            return
        yield ModelStreamUpdate(response=ModelResponse("已经处理完成。", []))

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)


def _confirmation_id(response: Any) -> int:
    """从 SSE 响应中取出待确认编号。"""
    marker = "event: confirmation_required\ndata: "
    raw_event = response.text.split(marker, 1)[1].split("\n", 1)[0]
    return int(json.loads(json.loads(raw_event)["content"])["confirmation_id"])


def _playlist_names(db_session: Session, user_id: int) -> list[str]:
    """读取该用户名下的全部歌单名。"""
    statement = select(Playlist.name).where(Playlist.user_id == user_id)
    return list(db_session.scalars(statement))


def _create_playlist_call(name: str) -> ToolCall:
    """构造一次创建歌单的工具调用。"""
    return ToolCall("call-1", "create_playlist", {"name": name})


def _decide(client: TestClient, headers: dict[str, str], response: Any, approved: bool) -> Any:
    """按待确认编号提交决定，并返回继续后的响应。"""
    session_id = int(response.headers["X-Session-Id"])
    return client.post(
        "/api/v1/agent/confirmations",
        json={
            "session_id": session_id,
            "decisions": [{"confirmation_id": _confirmation_id(response), "approved": approved}],
        },
        headers=headers,
    )


def test_create_playlist_is_registered_as_write_tool(db_session: Session) -> None:
    """创建歌单以写操作注册、对模型可见，且必须经过用户确认。"""
    registry = ToolRegistry()
    MusicAgentTools(db_session, user_id=1).register_all(registry)

    tool = registry.get("create_playlist")

    assert tool is not None
    assert tool.operation is ToolOperation.WRITE
    assert "create_playlist" in [item["function"]["name"] for item in registry.definitions()]
    assert evaluate_tool_call(tool, {"name": "夜间"}).decision is ToolDecision.CONFIRM


def test_write_tool_persists_only_after_approval(
    db_session: Session, client: TestClient, monkeypatch: Any
) -> None:
    """模型提出创建歌单时先等确认，用户确认后才真正落库。"""
    headers = _auth_headers(client, "WriteUser1")
    user_id = _current_user_id(client, headers)
    _patch_stream(monkeypatch, _create_playlist_call("夜间歌单"))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)

    assert "event: confirmation_required" in first.text
    assert _playlist_names(db_session, user_id) == []

    second = _decide(client, headers, first, approved=True)

    assert second.status_code == 200
    assert _playlist_names(db_session, user_id) == ["夜间歌单"]
    assert "event: end" in second.text


def test_rejected_write_tool_does_not_persist(
    db_session: Session, client: TestClient, monkeypatch: Any
) -> None:
    """用户拒绝后不得落库，并且模型要收到拒绝结果。"""
    headers = _auth_headers(client, "WriteUser2")
    user_id = _current_user_id(client, headers)
    _patch_stream(monkeypatch, _create_playlist_call("别建了"))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)
    second = _decide(client, headers, first, approved=False)

    assert second.status_code == 200
    assert "event: tool_rejected" in second.text
    assert _playlist_names(db_session, user_id) == []


def test_write_tool_failure_is_not_retried(
    db_session: Session, client: TestClient, monkeypatch: Any
) -> None:
    """写操作失败不重试（重复执行会重复建单），且失败只回滚自身不影响本轮。"""
    headers = _auth_headers(client, "WriteUser3")
    user_id = _current_user_id(client, headers)
    attempts = 0

    def failing_create(self: LibraryService, owner_id: int, payload: Any) -> Any:
        """模拟写库时的瞬时故障。"""
        nonlocal attempts
        attempts += 1
        raise OperationalError("INSERT INTO playlists", {}, Exception("connection lost"))

    monkeypatch.setattr(LibraryService, "create_playlist", failing_create)
    _patch_stream(monkeypatch, _create_playlist_call("会失败的歌单"))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)
    second = _decide(client, headers, first, approved=True)

    assert second.status_code == 200
    assert attempts == 1
    assert "event: tool_error" in second.text
    assert _playlist_names(db_session, user_id) == []
    assert "event: end" in second.text
