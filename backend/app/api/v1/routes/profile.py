"""当前用户音乐画像路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import MusicProfileResponse
from app.services.profile_service import ProfileService

router = APIRouter()


@router.get("/me/music-profile", response_model=MusicProfileResponse)
def get_music_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MusicProfileResponse:
    """返回当前用户的音乐画像和听歌统计。"""
    return ProfileService(db).get_music_profile(current_user.id)
