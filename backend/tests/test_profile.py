"""用户音乐画像接口测试。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.artist import Artist
from app.models.favorite import Favorite
from app.models.play_record import PlayRecord
from app.models.song import Song
from app.models.user import User
from app.services.auth_service import AuthService
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_music_profile_aggregates_only_current_user_data(
    client: TestClient, db_session: Session
) -> None:
    """画像统计应返回当前用户数据，并包含分布、特征和最近播放。"""
    payload = {"username": "ProfileUser", "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["access_token"]
    user = db_session.scalar(select(User).where(User.username == payload["username"]))
    assert user is not None
    user_id = user.id
    other_user = AuthService(db_session).register("OtherProfile", "Abc123")

    artist = Artist(name="Profile Artist")
    other_artist = Artist(name="Other Artist")
    db_session.add_all([artist, other_artist])
    db_session.flush()
    first = Song(
        title="Profile One",
        artist_id=artist.id,
        genre="Jazz",
        bpm=100,
        energy=0.4,
        valence=0.3,
        danceability=0.5,
    )
    second = Song(
        title="Profile Two",
        artist_id=artist.id,
        genre="Jazz",
        bpm=120,
        energy=0.6,
        valence=0.5,
        danceability=0.7,
    )
    other = Song(title="Other Song", artist_id=other_artist.id, genre="Rock")
    db_session.add_all([first, second, other])
    db_session.flush()
    played_at = datetime.now(timezone.utc)
    db_session.add_all(
        [
            PlayRecord(user_id=user_id, song_id=first.id, played_at=played_at),
            PlayRecord(user_id=user_id, song_id=second.id, played_at=played_at),
            PlayRecord(user_id=user_id, song_id=first.id, played_at=played_at),
            PlayRecord(user_id=other_user.id, song_id=other.id, played_at=played_at),
        ]
    )
    db_session.add(Favorite(user_id=user_id, song_id=first.id))
    db_session.flush()

    response = client.get(
        "/api/v1/me/music-profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_plays"] == 3
    assert body["unique_songs"] == 2
    assert body["favorite_count"] == 1
    assert body["preferred_genres"] == ["Jazz"]
    assert body["feature_profile"]["average_bpm"] == 110.0
    assert body["genre_distribution"] == [{"name": "Jazz", "count": 3}]
    assert body["top_artists"] == [{"name": "Profile Artist", "count": 3}]
    assert len(body["play_trend"]) == 1
    assert len(body["recent_plays"]) == 3


def test_music_profile_requires_authentication(client: TestClient) -> None:
    """未登录用户不能访问音乐画像。"""
    assert client.get("/api/v1/me/music-profile").status_code == 401
