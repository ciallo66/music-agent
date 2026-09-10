"""Agent 循环兜底与工具失败重试测试。"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.agent.music_tools import AgentToolError
from app.services.agent.provider import (
    DeepSeekProvider,
    ModelResponse,
    ModelStreamUpdate,
    ToolCall,
)
from app.services.agent.registry import ToolRegistry
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录测试用户，返回带令牌的请求头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _chat(client: TestClient, headers: dict[str, str]) -> Any:
    """调用 Agent 对话接口。"""
    return client.post("/api/v1/agent/chat", json={"message": "找氛围音乐"}, headers=headers)


def _tool_call(limit: int = 1) -> ToolCall:
    """构造一个搜索类工具调用。"""
    return ToolCall("call-1", "search_songs", {"query": "ambient", "limit": limit})


def test_transient_tool_error_is_retried_then_succeeds(
    client: TestClient, monkeypatch: Any
) -> None:
    """瞬时故障应先重试，重试成功后不再产生 tool_error。"""
    headers = _auth_headers(client, "FallbackUser1")
    monkeypatch.setattr(settings, "agent_tool_retry_backoff_seconds", 0.0)
    attempts = 0
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """首轮要求调用工具，次轮返回最终文本。"""
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call()]))
            return
        assert messages[-1]["role"] == "tool"
        yield ModelStreamUpdate(response=ModelResponse("已经找到结果。", []))

    def flaky_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """首次抛连接类瞬时异常，之后正常返回。"""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OperationalError("SELECT 1", {}, Exception("connection lost"))
        return {"items": [], "count": 0}

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", flaky_call)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert attempts == 2
    assert "event: tool_error" not in response.text
    assert "event: end" in response.text


def test_transient_tool_error_exhausts_retries_and_degrades(
    client: TestClient, monkeypatch: Any
) -> None:
    """瞬时故障重试耗尽后应降级为可重试提示，本轮仍能正常结束。"""
    headers = _auth_headers(client, "FallbackUser2")
    monkeypatch.setattr(settings, "agent_tool_retry_backoff_seconds", 0.0)
    attempts = 0
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """次轮断言已收到降级后的错误信息。"""
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call()]))
            return
        assert "工具暂时不可用" in str(messages[-1]["content"])
        yield ModelStreamUpdate(response=ModelResponse("工具暂时不可用。", []))

    def failing_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """始终抛连接类瞬时异常。"""
        nonlocal attempts
        attempts += 1
        raise OperationalError("SELECT 1", {}, Exception("connection lost"))

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", failing_call)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert attempts == settings.agent_tool_retry_max + 1
    assert "event: tool_error" in response.text
    assert "event: end" in response.text


def test_deterministic_tool_error_is_not_retried(client: TestClient, monkeypatch: Any) -> None:
    """确定性失败不应重试，原始错误文本要透传给模型。"""
    headers = _auth_headers(client, "FallbackUser3")
    attempts = 0
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """次轮断言收到的是工具的业务错误原文。"""
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call()]))
            return
        assert "歌曲不存在" in str(messages[-1]["content"])
        yield ModelStreamUpdate(response=ModelResponse("没有找到这首歌。", []))

    def business_failure(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """模拟工具层的业务错误。"""
        nonlocal attempts
        attempts += 1
        raise AgentToolError("歌曲不存在")

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", business_failure)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert attempts == 1
    assert "歌曲不存在" in response.text
    assert "event: end" in response.text


def test_repeated_tool_calls_trigger_wrap_up(client: TestClient, monkeypatch: Any) -> None:
    """连续重复的工具调用应触发兜底收尾，而不是等到轮数上限报错。"""
    headers = _auth_headers(client, "FallbackUser4")
    monkeypatch.setattr(settings, "agent_no_progress_limit", 1)
    calls = 0
    executed = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """每轮都返回完全相同的工具调用。"""
        nonlocal calls
        calls += 1
        yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call()]))

    def counting_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """记录工具实际执行次数。"""
        nonlocal executed
        executed += 1
        return {"items": [], "count": 0}

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", counting_call)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert executed == 1
    assert calls == 3  # 两次正常轮次 + 一次收尾调用
    assert "工具调用次数超过限制" not in response.text
    assert "event: end" in response.text


def test_round_limit_triggers_soft_landing(client: TestClient, monkeypatch: Any) -> None:
    """轮数保险丝触发时应软着陆，而不是抛硬错误。"""
    headers = _auth_headers(client, "FallbackUser5")
    monkeypatch.setattr(settings, "agent_max_tool_rounds", 1)
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """每轮返回参数不同的工具调用，避免触发重复检测。"""
        nonlocal calls
        calls += 1
        yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call(limit=calls)]))

    def stub_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """返回空结果，避免依赖真实数据。"""
        return {"items": [], "count": 0}

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", stub_call)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert calls == 2  # 一次正常轮次 + 一次收尾调用
    assert "工具调用次数超过限制" not in response.text
    assert "event: end" in response.text


def test_time_budget_triggers_soft_landing(client: TestClient, monkeypatch: Any) -> None:
    """时间预算耗尽时应软着陆，且不再执行任何工具。"""
    headers = _auth_headers(client, "FallbackUser6")
    monkeypatch.setattr(settings, "agent_total_timeout_seconds", 0.0)
    calls = 0
    executed = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        """模型始终要求调用工具。"""
        nonlocal calls
        calls += 1
        yield ModelStreamUpdate(response=ModelResponse(None, [_tool_call()]))

    def counting_call(
        _registry: ToolRegistry, _name: str, _arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """记录工具实际执行次数。"""
        nonlocal executed
        executed += 1
        return {"items": [], "count": 0}

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)
    monkeypatch.setattr(ToolRegistry, "call", counting_call)
    response = _chat(client, headers)

    assert response.status_code == 200
    assert executed == 0
    assert calls == 2  # 一次模型轮次 + 一次收尾调用
    assert "event: end" in response.text
