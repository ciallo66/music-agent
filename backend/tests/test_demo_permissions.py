"""演示账号权限契约测试。

覆盖三类契约：
- 演示账号的**正常使用**（收藏、歌单、反馈、收听、对话）与普通账号一致，可以写入；
- 演示账号在**后台改数据**的入口上被拒绝（即使它有 admin 角色）；
- 用户名比较不区分大小写，且不会误伤名字近似的普通账号。
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


def _demo_admin_headers(client: TestClient, db: Session, monkeypatch: Any) -> dict[str, str]:
    """创建带 admin 角色的演示账号并登录，用于验证后台写入口的拦截。"""
    _use_demo_username(monkeypatch)
    _make_user(db, DEMO_USERNAME, role=UserRole.ADMIN)
    return _login(client, DEMO_USERNAME)


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


def test_demo_user_can_add_favorite(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号属于正常使用，收藏歌曲应当成功。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    song = _song(db_session)
    headers = _login(client, DEMO_USERNAME)

    response = client.post("/api/v1/favorites", headers=headers, json={"song_id": song.id})

    assert response.status_code == 201


def test_demo_user_can_use_library_feedback_and_plays(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号可以建歌单、提交反馈、记录收听——这些都属于正常功能。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, DEMO_USERNAME)
    song = _song(db_session)
    headers = _login(client, DEMO_USERNAME)

    playlist = client.post("/api/v1/playlists", headers=headers, json={"name": "演示歌单"})
    add_song = client.post(
        f"/api/v1/playlists/{playlist.json()['id']}/songs",
        headers=headers,
        json={"song_id": song.id},
    )
    feedback = client.post(
        "/api/v1/feedback", headers=headers, json={"song_id": song.id, "action": "like"}
    )
    play = client.post("/api/v1/plays", headers=headers, json={"song_id": song.id})

    assert playlist.status_code == 201
    assert add_song.status_code == 204
    assert feedback.status_code == 201
    assert play.status_code == 204


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


def test_demo_admin_can_read_admin_console(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号带 admin 角色时可以查看后台统计（只读）。"""
    headers = _demo_admin_headers(client, db_session, monkeypatch)

    overview = client.get("/api/v1/admin/overview", headers=headers)
    users = client.get("/api/v1/admin/users", headers=headers)

    assert overview.status_code == 200
    assert users.status_code == 200


def test_demo_admin_cannot_mutate_admin_data(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """演示账号在后台所有会改数据的入口上都必须被拒（403 + 可读提示）。"""
    headers = _demo_admin_headers(client, db_session, monkeypatch)
    song = _song(db_session)

    requests: list[tuple[str, str, dict[str, Any] | None]] = [
        ("post", "/api/v1/admin/artists", {"name": "演示歌手"}),
        ("delete", "/api/v1/admin/artists/1", None),
        ("post", "/api/v1/admin/songs", {"title": "演示歌曲", "artist_id": 1}),
        ("delete", f"/api/v1/admin/songs/{song.id}", None),
        ("patch", "/api/v1/admin/users/1", {"status": "disabled"}),
        ("post", "/api/v1/admin/imports/jamendo", {"limit": 1}),
    ]
    for method, url, payload in requests:
        response = client.request(method, url, headers=headers, json=payload)
        assert response.status_code == 403, f"{method.upper()} {url} 未被后台只读保护拦截"
        detail = response.json()["detail"]
        assert "只能查看" in detail and "不能修改" in detail


def test_plain_user_writes_are_not_blocked(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """普通账号的写操作不受影响。"""
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
    """配置为 Demo99 时，用户名 DEMO99 同样被判定为演示账号（后台写入口被拦）。"""
    _use_demo_username(monkeypatch, "Demo99")
    _make_user(db_session, "DEMO99", role=UserRole.ADMIN)
    headers = _login(client, "DEMO99")

    response = client.post("/api/v1/admin/artists", headers=headers, json={"name": "X"})

    assert response.status_code == 403
    assert "不能修改" in response.json()["detail"]


def test_similar_username_is_not_treated_as_demo(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """用户名只是包含演示账号名（Demo999）时不应被误判：后台写入口按角色判断。"""
    _use_demo_username(monkeypatch, "Demo99")
    _make_user(db_session, "Demo999", role=UserRole.ADMIN)
    headers = _login(client, "Demo999")

    response = client.post("/api/v1/admin/artists", headers=headers, json={"name": "真实管理员"})

    assert response.status_code == 201


def test_admin_write_still_requires_admin_role(
    client: TestClient, db_session: Session, monkeypatch: Any
) -> None:
    """普通账号访问后台写接口仍按管理员权限拒绝。"""
    _use_demo_username(monkeypatch)
    _make_user(db_session, PLAIN_USERNAME)
    headers = _login(client, PLAIN_USERNAME)

    response = client.post("/api/v1/admin/artists", headers=headers, json={"name": "X"})

    assert response.status_code == 403
