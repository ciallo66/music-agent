"""DeepSeek Provider 协议测试。"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from app.core.config import settings
from app.services.agent.provider import DeepSeekProvider, LLMProviderError


def test_provider_parses_tool_call_response(monkeypatch: Any) -> None:
    """Provider 应按 Chat Completions 格式发送请求并解析 tool_call。"""
    captured: dict[str, Any] = {}

    class FakeResponse:
        """模拟非流式模型响应。"""

        def raise_for_status(self) -> None:
            """模拟成功响应的状态检查。"""
            return None

        def json(self) -> dict[str, Any]:
            """返回带工具调用的 Chat Completions 响应。"""
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "search_songs",
                                        "arguments": '{"query":"ambient"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        """记录请求参数并返回模拟响应。"""
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)
    response = DeepSeekProvider().complete(
        [{"role": "user", "content": "找氛围音乐"}],
        [{"type": "function", "function": {"name": "search_songs"}}],
    )

    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["stream"] is False
    assert captured["json"]["max_tokens"] == settings.agent_response_token_budget
    assert response.tool_calls[0].name == "search_songs"
    assert response.tool_calls[0].arguments == {"query": "ambient"}


def test_provider_reports_timeout(monkeypatch: Any) -> None:
    """模型请求超时应转换为可展示的 Provider 错误。"""
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    def fake_post(*_args: Any, **_kwargs: Any) -> None:
        """模拟网络超时。"""
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(LLMProviderError, match="DeepSeek 请求超时"):
        DeepSeekProvider().complete([], [])


def test_provider_stream_merges_content_and_tool_fragments(monkeypatch: Any) -> None:
    """Provider 应合并 SSE 文本和跨 chunk 的工具参数。"""

    class FakeStreamResponse:
        """模拟可迭代的流式模型响应。"""

        def raise_for_status(self) -> None:
            """模拟流式响应的状态检查。"""
            return None

        def iter_lines(self) -> list[str]:
            """返回跨行拆分的文本和工具参数片段。"""
            first_arguments = '{"query":"am'
            second_arguments = 'bient"}'

            def sse_data(payload: dict[str, Any]) -> str:
                """把对象编码成单行 SSE 数据。"""
                return f"data: {json.dumps(payload)}"

            return [
                sse_data({"choices": [{"delta": {"content": "你好"}}]}),
                sse_data(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call-1",
                                            "function": {
                                                "name": "search_songs",
                                                "arguments": first_arguments,
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
                sse_data(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "function": {"arguments": second_arguments},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
                "data: [DONE]",
            ]

        def __enter__(self) -> FakeStreamResponse:
            """进入响应上下文。"""
            return self

        def __exit__(self, *_args: object) -> None:
            """退出响应上下文。"""
            return None

    def fake_stream(*_args: Any, **_kwargs: Any) -> FakeStreamResponse:
        """返回可迭代的模拟 SSE 响应。"""
        return FakeStreamResponse()

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(httpx, "stream", fake_stream)
    updates = list(
        DeepSeekProvider().stream(
            [{"role": "user", "content": "找氛围音乐"}],
            [{"type": "function", "function": {"name": "search_songs"}}],
        )
    )

    assert [update.content_delta for update in updates[:-1]] == ["你好"]
    assert updates[-1].response is not None
    assert updates[-1].response.tool_calls[0].arguments == {"query": "ambient"}
