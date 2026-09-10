"""Agent 工具调用安全策略测试。"""

from __future__ import annotations

import json
from typing import Any

from app.services.agent.music_tools import MusicAgentTools
from app.services.agent.policy import ToolDecision, evaluate_tool_call
from app.services.agent.provider import (
    DeepSeekProvider,
    ModelResponse,
    ModelStreamUpdate,
    ToolCall,
)
from app.services.agent.registry import AgentTool, ToolOperation, ToolRegistry
from fastapi.testclient import TestClient


def _noop_handler(_arguments: dict[str, Any]) -> dict[str, Any]:
    """占位处理器，仅用于构造工具定义。"""
    return {"ok": True}


def _read_tool(counter: list[str]) -> AgentTool:
    """构造一个只读工具，执行时记录一次调用。"""

    def handler(_arguments: dict[str, Any]) -> dict[str, Any]:
        counter.append("read")
        return {"items": [], "count": 0}

    return AgentTool("list_songs", "列出歌曲。", {"type": "object", "properties": {}}, handler)


def _write_tool(counter: list[dict[str, Any]]) -> AgentTool:
    """构造一个写操作工具，执行时记录参数。"""

    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        counter.append(dict(arguments))
        return {"created": True}

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    return AgentTool("create_playlist", "创建歌单。", schema, handler, ToolOperation.WRITE)


def _delete_tool() -> AgentTool:
    """构造一个删除类工具。"""
    schema = {"type": "object", "properties": {"song_id": {"type": "integer"}}}
    return AgentTool("delete_song", "删除歌曲。", schema, _noop_handler, ToolOperation.DELETE)


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录测试用户，返回带令牌的请求头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register_tools(monkeypatch: Any, tools: list[AgentTool]) -> None:
    """用假工具集合替换注册流程，让用例只依赖被测的安全逻辑。"""

    def register_all(_self: MusicAgentTools, registry: ToolRegistry) -> None:
        for tool in tools:
            registry.register(tool)

    monkeypatch.setattr(MusicAgentTools, "register_all", register_all)


def _patch_stream(monkeypatch: Any, tool_call: ToolCall) -> None:
    """让模型首轮要求一次工具调用，之后返回最终文本。"""
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


def test_read_tool_is_allowed() -> None:
    """只读工具直接放行。"""
    verdict = evaluate_tool_call(_read_tool([]), {"query": "ambient"})

    assert verdict.decision is ToolDecision.ALLOW


def test_write_tool_requires_confirmation() -> None:
    """写操作需要用户确认。"""
    verdict = evaluate_tool_call(_write_tool([]), {"name": "夜间歌单"})

    assert verdict.decision is ToolDecision.CONFIRM


def test_delete_tool_requires_confirmation() -> None:
    """删除操作需要用户确认。"""
    verdict = evaluate_tool_call(_delete_tool(), {"song_id": 1})

    assert verdict.decision is ToolDecision.CONFIRM


def test_confirmed_write_tool_is_allowed() -> None:
    """用户确认过的写操作放行。"""
    verdict = evaluate_tool_call(_write_tool([]), {"name": "夜间歌单"}, confirmed=True)

    assert verdict.decision is ToolDecision.ALLOW


def test_identity_argument_is_denied() -> None:
    """参数携带身份字段时拒绝执行。"""
    verdict = evaluate_tool_call(_write_tool([]), {"user_id": 999, "name": "x"})

    assert verdict.decision is ToolDecision.DENY
    assert "身份字段" in verdict.reason


def test_undeclared_argument_is_denied() -> None:
    """参数不在工具声明的白名单里时拒绝执行。"""
    verdict = evaluate_tool_call(_write_tool([]), {"name": "x", "uid": 5})

    assert verdict.decision is ToolDecision.DENY
    assert "未声明" in verdict.reason


def test_identity_argument_is_denied_even_when_confirmed() -> None:
    """即使被"确认"，身份字段仍然拒绝，确认不能绕过校验。"""
    verdict = evaluate_tool_call(_write_tool([]), {"owner_id": 1}, confirmed=True)

    assert verdict.decision is ToolDecision.DENY


def test_all_tools_stay_visible_to_model() -> None:
    """写/删工具同样要出现在发给模型的工具清单里，不能靠隐藏工具限制能力。"""
    registry = ToolRegistry()
    registry.register(_write_tool([]))
    registry.register(_delete_tool())

    names = [item["function"]["name"] for item in registry.definitions()]

    assert names == ["create_playlist", "delete_song"]


def test_high_risk_tool_waits_for_confirmation(client: TestClient, monkeypatch: Any) -> None:
    """写操作只登记待确认并结束本轮，不执行工具。"""
    headers = _auth_headers(client, "PolicyUser1")
    executed: list[dict[str, Any]] = []
    _register_tools(monkeypatch, [_write_tool(executed)])
    _patch_stream(monkeypatch, ToolCall("call-1", "create_playlist", {"name": "夜间"}))

    response = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)

    assert response.status_code == 200
    assert "event: confirmation_required" in response.text
    assert "create_playlist" in response.text
    assert executed == []
    assert "event: end" in response.text


def test_confirmed_call_executes_after_user_approval(client: TestClient, monkeypatch: Any) -> None:
    """按确认编号提交后，工具才真正执行。"""
    headers = _auth_headers(client, "PolicyUser2")
    executed: list[dict[str, Any]] = []
    _register_tools(monkeypatch, [_write_tool(executed)])
    _patch_stream(monkeypatch, ToolCall("call-1", "create_playlist", {"name": "夜间"}))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)
    session_id = int(first.headers["X-Session-Id"])
    confirmation_id = _confirmation_id(first)
    assert executed == []

    second = client.post(
        "/api/v1/agent/confirmations",
        json={
            "session_id": session_id,
            "decisions": [{"confirmation_id": confirmation_id, "approved": True}],
        },
        headers=headers,
    )

    assert second.status_code == 200
    assert executed == [{"name": "夜间"}]
    assert "event: end" in second.text


def test_rejected_call_is_not_executed(client: TestClient, monkeypatch: Any) -> None:
    """用户拒绝后工具不执行，模型收到拒绝结果。"""
    headers = _auth_headers(client, "PolicyUser3")
    executed: list[dict[str, Any]] = []
    _register_tools(monkeypatch, [_write_tool(executed)])
    _patch_stream(monkeypatch, ToolCall("call-1", "create_playlist", {"name": "夜间"}))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)
    session_id = int(first.headers["X-Session-Id"])
    confirmation_id = _confirmation_id(first)

    second = client.post(
        "/api/v1/agent/confirmations",
        json={
            "session_id": session_id,
            "decisions": [{"confirmation_id": confirmation_id, "approved": False}],
        },
        headers=headers,
    )

    assert second.status_code == 200
    assert executed == []
    assert "event: tool_rejected" in second.text
    assert "event: end" in second.text


def test_confirmation_cannot_be_replayed(client: TestClient, monkeypatch: Any) -> None:
    """同一条确认记录不能重复提交，防止重放执行。"""
    headers = _auth_headers(client, "PolicyUser4")
    executed: list[dict[str, Any]] = []
    _register_tools(monkeypatch, [_write_tool(executed)])
    _patch_stream(monkeypatch, ToolCall("call-1", "create_playlist", {"name": "夜间"}))

    first = client.post("/api/v1/agent/chat", json={"message": "建个歌单"}, headers=headers)
    session_id = int(first.headers["X-Session-Id"])
    confirmation_id = _confirmation_id(first)
    body = {
        "session_id": session_id,
        "decisions": [{"confirmation_id": confirmation_id, "approved": True}],
    }

    assert client.post("/api/v1/agent/confirmations", json=body, headers=headers).status_code == 200
    replay = client.post("/api/v1/agent/confirmations", json=body, headers=headers)

    assert replay.status_code == 409
    assert executed == [{"name": "夜间"}]


def test_identity_argument_is_rejected_at_runtime(client: TestClient, monkeypatch: Any) -> None:
    """模型试图指定 user_id 时，工具不执行并回写错误。"""
    headers = _auth_headers(client, "PolicyUser5")
    executed: list[str] = []
    _register_tools(monkeypatch, [_read_tool(executed)])
    _patch_stream(monkeypatch, ToolCall("call-1", "list_songs", {"user_id": 999}))

    response = client.post("/api/v1/agent/chat", json={"message": "看歌"}, headers=headers)

    assert response.status_code == 200
    assert executed == []
    assert "event: tool_error" in response.text
    assert "身份字段" in response.text
