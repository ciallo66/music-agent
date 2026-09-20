"""后台列表筛选参数契约测试。

回归背景：管理后台的「曲目管理 / 歌手管理」打开时会带上空的筛选参数
（`q=`、`genre=`）。此前接口对 q 设了 min_length=1，空字符串直接 422，
前端把失败当空结果，于是**控制台曲目与歌手列表永远是空的**，
看起来像「服务器数据没了」。这里把「空参数=不过滤」钉成契约。
"""

from __future__ import annotations

from app.models.artist import Artist
from app.models.song import Song
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _seed(db: Session) -> Song:
    """造一位歌手与一首歌，供列表接口查询。"""
    artist = Artist(name="EmptyParamArtist", avatar_url=None)
    db.add(artist)
    db.flush()
    song = Song(
        title="EmptyParamSong",
        artist_id=artist.id,
        album="EmptyParamAlbum",
        genre="摇滚",
        language=None,
        duration=200,
        audio_url=None,
        lyrics=None,
        popularity=0,
        bpm=120.0,
        music_key="C",
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


def test_songs_list_accepts_empty_keyword_and_genre(
    client: TestClient, db_session: Session
) -> None:
    """空 q / 空 genre 表示不过滤，而不是 422。"""
    _seed(db_session)

    response = client.get(
        "/api/v1/songs", params={"q": "", "genre": "", "page": 1, "page_size": 20}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["title"] == "EmptyParamSong" for item in body["items"])


def test_artists_list_accepts_empty_keyword(client: TestClient, db_session: Session) -> None:
    """歌手列表同样接受空关键词。"""
    _seed(db_session)

    response = client.get("/api/v1/artists", params={"q": "", "page": 1, "page_size": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["name"] == "EmptyParamArtist" for item in body["items"])


def test_songs_list_still_filters_when_keyword_given(
    client: TestClient, db_session: Session
) -> None:
    """传了关键词仍然按关键词筛。"""
    _seed(db_session)

    hit = client.get("/api/v1/songs", params={"q": "EmptyParamSong"})
    miss = client.get("/api/v1/songs", params={"q": "根本不存在的歌名"})

    assert hit.status_code == 200
    assert hit.json()["total"] >= 1
    assert miss.status_code == 200
    assert miss.json()["total"] == 0
