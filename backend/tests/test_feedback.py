"""推荐反馈接口测试。"""

from __future__ import annotations

from app.models.artist import Artist
from app.models.song import Song
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PASSWORD = "Abc123"


def _login(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录，返回可直接使用的认证头。"""
    payload = {"username": username, "password": PASSWORD}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_song(db_session: Session, title: str) -> int:
    """直接落库造一首歌，返回主键。"""
    artist = Artist(name=f"{title} Artist")
    db_session.add(artist)
    db_session.flush()
    song = Song(title=title, artist_id=artist.id, popularity=1)
    db_session.add(song)
    db_session.flush()
    return song.id


def test_feedback_endpoints_require_authentication(client: TestClient) -> None:
    """未登录访问反馈接口应被拒绝。"""
    assert client.get("/api/v1/feedback/actions").status_code == 401
    assert client.get("/api/v1/feedback/stats").status_code == 401
    assert client.post("/api/v1/feedback", json={"song_id": 1, "action": "like"}).status_code == 401


def test_list_feedback_actions_returns_full_catalog(client: TestClient) -> None:
    """反馈类型列表应按服务定义顺序返回全部动作。"""
    headers = _login(client, "FeedbackActions1")

    response = client.get("/api/v1/feedback/actions", headers=headers)

    assert response.status_code == 200
    actions = [item["action"] for item in response.json()]
    assert actions == ["like", "dislike", "seen", "similar", "less"]


def test_create_feedback_updates_stats(client: TestClient, db_session: Session) -> None:
    """记录反馈后统计应同步更新。"""
    headers = _login(client, "FeedbackCreate1")
    song_id = _create_song(db_session, "Feedback Song")

    created = client.post(
        "/api/v1/feedback", json={"song_id": song_id, "action": "like"}, headers=headers
    )

    assert created.status_code == 201
    assert created.json()["action"] == "like"

    stats = client.get("/api/v1/feedback/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json() == {
        "total": 1,
        "liked_count": 1,
        "disliked_count": 0,
        "seen_count": 0,
    }


def test_create_feedback_rejects_unknown_action(client: TestClient, db_session: Session) -> None:
    """未定义的反馈类型应返回 422。"""
    headers = _login(client, "FeedbackAction2")
    song_id = _create_song(db_session, "Unknown Action Song")

    response = client.post(
        "/api/v1/feedback",
        json={"song_id": song_id, "action": "not-an-action"},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_feedback_rejects_missing_song(client: TestClient) -> None:
    """对不存在的歌曲提交反馈应返回 404。"""
    headers = _login(client, "FeedbackMissing1")

    response = client.post(
        "/api/v1/feedback", json={"song_id": 999999, "action": "like"}, headers=headers
    )

    assert response.status_code == 404


def test_delete_feedback_removes_record(client: TestClient, db_session: Session) -> None:
    """删除反馈后统计应归零。"""
    headers = _login(client, "FeedbackDelete1")
    song_id = _create_song(db_session, "Delete Feedback Song")
    client.post("/api/v1/feedback", json={"song_id": song_id, "action": "like"}, headers=headers)

    deleted = client.delete(f"/api/v1/feedback/{song_id}", headers=headers)

    assert deleted.status_code == 204
    assert client.get("/api/v1/feedback/stats", headers=headers).json()["total"] == 0


def test_delete_missing_feedback_returns_not_found(
    client: TestClient,
    db_session: Session,
) -> None:
    """删除并不存在的反馈应返回 404。"""
    headers = _login(client, "FeedbackDelete2")
    song_id = _create_song(db_session, "No Feedback Song")

    response = client.delete(f"/api/v1/feedback/{song_id}", headers=headers)

    assert response.status_code == 404


def test_feedback_stats_are_isolated_per_user(
    client: TestClient,
    db_session: Session,
) -> None:
    """用户之间不应看到彼此的反馈统计。"""
    first = _login(client, "FeedbackIso1")
    second = _login(client, "FeedbackIso2")
    song_id = _create_song(db_session, "Isolated Song")

    client.post("/api/v1/feedback", json={"song_id": song_id, "action": "dislike"}, headers=first)

    assert client.get("/api/v1/feedback/stats", headers=first).json()["total"] == 1
    assert client.get("/api/v1/feedback/stats", headers=second).json()["total"] == 0
