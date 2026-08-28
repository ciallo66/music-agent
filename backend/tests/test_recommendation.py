"""推荐接口测试。"""

from __future__ import annotations

from app.models.artist import Artist
from app.models.play_record import PlayRecord
from app.models.song import Song
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_recommendations_return_stable_empty_fallback(client: TestClient) -> None:
    """没有歌曲数据时推荐接口应返回稳定的空热门兜底结果。"""
    payload = {"username": "Recommend1", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "strategy": "popular_fallback"}


def test_record_play_validates_song_and_persists_record(
    client: TestClient, db_session: Session
) -> None:
    """播放记录接口应校验歌曲并写入当前用户行为。"""
    payload = {"username": "PlayRecord1", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]
    user = db_session.scalar(select(User).where(User.username == payload["username"]))
    assert user is not None
    artist = Artist(name="Play Artist")
    db_session.add(artist)
    db_session.flush()
    song = Song(title="Play Song", artist_id=artist.id)
    db_session.add(song)
    db_session.flush()

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/plays", json={"song_id": song.id}, headers=headers)
    missing = client.post("/api/v1/plays", json={"song_id": 999999}, headers=headers)

    assert response.status_code == 204
    assert missing.status_code == 404
    assert (
        db_session.scalar(
            select(PlayRecord).where(PlayRecord.user_id == user.id, PlayRecord.song_id == song.id)
        )
        is not None
    )
