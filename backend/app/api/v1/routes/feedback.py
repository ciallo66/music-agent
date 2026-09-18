"""推荐反馈路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import block_demo_writes, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.feedback import (
    FeedbackActionItem,
    FeedbackStats,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
)
from app.services.feedback_service import (
    FeedbackNotFoundError,
    FeedbackService,
    InvalidFeedbackActionError,
)
from app.services.recommendation_service import SongNotFoundError

router = APIRouter()


@router.get("/feedback/actions", response_model=list[FeedbackActionItem])
def list_feedback_actions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FeedbackActionItem]:
    """返回可用反馈类型。"""
    return FeedbackService(db).list_actions()


@router.post(
    "/feedback", response_model=RecommendationFeedbackResponse, status_code=status.HTTP_201_CREATED
)
def create_feedback(
    payload: RecommendationFeedbackCreate,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> RecommendationFeedbackResponse:
    """记录用户对推荐歌曲的反馈。"""
    service = FeedbackService(db)
    try:
        return service.record_feedback(current_user.id, payload)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    except InvalidFeedbackActionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.delete("/feedback/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(
    song_id: int,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """删除用户对某首歌的反馈。"""
    service = FeedbackService(db)
    try:
        service.remove_feedback(current_user.id, song_id)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/feedback/stats", response_model=FeedbackStats)
def get_feedback_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FeedbackStats:
    """返回当前用户的反馈汇总。"""
    return FeedbackService(db).get_stats(current_user.id)
