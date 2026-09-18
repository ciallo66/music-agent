"""演示账号只读保护测试。

覆盖三类契约：演示账号写操作被拒、演示账号读操作照常、普通账号写操作不受影响。
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.security import hash_password
from app.models.artist import Artist
from app.models.song import Song
from app.models.user import User, UserRole, UserStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PASSWORD = "Abcd1234"
DEMO_USERNAME = "Demo99"
PLAIN_USERNAME = "Plain99"


def _use_demo_username(monkeypatch: Any, username: str = DEMO_USERNAME) -> None:
    """把演示账号配置指向测试用用户名，避免污染真实配置。"""
    monkeypatch.setattr(settings, "demo_username", username)


def _make_user(db: Session, username: str, role: UserRole = UserRole.USER) -> User:
    """直接写库创建账号，避免依赖注册接口的额外校验。"""
    user = User(
        username=username,
        password_hash=hash_password(PASSWORD),
        role=role.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _login(client: TestClient, username: str) -> dict[str, str]:
    """以普通登录接口登录，返回认证头。"""
    response = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _song(db: Session) -> Song:
    """创建可供收藏接口引用的歌曲。"""
    artist = Artist(name="Demo Artist", avatar_url=None)
    db.add(artist)
    db.flush()
    song = Song(
        title="Demo Song",
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
    db.add(song)
    db.flush()
    return song


def test_demo_user_cannot_add_favorite(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号收藏歌曲应返回 403，且提示包含「只读」。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    song = _song(db_session)
    headers = _login(client, DEMO_USERNAME)

    response = client.post("/api/v1/favorites", headers=headers, json={"song_id": song.id})

    assert response.status_code == 403
    assert "只读" in response.json()["detail"]


def test_demo_user_can_read_catalog(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号读取公开歌曲目录应正常返回。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    _song(db_session)
    headers = _login(client, DEMO_USERNAME)

    response = client.get("/api/v1/songs", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_demo_user_can_read_own_library(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号读取自己的收藏与歌单列表应正常返回。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    headers = _login(client, DEMO_USERNAME)

    favorites = client.get("/api/v1/favorites", headers=headers)
    playlists = client.get("/api/v1/playlists", headers=headers)

    assert favorites.status_code == 200
    assert favorites.json()["items"] == []
    assert playlists.status_code == 200
    assert playlists.json()["items"] == []


def test_demo_user_write_endpoints_are_blocked(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号的各写入口（歌单、反馈、播放、Agent）都应返回 403。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    song = _song(db_session)
    headers = _login(client, DEMO_USERNAME)

    requests: list[tuple[str, str, dict[str, Any] | None]] = [
        ("post", "/api/v1/playlists", {"name": "演示歌单"}),
        ("patch", "/api/v1/playlists/1", {"name": "改名"}),
        ("delete", "/api/v1/playlists/1", None),
        ("post", "/api/v1/playlists/1/songs", {"song_id": song.id}),
        ("delete", f"/api/v1/playlists/1/songs/{song.id}", None),
        ("delete", f"/api/v1/favorites/{song.id}", None),
        ("post", "/api/v1/feedback", {"song_id": song.id, "action": "like"}),
        ("delete", f"/api/v1/feedback/{song.id}", None),
        ("post", "/api/v1/plays", {"song_id": song.id}),
        ("post", "/api/v1/agent/chat", {"message": "帮我看歌"}),
        (
            "post",
            "/api/v1/agent/confirmations",
            {"session_id": 1, "decisions": [{"confirmation_id": 1, "approved": True}]},
        ),
    ]
    for method, url, payload in requests:
        response = client.request(method, url, headers=headers, json=payload)
        assert response.status_code == 403, f"{method.upper()} {url} 未被只读保护拦截"
        assert "只读" in response.json()["detail"]


def test_plain_user_writes_are_not_blocked(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """普通账号的写操作不受演示账号保护影响。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, PLAIN_USERNAME)
    song = _song(db_session)
    headers = _login(client, PLAIN_USERNAME)

    favorite = client.post("/api/v1/favorites", headers=headers, json={"song_id": song.id})
    playlist = client.post("/api/v1/playlists", headers=headers, json={"name": "我的歌单"})

    assert favorite.status_code == 201
    assert playlist.status_code == 201


def test_username_comparison_is_case_insensitive(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """配置为 Demo99 时，用户名 DEMO99 同样被判定为演示账号。"""
    _use_demo_username(monkeypatch, "Demo99")
    _make_user(db_session, "DEMO99")
    song = _song(db_session)
    headers = _login(client, "DEMO99")

    response = client.post("/api/v1/favorites", headers=headers, json={"song_id": song.id})

    assert response.status_code == 403
    assert "只读" in response.json()["detail"]


def test_similar_username_is_not_treated_as_demo(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """用户名只是包含演示账号名（Demo999）时不应被误判。"""
    _use_demo_username(monkeypatch, "Demo99")
    _make_user(db_session, "Demo999")
    song = _song(db_session)
    headers = _login(client, "Demo999")

    response = client.post("/api/v1/favorites", headers=headers, json={"song_id": song.id})

    assert response.status_code == 201


def test_admin_write_still_requires_admin_role(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号不是管理员，后台写接口仍按管理员权限拒绝。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    headers = _login(client, DEMO_USERNAME)

    response = client.post("/api/v1/admin/artists", headers=headers, json={"name": "X"})

    assert response.status_code == 403
