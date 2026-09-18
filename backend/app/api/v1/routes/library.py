"""当前用户歌单与收藏路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import block_demo_writes, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.library import (
    FavoriteItem,
    FavoritePage,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItem,
    PlaylistPage,
    PlaylistUpdate,
    SongReference,
)
from app.services.library_service import (
    DuplicateRelationError,
    LibraryService,
    PlaylistNotFoundError,
    RelationNotFoundError,
    SongNotFoundError,
)

router = APIRouter()


@router.get("/playlists", response_model=PlaylistPage)
def list_playlists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlaylistPage:
    """列出当前用户歌单。"""
    return LibraryService(db).list_playlists(current_user.id)


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(
    playlist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlaylistDetail:
    """读取当前用户歌单详情。"""
    try:
        return LibraryService(db).get_playlist(playlist_id, current_user.id)
    except PlaylistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌单不存在") from error


@router.post("/playlists", response_model=PlaylistItem, status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PlaylistCreate,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> PlaylistItem:
    """创建当前用户歌单。"""
    return LibraryService(db).create_playlist(current_user.id, payload)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistItem)
def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> PlaylistItem:
    """修改当前用户歌单。"""
    try:
        return LibraryService(db).update_playlist(playlist_id, current_user.id, payload)
    except PlaylistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌单不存在") from error


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: int,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """删除当前用户歌单。"""
    try:
        LibraryService(db).delete_playlist(playlist_id, current_user.id)
    except PlaylistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌单不存在") from error


@router.post("/playlists/{playlist_id}/songs", status_code=status.HTTP_204_NO_CONTENT)
def add_playlist_song(
    playlist_id: int,
    payload: SongReference,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """向当前用户歌单添加歌曲。"""
    try:
        LibraryService(db).add_playlist_song(playlist_id, current_user.id, payload.song_id)
    except PlaylistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌单不存在") from error
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    except DuplicateRelationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="歌曲已在歌单中"
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/playlists/{playlist_id}/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_playlist_song(
    playlist_id: int,
    song_id: int,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """从当前用户歌单删除歌曲。"""
    try:
        LibraryService(db).remove_playlist_song(playlist_id, current_user.id, song_id)
    except (PlaylistNotFoundError, RelationNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="歌单或歌曲不存在"
        ) from error


@router.get("/favorites", response_model=FavoritePage)
def list_favorites(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FavoritePage:
    """列出当前用户收藏。"""
    return LibraryService(db).list_favorites(current_user.id)


@router.post("/favorites", response_model=FavoriteItem, status_code=status.HTTP_201_CREATED)
def add_favorite(
    payload: SongReference,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> FavoriteItem:
    """收藏歌曲。"""
    try:
        return LibraryService(db).add_favorite(current_user.id, payload.song_id)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error
    except DuplicateRelationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="歌曲已收藏") from error


@router.delete("/favorites/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    song_id: int,
    current_user: Annotated[User, Depends(block_demo_writes)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """取消收藏歌曲。"""
    try:
        LibraryService(db).remove_favorite(current_user.id, song_id)
    except RelationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="收藏不存在") from error
