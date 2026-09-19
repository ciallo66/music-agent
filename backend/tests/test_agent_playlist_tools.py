"""Agent 歌单写入能力测试：列出歌单、把歌曲加入歌单。

覆盖契约：
- 两个工具都注册成功，写工具必须经过用户确认；
- 未确认不落库，确认后才真正写进 playlist_songs；
- 歌单不存在 / 不属于当前用户 / 歌曲不存在 / 重复加入，都给出可读原因；
- 加入歌单只影响目标歌单，不动别人的数据。
"""

from __future__ import annotations

import json
from typing import Any

from app.core.security import hash_password
from app.models.artist import Artist
from app.models.associations import PlaylistSong
from app.models.playlist import Playlist
from app.models.song import Song
from app.models.user import User, UserRole, UserStatus
from app.services.agent.music_tools import AgentToolError, MusicAgentTools
from app.services.agent.policy import ToolDecision, evaluate_tool_call
from app.services.agent.provider import (
    DeepSeekProvider,
    ModelResponse,
    ModelStreamUpdate,
    ToolCall,
)
from app.services.agent.registry import ToolOperation, ToolRegistry
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """注册并登录测试用户，返回带令牌的请求头。"""
    payload = {"username": username, "password": "Abc123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _current_user_id(client: TestClient, headers: dict[str, str]) -> int:
    """读取当前登录用户主键，用于核对落库归属。"""
    return int(client.get("/api/v1/auth/me", headers=headers).json()["id"])


def _make_song(db: Session, title: str) -> Song:
    """造一首可加入歌单的歌曲。"""
    artist = Artist(name=f"{title} 的歌手", avatar_url=None)
    db.add(artist)
    db.flush()
    song = Song(
        title=title,
        artist_id=artist.id,
        album=None,
        genre="Pop",
        language=None,
        duration=180,
        audio_url=None,
        lyrics=None,
        popularity=0,
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


def _make_playlist(db: Session, user_id: int, name: str) -> Playlist:
    """造一个属于指定用户的歌单。"""
    playlist = Playlist(user_id=user_id, name=name, description=None)
    db.add(playlist)
    db.flush()
    return playlist


def _make_user(db: Session, username: str) -> User:
    """直接建库账户，供不经 HTTP 的工具级测试使用。"""
    user = User(
        username=username,
        password_hash=hash_password("Abc123"),
        role=UserRole.USER.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _song_titles(db: Session, playlist_id: int) -> list[str]:
    """读取歌单内歌曲标题，按加入顺序。"""
    statement = (
        select(Song.title)
        .join(PlaylistSong, PlaylistSong.song_id == Song.id)
        .where(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position)
    )
    return list(db.scalars(statement))


def _patch_stream(monkeypatch: Any, tool_call: ToolCall) -> None:
    """让模型首轮要求一次工具调用，之后返回最终文本。"""
    calls = 0

    def fake_stream(
        _provider: DeepSeekProvider,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]],
    ) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            yield ModelStreamUpdate(response=ModelResponse(None, [tool_call]))
            return
        yield ModelStreamUpdate(response=ModelResponse("已经处理完成。", []))

    monkeypatch.setattr(DeepSeekProvider, "stream", fake_stream)


def _confirmation_id(response: Any) -> int:
    """从 SSE 响应中取出待确认编号。"""
    marker = "event: confirmation_required\ndata: "
    raw_event = response.text.split(marker, 1)[1].split("\n", 1)[0]
    return int(json.loads(json.loads(raw_event)["content"])["confirmation_id"])


def _decide(client: TestClient, headers: dict[str, str], response: Any, approved: bool) -> Any:
    """按待确认编号提交决定，并返回继续后的响应。"""
    session_id = int(response.headers["X-Session-Id"])
    return client.post(
        "/api/v1/agent/confirmations",
        json={
            "session_id": session_id,
            "decisions": [{"confirmation_id": _confirmation_id(response), "approved": approved}],
        },
        headers=headers,
    )


def test_playlist_tools_are_registered_with_expected_operation(db_session: Session) -> None:
    """list_playlists 只读、add_songs_to_playlist 写操作且需确认。"""
    registry = ToolRegistry()
    MusicAgentTools(db_session, user_id=1).register_all(registry)

    discover = registry.get("list_playlists")
    add = registry.get("add_songs_to_playlist")

    assert discover is not None
    assert discover.operation is ToolOperation.READ
    assert add is not None
    assert add.operation is ToolOperation.WRITE

    names = [item["function"]["name"] for item in registry.definitions()]
    assert "list_playlists" in names
    assert "add_songs_to_playlist" in names
    assert (
        evaluate_tool_call(add, {"playlist_id": 1, "song_ids": [1, 2]}).decision
        is ToolDecision.CONFIRM
    )
    assert evaluate_tool_call(discover, {}).decision is ToolDecision.ALLOW


def test_add_songs_requires_confirmation_before_persisting(
    db_session: Session, client: TestClient, monkeypatch: Any
) -> None:
    """模型提出加入歌单后先等确认，确认了才写进歌单。"""
    headers = _auth_headers(client, "ListUser1")
    user_id = _current_user_id(client, headers)
    playlist = _make_playlist(db_session, user_id, "通勤")
    song = _make_song(db_session, "曲目甲")
    _patch_stream(
        monkeypatch,
        ToolCall(
            "call-1",
            "add_songs_to_playlist",
            {"playlist_id": playlist.id, "song_ids": [song.id]},
        ),
    )

    first = client.post("/api/v1/agent/chat", json={"message": "加进歌单"}, headers=headers)

    assert "event: confirmation_required" in first.text
    assert _song_titles(db_session, playlist.id) == []

    second = _decide(client, headers, first, approved=True)

    assert second.status_code == 200
    assert _song_titles(db_session, playlist.id) == ["曲目甲"]
    assert "event: end" in second.text


def test_rejected_add_does_not_touch_playlist(
    db_session: Session, client: TestClient, monkeypatch: Any
) -> None:
    """用户拒绝后歌单保持原样。"""
    headers = _auth_headers(client, "ListUser2")
    user_id = _current_user_id(client, headers)
    playlist = _make_playlist(db_session, user_id, "别动")
    song = _make_song(db_session, "曲目乙")
    _patch_stream(
        monkeypatch,
        ToolCall(
            "call-2",
            "add_songs_to_playlist",
            {"playlist_id": playlist.id, "song_ids": [song.id]},
        ),
    )

    first = client.post("/api/v1/agent/chat", json={"message": "加进去"}, headers=headers)
    second = _decide(client, headers, first, approved=False)

    assert "event: tool_rejected" in second.text
    assert _song_titles(db_session, playlist.id) == []


def test_tool_lists_only_current_user_playlists(db_session: Session) -> None:
    """歌单列表只包含当前用户的歌单，不泄露别人数据。"""
    owner = _make_user(db_session, "ToolOwner1")
    other = _make_user(db_session, "ToolOwner2")
    mine = _make_playlist(db_session, owner.id, "我的歌单")
    _make_playlist(db_session, other.id, "别人的歌单")

    result = MusicAgentTools(db_session, user_id=owner.id).list_playlists({})

    assert [item["id"] for item in result["items"]] == [mine.id]
    assert result["count"] == 1


def test_tool_adds_multiple_songs_and_reports_duplicates(db_session: Session) -> None:
    """一次可加多首；已在歌单里的会单独报出来，不算失败。"""
    owner = _make_user(db_session, "ToolOwner3")
    playlist = _make_playlist(db_session, owner.id, "批量")
    first_song = _make_song(db_session, "批量甲")
    second_song = _make_song(db_session, "批量乙")
    tools = MusicAgentTools(db_session, user_id=owner.id)

    result = tools.add_songs_to_playlist(
        {"playlist_id": playlist.id, "song_ids": [first_song.id, second_song.id]}
    )
    again = tools.add_songs_to_playlist({"playlist_id": playlist.id, "song_ids": [first_song.id]})

    assert result["added_song_ids"] == [first_song.id, second_song.id]
    assert result["already_in_playlist"] == []
    assert result["playlist"]["song_count"] == 2
    assert again["added_song_ids"] == []
    assert again["already_in_playlist"] == [first_song.id]
    assert _song_titles(db_session, playlist.id) == ["批量甲", "批量乙"]


def test_tool_rejects_foreign_playlist_and_unknown_song(db_session: Session) -> None:
    """别人的歌单与不存在的歌曲都给出可读原因，且不落库。"""
    owner = _make_user(db_session, "ToolOwner4")
    other = _make_user(db_session, "ToolOwner5")
    others = _make_playlist(db_session, other.id, "别人的")
    song = _make_song(db_session, "曲目丙")
    tools = MusicAgentTools(db_session, user_id=owner.id)

    try:
        tools.add_songs_to_playlist({"playlist_id": others.id, "song_ids": [song.id]})
    except AgentToolError as error:
        assert "歌单" in str(error)
    else:  # pragma: no cover - 越权必须失败
        raise AssertionError("越权加入别人的歌单没有被拒绝")

    mine = _make_playlist(db_session, owner.id, "我的")
    try:
        tools.add_songs_to_playlist({"playlist_id": mine.id, "song_ids": [999_999]})
    except AgentToolError as error:
        assert "歌曲不存在" in str(error)
    else:  # pragma: no cover - 不存在的歌曲必须失败
        raise AssertionError("不存在的歌曲没有被拒绝")

    total = db_session.scalar(select(func.count()).select_from(PlaylistSong))
    assert total == 0
