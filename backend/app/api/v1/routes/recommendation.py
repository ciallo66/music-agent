"""用户推荐路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.library import SongReference
from app.schemas.recommendation import RecommendationPage
from app.services.recommendation_service import RecommendationService, SongNotFoundError

router = APIRouter()


@router.get("/recommendations", response_model=RecommendationPage)
def list_recommendations(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> RecommendationPage:
    """返回当前用户的可解释推荐。"""
    user_id = current_user.id if current_user is not None else None
    return RecommendationService(db).recommend(user_id, limit)


@router.post("/plays", status_code=status.HTTP_204_NO_CONTENT)
def record_play(
    payload: SongReference,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """记录当前用户的一次播放行为，供推荐画像使用。"""
    try:
        RecommendationService(db).record_play(current_user.id, payload.song_id)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
