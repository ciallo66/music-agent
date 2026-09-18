"""Agent 对话路由。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import block_demo_writes
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import AgentMessage, ToolConfirmationRequest
from app.services.agent.service import (
    AgentConfirmationError,
    AgentService,
    AgentSessionNotFoundError,
)

router = APIRouter()


def _sse(stream: Iterator[str], session_id: int) -> StreamingResponse:
    """把 Agent 事件生成器包装成 SSE 响应。"""
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": str(session_id),
        },
    )


@router.post("/agent/chat")
def chat(
    payload: AgentMessage,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """通过 SSE 流式返回 Agent 事件。

    对话本身会写入会话与消息表，并且本轮可能产生写工具调用，因此演示账号同样只读。
    """
    service = AgentService(db, current_user.id)
    try:
        conversation = service.get_or_create_conversation(payload.session_id)
    except AgentSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在") from error
    return _sse(service.stream(conversation, payload.message), conversation.session_id)


@router.post("/agent/confirmations")
def confirm(
    payload: ToolConfirmationRequest,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """按用户决定处理待确认工具调用，并继续会话的 SSE 流。

    确认流程是写工具真正落库的入口，演示账号必须在这里被拦住。
    """
    service = AgentService(db, current_user.id)
    try:
        conversation = service.get_or_create_conversation(payload.session_id)
    except AgentSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在") from error
    try:
        stream = service.confirm(conversation, payload.decisions)
    except AgentConfirmationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _sse(stream, conversation.session_id)
