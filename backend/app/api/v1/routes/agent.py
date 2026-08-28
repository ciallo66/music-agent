"""Agent 对话路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import AgentMessage
from app.services.agent.service import AgentService, AgentSessionNotFoundError

router = APIRouter()


@router.post("/agent/chat")
def chat(
    payload: AgentMessage,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """通过 SSE 流式返回 Agent 事件。"""
    service = AgentService(db, current_user.id)
    try:
        conversation = service.get_or_create_conversation(payload.session_id)
    except AgentSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在") from error
    stream = service.stream(conversation, payload.message)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": str(conversation.session_id),
        },
    )
