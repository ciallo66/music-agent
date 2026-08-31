"""Jamendo 导入服务的字段清洗和客户端响应测试。"""

from __future__ import annotations

import httpx
import pytest
from app.models import Artist, Song
from app.services.jamendo_import_service import (
    JamendoClient,
    JamendoImportError,
    JamendoImportService,
    JamendoTrack,
    normalize_track,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_normalize_track_maps_musicinfo() -> None:
    """应提取 Jamendo 基础字段和音乐特征。"""
    track = normalize_track(
        {
            "id": "42",
            "name": "  Song  ",
            "artist_id": "7",
            "artist_name": "Artist",
            "album_name": "Album",
            "audio": "https://cdn.example/song.mp3",
            "duration": "123",
            "image": "https://cdn.example/artist.jpg",
            "musicinfo": {
                "tags": {"genres": ["Electronic"]},
                "melody": {"bpm": 120, "key": "C"},
                "energy": 0.8,
            },
        }
    )
    assert track is not None
    assert track.title == "Song"
    assert track.genre == "Electronic"
    assert track.duration == 123
    assert track.features["bpm"] == 120.0


def test_normalize_track_skips_missing_identity() -> None:
    """缺少稳定外部 ID 的记录不能进入数据库。"""
    assert normalize_track({"id": "1", "name": "No artist"}) is None


def test_client_validates_success_response(monkeypatch) -> None:
    """客户端应把成功响应转换为规范对象。"""
    from app.services import jamendo_import_service as module

    monkeypatch.setattr(module.settings, "jamendo_client_id", "test-client")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "headers": {"status": "success"},
                "results": [
                    {
                        "id": "1",
                        "name": "x",
                        "artist_id": "2",
                        "artist_name": "a",
                        "audio": "https://x",
                    }
                ],
            },
        )
    )
    client = JamendoClient(httpx.Client(transport=transport))
    try:
        result = client.fetch_tracks(offset=0, limit=100)
    finally:
        client.close()
    assert [item.source_id for item in result] == ["1"]


def test_client_retries_temporary_failure(monkeypatch) -> None:
    """限流或服务端故障时应按配置重试。"""
    from app.services import jamendo_import_service as module

    monkeypatch.setattr(module.settings, "jamendo_client_id", "test-client")
    monkeypatch.setattr(module.settings, "jamendo_max_retries", 1)
    monkeypatch.setattr(module.settings, "jamendo_retry_base_seconds", 0)
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            json={"headers": {"status": "success"}, "results": []},
        )

    client = JamendoClient(httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        page = client.fetch_page(offset=0, limit=100)
    finally:
        client.close()
    assert attempts == 2
    assert page.raw_count == 0


def test_client_preserves_api_failure_reason(monkeypatch) -> None:
    """业务失败响应应保留上游错误代码和原因，便于定位配置问题。"""
    from app.services import jamendo_import_service as module

    monkeypatch.setattr(module.settings, "jamendo_client_id", "test-client")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            request=request,
            json={
                "headers": {
                    "status": "failed",
                    "code": 11,
                    "error_message": "application suspended",
                },
                "results": [],
            },
        )
    )
    client = JamendoClient(httpx.Client(transport=transport))
    try:
        with pytest.raises(JamendoImportError, match="代码 11.*application suspended"):
            client.fetch_page(offset=0, limit=100)
    finally:
        client.close()


def test_import_service_is_idempotent(monkeypatch) -> None:
    """同一外部 ID 再次导入时应走更新而不是新增。"""
    from app.services import jamendo_import_service as module

    class FakeArtist:
        id: int = 10
        name: str = "Artist"
        avatar_url: str | None = None

    class FakeSong:
        pass

    artists: dict[str, FakeArtist] = {}
    songs: dict[str, FakeSong] = {}

    class FakeArtists:
        def __init__(self, db) -> None:
            del db

        def get_by_source_id(self, source: str, source_id: str):
            return artists.get(f"{source}:{source_id}")

        def create(self, name: str, avatar_url: str | None, **kwargs):
            artist = FakeArtist()
            artist.name = name
            artist.avatar_url = avatar_url
            artists[f"{kwargs['source']}:{kwargs['source_id']}"] = artist
            return artist

        def update(self, artist, values):
            for key, value in values.items():
                setattr(artist, key, value)
            return artist

    class FakeSongs:
        def __init__(self, db) -> None:
            del db

        def get_by_source_id(self, source: str, source_id: str):
            return songs.get(f"{source}:{source_id}")

        def create(self, values):
            song = FakeSong()
            songs[values["source"] + ":" + values["source_id"]] = song
            return song

        def update(self, song, values):
            del song, values

    monkeypatch.setattr(module, "ArtistRepository", FakeArtists)
    monkeypatch.setattr(module, "SongRepository", FakeSongs)
    track = JamendoTrack("1", "Song", "2", "Artist", None, "https://x", 1, None, None, {})
    service = JamendoImportService(object())
    first = service.import_tracks([track])
    second = service.import_tracks([track])
    assert (first.created, first.updated) == (1, 0)
    assert (second.created, second.updated) == (0, 1)


def test_bulk_import_100_rows_is_idempotent(db_session: Session) -> None:
    """独立测试库中重复导入 100 条时，第二次只能更新已有记录。"""
    tracks = [
        JamendoTrack(
            source_id=str(index),
            title=f"Song {index}",
            artist_source_id=str(index % 10),
            artist_name=f"Artist {index % 10}",
            album=None,
            audio_url=f"https://cdn.example/{index}.mp3",
            duration=180,
            genre="Electronic",
            avatar_url=None,
            features={},
        )
        for index in range(100)
    ]
    service = JamendoImportService(db_session)

    first = service.import_tracks(tracks)
    db_session.flush()
    second = service.import_tracks(tracks)
    db_session.flush()

    assert (first.created, first.updated, first.skipped) == (100, 0, 0)
    assert (second.created, second.updated, second.skipped) == (0, 100, 0)
    assert db_session.scalar(select(func.count()).select_from(Song)) == 100
    assert db_session.scalar(select(func.count()).select_from(Artist)) == 10
