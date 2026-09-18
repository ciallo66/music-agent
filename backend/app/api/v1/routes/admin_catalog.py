"""管理员歌曲和歌手维护路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_real_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.catalog import (
    ArtistCreate,
    ArtistResponse,
    ArtistUpdate,
    SongCreate,
    SongDetail,
    SongUpdate,
)
from app.services.catalog_service import (
    ArtistHasSongsError,
    ArtistNotFoundError,
    CatalogService,
    SongNotFoundError,
)

router = APIRouter()


@router.post("/artists", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED)
def create_artist(
    payload: ArtistCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> ArtistResponse:
    """创建歌手，仅管理员可用。"""
    return CatalogService(db).create_artist(payload)


@router.patch("/artists/{artist_id}", response_model=ArtistResponse)
def update_artist(
    artist_id: int,
    payload: ArtistUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> ArtistResponse:
    """局部更新歌手，仅管理员可用。"""
    try:
        return CatalogService(db).update_artist(artist_id, payload)
    except ArtistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌手不存在") from error


@router.delete("/artists/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(
    artist_id: int,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> Response:
    """删除没有歌曲的歌手，仅管理员可用。"""
    try:
        CatalogService(db).delete_artist(artist_id)
    except ArtistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌手不存在") from error
    except ArtistHasSongsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="歌手仍有关联歌曲，不能删除",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/songs", response_model=SongDetail, status_code=status.HTTP_201_CREATED)
def create_song(
    payload: SongCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> SongDetail:
    """创建歌曲，仅管理员可用。"""
    try:
        return CatalogService(db).create_song(payload)
    except ArtistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌手不存在") from error


@router.patch("/songs/{song_id}", response_model=SongDetail)
def update_song(
    song_id: int,
    payload: SongUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> SongDetail:
    """局部更新歌曲，仅管理员可用。"""
    try:
        return CatalogService(db).update_song(song_id, payload)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    except ArtistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌手不存在") from error


@router.delete("/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(
    song_id: int,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> Response:
    """清理关联并删除歌曲，仅管理员可用。"""
    try:
        CatalogService(db).delete_song(song_id)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
