"""音乐 Agent 的模型调用和工具编排。"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.chat_repository import ChatRepository
from app.schemas.agent import AgentEvent
from app.services.agent.context import compact_messages, serialize_tool_result
from app.services.agent.music_tools import AgentToolError, MusicAgentTools
from app.services.agent.provider import DeepSeekProvider, LLMProviderError, ModelResponse
from app.services.agent.registry import ToolRegistry

SYSTEM_PROMPT = """你是 Music Agent，一个严谨的中文音乐助手。
你只能通过提供的只读工具查询音乐数据，不得编造数据库中不存在的歌曲、特征或用户行为。
需要真实数据时先调用工具；工具返回为空时必须明确说明没有匹配数据。
回答音乐知识问题时必须先检索知识库；检索结果标记为不相关或为空时，不要猜测答案。
回答要简洁，引用歌曲特征时只能使用工具返回的字段。"""

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """驱动 DeepSeek Function Calling 循环并输出 SSE 事件。"""

    def __init__(
        self,
        db: Session,
        user_id: int,
        session_id: int,
        history: list[dict[str, str]],
        provider: DeepSeekProvider | None = None,
    ) -> None:
        self.db = db
        self.chat = ChatRepository(db)
        self.session_id = session_id
        self.history = history
        self.provider = provider or DeepSeekProvider()
        self.registry = ToolRegistry()
        self._last_response: ModelResponse | None = None
        self._streamed_content = False
        MusicAgentTools(db, user_id).register_all(self.registry)

    def stream(self, message: str) -> Iterator[str]:
        """执行模型和工具循环，逐条产生 SSE 事件。"""
        try:
            yield from self._stream(message)
        except GeneratorExit:
            logger.info("Agent SSE 客户端已断开，停止当前会话：%s", self.session_id)

    def _stream(self, message: str) -> Iterator[str]:
        """执行单次 Agent 循环；外层负责处理客户端取消。"""
        yield self._event(AgentEvent(type="start", content="正在理解你的问题"))
        self.chat.add_message(self.session_id, "user", message)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.history,
            {"role": "user", "content": message},
        ]
        current_turn_index = len(messages) - 1
        for _ in range(settings.agent_max_tool_rounds):
            messages, current_turn_index = compact_messages(
                messages,
                settings.agent_context_token_budget,
                current_turn_index,
            )
            try:
                yield from self._stream_model(messages)
            except LLMProviderError as error:
                yield self._event(AgentEvent(type="error", content=str(error)))
                return
            response = self._last_response
            if response is None:
                yield self._event(AgentEvent(type="error", content="DeepSeek 未返回有效响应"))
                return
            messages.append(self._assistant_message(response))
            if not response.tool_calls:
                content = response.content or "模型没有返回文本。"
                self.chat.add_message(self.session_id, "assistant", content)
                if not self._streamed_content:
                    yield self._event(AgentEvent(type="content", content=content))
                yield self._event(AgentEvent(type="end", content="分析完成"))
                return
            for call in response.tool_calls:
                yield from self._execute_tool(messages, call)
        yield self._event(AgentEvent(type="error", content="工具调用次数超过限制"))

    def _stream_model(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        """读取一轮模型响应并转成增量 SSE。"""
        self._last_response = None
        self._streamed_content = False
        try:
            for update in self.provider.stream(messages, self.registry.definitions()):
                if update.content_delta:
                    self._streamed_content = True
                    yield self._event(
                        AgentEvent(type="content_delta", content=update.content_delta)
                    )
                if update.response is not None:
                    self._last_response = update.response
        except LLMProviderError:
            raise
        except Exception as error:
            logger.exception("Agent 模型调用异常，会话：%s", self.session_id)
            raise LLMProviderError("模型服务暂时不可用，请稍后重试") from error
        if self._last_response is None:
            raise LLMProviderError("DeepSeek 未返回有效响应")

    @staticmethod
    def _event(event: AgentEvent) -> str:
        """编码单条 SSE 事件。"""
        return (
            f"event: {event.type}\ndata: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
        )

    @staticmethod
    def _assistant_message(response: Any) -> dict[str, Any]:
        """将模型响应转换成下一轮请求需要的 assistant 消息。"""
        message: dict[str, Any] = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in response.tool_calls
            ]
        return message

    def _execute_tool(self, messages: list[dict[str, Any]], call: Any) -> Iterator[str]:
        """执行单个工具并追加 tool 消息。"""
        yield self._event(AgentEvent(type="tool", content=f"正在调用 {call.name}"))
        try:
            result = self.registry.call(call.name, call.arguments)
        except (AgentToolError, KeyError, ValueError) as error:
            result = {"error": str(error)}
            yield self._event(AgentEvent(type="tool_error", content=str(error)))
        except Exception:
            logger.exception("Agent 工具执行异常：%s", call.name)
            result = {"error": "工具暂时不可用，请稍后重试"}
            yield self._event(AgentEvent(type="tool_error", content="工具暂时不可用，请稍后重试"))
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.call_id,
                "name": call.name,
                "content": serialize_tool_result(
                    result,
                    settings.agent_tool_result_max_chars,
                ),
            }
        )
