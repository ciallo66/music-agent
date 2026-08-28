"""用户歌单与收藏接口集成测试。"""

from __future__ import annotations

from app.models.artist import Artist
from app.models.song import Song
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册登录测试用户并返回认证头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _song(db_session: Session) -> Song:
    """创建可供业务接口引用的歌曲。"""
    artist = Artist(name="Library Artist", avatar_url=None)
    db_session.add(artist)
    db_session.flush()
    song = Song(
        title="Library Song",
        artist_id=artist.id,
        album=None,
        genre="Pop",
        language=None,
        duration=180,
        audio_url=None,
        lyrics=None,
        popularity=1,
        bpm=None,
        music_key=None,
        energy=None,
        valence=None,
        danceability=None,
        loudness=None,
        instruments=None,
        song_structure=None,
    )
    db_session.add(song)
    db_session.flush()
    return song


def test_playlist_lifecycle_and_user_isolation(client: TestClient, db_session: Session) -> None:
    """歌单应支持完整生命周期且不能被其他用户读取。"""
    song = _song(db_session)
    owner_headers = _auth_headers(client, "ListOwn1")
    create_response = client.post(
        "/api/v1/playlists",
        headers=owner_headers,
        json={"name": "通勤", "description": "早高峰"},
    )
    assert create_response.status_code == 201
    playlist_id = create_response.json()["id"]

    add_response = client.post(
        f"/api/v1/playlists/{playlist_id}/songs",
        headers=owner_headers,
        json={"song_id": song.id},
    )
    assert add_response.status_code == 204
    detail = client.get(f"/api/v1/playlists/{playlist_id}", headers=owner_headers)
    assert detail.status_code == 200
    assert detail.json()["song_count"] == 1
    assert detail.json()["songs"][0]["id"] == song.id

    other_headers = _auth_headers(client, "ListOth1")
    assert client.get(f"/api/v1/playlists/{playlist_id}", headers=other_headers).status_code == 404


def test_favorite_lifecycle_and_duplicate_conflict(client: TestClient, db_session: Session) -> None:
    """收藏应支持增删查询并拒绝重复记录。"""
    song = _song(db_session)
    headers = _auth_headers(client, "FavUser1")
    payload = {"song_id": song.id}

    first = client.post("/api/v1/favorites", headers=headers, json=payload)
    assert first.status_code == 201
    assert first.json()["song_id"] == song.id
    assert client.post("/api/v1/favorites", headers=headers, json=payload).status_code == 409

    listing = client.get("/api/v1/favorites", headers=headers)
    assert listing.status_code == 200
    assert [item["song_id"] for item in listing.json()["items"]] == [song.id]
    assert client.delete(f"/api/v1/favorites/{song.id}", headers=headers).status_code == 204
    assert client.get("/api/v1/favorites", headers=headers).json()["items"] == []
