"""Agent 对话接口测试。"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.agent.provider import (
    DeepSeekProvider,
    ModelResponse,
    ModelStreamUpdate,
    ToolCall,
)
from app.services.agent.registry import ToolRegistry
from fastapi.testclient import TestClient


def test_agent_chat_streams_expected_events(client: TestClient, monkeypatch: Any) -> None:
    """已登录用户应收到完整的 Agent SSE 生命周期事件。"""
    payload = {"username": "AgentUser1", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]

    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> object:
        """模拟两轮模型响应，覆盖工具调用后继续生成文本。"""
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(
                response=ModelResponse(
                    content=None,
                    tool_calls=[ToolCall("call-1", "analyze_user_taste", {})],
                )
            )
            return
        assert messages[-1]["role"] == "tool"
        assert len(tools) == 5
        yield ModelStreamUpdate(
            response=ModelResponse(content="你的偏好数据还不充分。", tool_calls=[])
        )

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)

    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "分析我的偏好"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: start" in response.text
    assert "event: tool" in response.text
    assert "event: content" in response.text
    assert "event: end" in response.text
    assert calls == 2


def test_agent_chat_requires_authentication(client: TestClient) -> None:
    """未登录用户不能调用 Agent。"""
    response = client.post("/api/v1/agent/chat", json={"message": "你好"})

    assert response.status_code == 401


def test_agent_chat_reports_missing_provider_key(client: TestClient, monkeypatch: Any) -> None:
    """未配置模型密钥时返回可识别的 SSE 错误，而不是固定假回答。"""
    payload = {"username": "AgentUser2", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]
    monkeypatch.setattr(settings, "deepseek_api_key", "")

    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "你好"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "AI 服务尚未配置，请联系管理员" in response.text


def test_agent_chat_does_not_duplicate_streamed_content(
    client: TestClient, monkeypatch: Any
) -> None:
    """已发送 token 增量时，SSE 不应再次发送完整文本。"""
    payload = {"username": "AgentUser3", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, object]],
        _tools: list[dict[str, object]],
    ) -> object:
        """模拟增量文本与完整响应同时返回的供应商。"""
        yield ModelStreamUpdate(content_delta="流式文本")
        yield ModelStreamUpdate(response=ModelResponse(content="流式文本", tool_calls=[]))

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "你好"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.text.count("流式文本") == 1
    assert "event: content\n" not in response.text


def test_agent_chat_recovers_from_tool_runtime_error(client: TestClient, monkeypatch: Any) -> None:
    """单个工具运行异常时应回馈模型并继续完成本轮对话。"""
    payload = {"username": "AgentUser4", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        messages: list[dict[str, object]],
        _tools: list[dict[str, object]],
    ) -> object:
        """模拟工具失败后仍能继续生成最终文本。"""
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(
                response=ModelResponse(
                    content=None,
                    tool_calls=[
                        ToolCall("call-1", "search_songs", {"query": "ambient", "limit": 1})
                    ],
                )
            )
            return
        assert messages[-1]["role"] == "tool"
        assert "工具暂时不可用" in str(messages[-1]["content"])
        yield ModelStreamUpdate(response=ModelResponse(content="已完成", tool_calls=[]))

    def failing_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, object]
    ) -> dict[str, object]:
        """模拟工具运行时异常。"""
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", failing_call)
    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "找氛围音乐"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "event: tool_error" in response.text
    assert "event: content" in response.text
    assert "event: end" in response.text
