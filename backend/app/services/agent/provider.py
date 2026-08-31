"""DeepSeek OpenAI-compatible API 客户端。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


class LLMProviderError(RuntimeError):
    """模型请求或响应格式异常。"""


@dataclass(frozen=True)
class ToolCall:
    """模型返回的一次工具调用。"""

    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    """模型的一次非流式响应。"""

    content: str | None
    tool_calls: list[ToolCall]


@dataclass(frozen=True)
class ModelStreamUpdate:
    """模型流式响应中的文本片段或最终结构。"""

    content_delta: str | None = None
    response: ModelResponse | None = None


class DeepSeekProvider:
    """通过 Chat Completions 调用 DeepSeek，并解析 Tool Calls。"""

    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelResponse:
        """发送一次模型请求；API Key 未配置时明确失败。"""
        if not settings.deepseek_api_key:
            raise LLMProviderError("AI 服务尚未配置，请联系管理员")
        payload: dict[str, Any] = {
            "model": settings.deepseek_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": settings.agent_response_token_budget,
            "stream": False,
        }
        try:
            response = httpx.post(
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json=payload,
                timeout=settings.deepseek_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as error:
            raise LLMProviderError("DeepSeek 请求超时") from error
        except (httpx.HTTPError, ValueError) as error:
            raise LLMProviderError("DeepSeek 请求失败") from error
        try:
            message = body["choices"][0]["message"]
            tool_calls = [self._parse_tool_call(item) for item in message.get("tool_calls", [])]
            return ModelResponse(content=message.get("content"), tool_calls=tool_calls)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMProviderError("DeepSeek 返回格式无效") from error

    def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Iterator[ModelStreamUpdate]:
        """以 SSE 读取模型文本，并在结束时产出完整工具调用。"""
        if not settings.deepseek_api_key:
            raise LLMProviderError("AI 服务尚未配置，请联系管理员")
        payload: dict[str, Any] = {
            "model": settings.deepseek_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": settings.agent_response_token_budget,
            "stream": True,
        }
        content_parts: list[str] = []
        tool_fragments: dict[int, dict[str, str]] = {}
        try:
            with httpx.stream(
                "POST",
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json=payload,
                timeout=settings.deepseek_timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    content, fragments = self._parse_stream_chunk(data)
                    if isinstance(content, str) and content:
                        content_parts.append(content)
                        yield ModelStreamUpdate(content_delta=content)
                    self._merge_tool_fragments(tool_fragments, fragments)
        except httpx.TimeoutException as error:
            raise LLMProviderError("DeepSeek 流式请求超时") from error
        except (httpx.HTTPError, LLMProviderError) as error:
            if isinstance(error, LLMProviderError):
                raise
            raise LLMProviderError("DeepSeek 流式请求失败") from error
        try:
            calls = self._build_tool_calls(tool_fragments)
        except (json.JSONDecodeError, TypeError, KeyError) as error:
            raise LLMProviderError("工具参数 JSON 无效") from error
        yield ModelStreamUpdate(
            response=ModelResponse(content="".join(content_parts) or None, tool_calls=calls)
        )

    @staticmethod
    def _parse_stream_chunk(data: str) -> tuple[str | None, list[tuple[int, str, str, str]]]:
        """解析一个流式 data 块，提取文本和工具参数片段。"""
        try:
            delta = json.loads(data)["choices"][0].get("delta", {})
            content = delta.get("content")
            fragments = []
            for tool_call in delta.get("tool_calls", []):
                function = tool_call.get("function", {})
                fragments.append(
                    (
                        int(tool_call.get("index", 0)),
                        str(tool_call.get("id", "")),
                        str(function.get("name", "")),
                        str(function.get("arguments", "")),
                    )
                )
            return content, fragments
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("DeepSeek 流式响应格式无效") from error

    @staticmethod
    def _merge_tool_fragments(
        target: dict[int, dict[str, str]], fragments: list[tuple[int, str, str, str]]
    ) -> None:
        """合并同一工具调用的流式参数片段。"""
        for index, call_id, name, arguments in fragments:
            fragment = target.setdefault(index, {"id": "", "name": "", "arguments": ""})
            fragment["id"] += call_id
            fragment["name"] += name
            fragment["arguments"] += arguments

    @staticmethod
    def _build_tool_calls(fragments: dict[int, dict[str, str]]) -> list[ToolCall]:
        """将合并后的工具片段解析为调用对象。"""
        calls = [
            ToolCall(
                call_id=fragment["id"],
                name=fragment["name"],
                arguments=json.loads(fragment["arguments"] or "{}"),
            )
            for _, fragment in sorted(fragments.items())
        ]
        if any(not isinstance(call.arguments, dict) for call in calls):
            raise LLMProviderError("工具参数必须是 JSON 对象")
        return calls

    @staticmethod
    def _parse_tool_call(payload: dict[str, Any]) -> ToolCall:
        """解析并校验单个 tool_call 的基本字段。"""
        function = payload["function"]
        raw_arguments = function.get("arguments", "{}")
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        if not isinstance(arguments, dict):
            raise LLMProviderError("工具参数必须是 JSON 对象")
        return ToolCall(
            call_id=str(payload["id"]),
            name=str(function["name"]),
            arguments=arguments,
        )
