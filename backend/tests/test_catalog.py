"""公开音乐目录和管理员维护接口测试。"""

from __future__ import annotations

from app.models.associations import PlaylistSong, SongTag
from app.models.play_record import PlayRecord
from app.models.playlist import Playlist
from app.models.tag import Tag
from app.services.auth_service import AuthService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _admin_headers(client: TestClient, db_session: Session, username: str) -> dict[str, str]:
    """创建管理员并返回认证请求头。"""
    AuthService(db_session).create_admin(username, "Abc123")
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": "Abc123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_artist(client: TestClient, headers: dict[str, str], name: str) -> int:
    """通过管理员接口创建歌手并返回主键。"""
    response = client.post("/api/v1/admin/artists", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_song(
    client: TestClient,
    headers: dict[str, str],
    artist_id: int,
    title: str,
    popularity: int,
    genre: str = "Pop",
    language: str = "en",
) -> int:
    """通过管理员接口创建歌曲并返回主键。"""
    response = client.post(
        "/api/v1/admin/songs",
        headers=headers,
        json={
            "title": title,
            "artist_id": artist_id,
            "genre": genre,
            "language": language,
            "duration": 180,
            "audio_url": f"https://example.com/{title}.mp3",
            "popularity": popularity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_public_catalog_supports_search_filter_sort_and_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    """公开歌曲列表应按规则搜索、筛选、排序和分页。"""
    headers = _admin_headers(client, db_session, "Catalog1")
    first_artist = _create_artist(client, headers, "Neon Echo")
    second_artist = _create_artist(client, headers, "Quiet Lake")
    _create_song(client, headers, first_artist, "Night Drive", 80, "Synthpop", "en")
    _create_song(client, headers, first_artist, "Morning Light", 20, "Pop", "en")
    _create_song(client, headers, second_artist, "Silent Rain", 60, "Ambient", "zh")

    first_page = client.get("/api/v1/songs", params={"page_size": 2})
    artist_search = client.get("/api/v1/songs", params={"q": "neon"})
    filtered = client.get("/api/v1/songs", params={"genre": "ambient", "language": "ZH"})

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert [item["title"] for item in first_page.json()["items"]] == [
        "Night Drive",
        "Silent Rain",
    ]
    assert artist_search.json()["total"] == 2
    assert filtered.json()["items"][0]["title"] == "Silent Rain"


def test_song_genres_endpoint_returns_distinct_values(
    client: TestClient,
    db_session: Session,
) -> None:
    """风格列表接口应返回去重取值并按歌曲数量降序，且不会被当成歌曲 ID。"""
    headers = _admin_headers(client, db_session, "GenreList")
    artist_id = _create_artist(client, headers, "Genre Artist")
    _create_song(client, headers, artist_id, "Track A", 50, "摇滚")
    _create_song(client, headers, artist_id, "Track B", 30, "摇滚")
    _create_song(client, headers, artist_id, "Track C", 40, "爵士")

    response = client.get("/api/v1/songs/genres")

    assert response.status_code == 200
    # 摇滚出现 2 次，应排在爵士之前
    assert response.json() == ["摇滚", "爵士"]


def test_public_song_and_artist_details_return_not_found(client: TestClient) -> None:
    """不存在的公开资源应返回404。"""
    assert client.get("/api/v1/songs/999999").status_code == 404
    assert client.get("/api/v1/artists/999999").status_code == 404


def test_regular_user_cannot_manage_catalog(client: TestClient) -> None:
    """普通用户即使已登录也不能写入音乐目录。"""
    payload = {"username": "Catalog2", "password": "Abc123"}
    client.post("/api/v1/auth/register", json=payload)
    login = client.post("/api/v1/auth/login", json=payload)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post("/api/v1/admin/artists", json={"name": "Denied"}, headers=headers)

    assert response.status_code == 403


def test_catalog_payloads_are_validated(client: TestClient, db_session: Session) -> None:
    """管理员写入应拒绝空名称、非法URL和空更新。"""
    headers = _admin_headers(client, db_session, "Catalog3")
    artist_id = _create_artist(client, headers, "Valid Artist")

    bad_artist = client.post("/api/v1/admin/artists", json={"name": "   "}, headers=headers)
    bad_song = client.post(
        "/api/v1/admin/songs",
        headers=headers,
        json={"title": "Song", "artist_id": artist_id, "audio_url": "file:///music.mp3"},
    )
    empty_update = client.patch(f"/api/v1/admin/artists/{artist_id}", json={}, headers=headers)

    assert bad_artist.status_code == 422
    assert bad_song.status_code == 422
    assert empty_update.status_code == 422


def test_song_requires_existing_artist(client: TestClient, db_session: Session) -> None:
    """新增歌曲引用不存在的歌手时应返回404。"""
    headers = _admin_headers(client, db_session, "Catalog4")

    response = client.post(
        "/api/v1/admin/songs",
        headers=headers,
        json={
            "title": "Orphan Song",
            "artist_id": 999999,
            "audio_url": "https://example.com/orphan.mp3",
        },
    )

    assert response.status_code == 404


def test_artist_with_songs_cannot_be_deleted(client: TestClient, db_session: Session) -> None:
    """仍有关联歌曲的歌手应返回409而不是级联删除。"""
    headers = _admin_headers(client, db_session, "Catalog5")
    artist_id = _create_artist(client, headers, "Protected Artist")
    song_id = _create_song(client, headers, artist_id, "Protected Song", 1)

    response = client.delete(f"/api/v1/admin/artists/{artist_id}", headers=headers)

    assert response.status_code == 409
    assert client.get(f"/api/v1/songs/{song_id}").status_code == 200


def test_deleting_song_cleans_associated_records(
    client: TestClient,
    db_session: Session,
) -> None:
    """删除歌曲应同步清理歌单、标签和播放记录关联。"""
    headers = _admin_headers(client, db_session, "Catalog6")
    artist_id = _create_artist(client, headers, "Cleanup Artist")
    song_id = _create_song(client, headers, artist_id, "Cleanup Song", 1)
    admin = AuthService(db_session).get_user_from_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )
    playlist = Playlist(user_id=admin.id, name="Cleanup List", description=None)
    tag = Tag(name="cleanup-tag")
    db_session.add_all([playlist, tag])
    db_session.flush()
    db_session.add_all(
        [
            PlaylistSong(playlist_id=playlist.id, song_id=song_id, position=0),
            SongTag(song_id=song_id, tag_id=tag.id),
            PlayRecord(user_id=admin.id, song_id=song_id),
        ]
    )
    db_session.commit()

    response = client.delete(f"/api/v1/admin/songs/{song_id}", headers=headers)

    assert response.status_code == 204
    assert (
        db_session.scalar(
            select(func.count()).select_from(PlaylistSong).where(PlaylistSong.song_id == song_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(SongTag).where(SongTag.song_id == song_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(PlayRecord).where(PlayRecord.song_id == song_id)
        )
        == 0
    )
