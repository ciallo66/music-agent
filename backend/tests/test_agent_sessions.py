"""Agent 历史会话接口测试：列表、读取、删除与越权隔离。"""

from __future__ import annotations

from app.models.chat import ChatMessage, ChatSession
from app.repositories.chat_repository import ChatRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录测试用户，返回带令牌的请求头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _user_id(client: TestClient, headers: dict[str, str]) -> int:
    """读取当前登录用户主键。"""
    return int(client.get("/api/v1/auth/me", headers=headers).json()["id"])


def _seed_session(db: Session, user_id: int, question: str, answer: str) -> int:
    """造一段会话：一条用户消息 + 一条助手回复。"""
    chats = ChatRepository(db)
    session = chats.create_session(user_id)
    chats.add_message(session.id, "user", question)
    chats.add_message(session.id, "assistant", answer)
    db.commit()
    return session.id


def test_sessions_are_listed_with_title_and_counts(client: TestClient, db_session: Session) -> None:
    """列表按最近活跃倒序，标题取首条用户消息，并带上消息条数。"""
    headers = _auth_headers(client, "ChatUser1")
    user_id = _user_id(client, headers)
    first = _seed_session(db_session, user_id, "第一个问题", "第一个回答")
    second = _seed_session(db_session, user_id, "第二个问题", "第二个回答")

    response = client.get("/api/v1/agent/sessions", headers=headers)

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [second, first]
    assert items[0]["title"] == "第二个问题"
    assert items[0]["message_count"] == 2
    assert items[0]["last_message_id"] is not None


def test_session_detail_returns_messages_in_order(client: TestClient, db_session: Session) -> None:
    """详情按写入顺序返回 user / assistant 消息，供刷新后恢复。"""
    headers = _auth_headers(client, "ChatUser2")
    user_id = _user_id(client, headers)
    session_id = _seed_session(db_session, user_id, "问题", "回答")

    response = client.get(f"/api/v1/agent/sessions/{session_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == session_id
    assert [(item["role"], item["content"]) for item in body["messages"]] == [
        ("user", "问题"),
        ("assistant", "回答"),
    ]


def test_other_users_session_is_not_readable(client: TestClient, db_session: Session) -> None:
    """别人的会话读不到也删不掉，统一 404。"""
    owner_headers = _auth_headers(client, "ChatOwner")
    owner_id = _user_id(client, owner_headers)
    session_id = _seed_session(db_session, owner_id, "私密问题", "私密回答")

    intruder_headers = _auth_headers(client, "ChatIntruder")
    read = client.get(f"/api/v1/agent/sessions/{session_id}", headers=intruder_headers)
    delete = client.delete(f"/api/v1/agent/sessions/{session_id}", headers=intruder_headers)
    listing = client.get("/api/v1/agent/sessions", headers=intruder_headers)

    assert read.status_code == 404
    assert delete.status_code == 404
    assert listing.json() == []
    # 原会话仍在
    assert db_session.scalar(select(func.count()).select_from(ChatSession)) == 1


def test_delete_session_removes_messages(client: TestClient, db_session: Session) -> None:
    """删除会话后消息一并清理，列表里不再出现。"""
    headers = _auth_headers(client, "ChatUser3")
    user_id = _user_id(client, headers)
    session_id = _seed_session(db_session, user_id, "待删除", "回答")

    response = client.delete(f"/api/v1/agent/sessions/{session_id}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/api/v1/agent/sessions/{session_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/agent/sessions", headers=headers).json() == []
    assert db_session.scalar(select(func.count()).select_from(ChatMessage)) == 0


def test_sessions_require_authentication(client: TestClient, db_session: Session) -> None:
    """未登录时不能读历史会话。"""
    headers = _auth_headers(client, "ChatUser4")
    user_id = _user_id(client, headers)
    session_id = _seed_session(db_session, user_id, "问题", "回答")

    assert client.get("/api/v1/agent/sessions").status_code == 401
    assert client.get(f"/api/v1/agent/sessions/{session_id}").status_code == 401


def test_session_without_user_message_has_null_title(
    client: TestClient, db_session: Session
) -> None:
    """只有助手消息的会话标题为 null，由前端显示兜底文案。"""
    headers = _auth_headers(client, "ChatUser5")
    user_id = _user_id(client, headers)
    chats = ChatRepository(db_session)
    session = chats.create_session(user_id)
    chats.add_message(session.id, "assistant", "只有回复")
    db_session.commit()

    items = client.get("/api/v1/agent/sessions", headers=headers).json()

    assert items[0]["title"] is None
    assert items[0]["message_count"] == 1
