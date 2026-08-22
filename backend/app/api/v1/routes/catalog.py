"""公开歌曲和歌手目录路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.catalog import ArtistPage, ArtistResponse, SongDetail, SongPage
from app.services.catalog_service import ArtistNotFoundError, CatalogService, SongNotFoundError

router = APIRouter()


@router.get("/songs", response_model=SongPage)
def list_songs(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    genre: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    language: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    artist_id: Annotated[int | None, Query(gt=0)] = None,
) -> SongPage:
    """分页搜索和筛选公开歌曲。"""
    return CatalogService(db).list_songs(page, page_size, q, genre, language, artist_id)


@router.get("/songs/{song_id}", response_model=SongDetail)
def read_song(song_id: int, db: Annotated[Session, Depends(get_db)]) -> SongDetail:
    """读取公开歌曲详情。"""
    try:
        return CatalogService(db).get_song(song_id)
    except SongNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌曲不存在") from error


@router.get("/artists", response_model=ArtistPage)
def list_artists(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> ArtistPage:
    """分页搜索公开歌手。"""
    return CatalogService(db).list_artists(page, page_size, q)


@router.get("/artists/{artist_id}", response_model=ArtistResponse)
def read_artist(artist_id: int, db: Annotated[Session, Depends(get_db)]) -> ArtistResponse:
    """读取公开歌手详情。"""
    try:
        return CatalogService(db).get_artist(artist_id)
    except ArtistNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌手不存在") from error
