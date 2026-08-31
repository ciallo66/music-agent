"""Jamendo 元数据抓取、清洗和幂等写入。"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.catalog_repository import ArtistRepository, SongRepository

JAMENDO_SOURCE = "jamendo"


class JamendoImportError(RuntimeError):
    """Jamendo 响应无效或配置不完整。"""


@dataclass(frozen=True)
class JamendoTrack:
    """经过字段清洗后的 Jamendo 歌曲。"""

    source_id: str
    title: str
    artist_source_id: str
    artist_name: str
    album: str | None
    audio_url: str | None
    duration: int | None
    genre: str | None
    avatar_url: str | None
    features: dict[str, Any]


@dataclass
class ImportReport:
    """一次导入执行的统计结果。"""

    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failure_reasons: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class JamendoPage:
    """Jamendo 一页原始数量、有效歌曲和清洗失败统计。"""

    raw_count: int
    tracks: list[JamendoTrack]
    failure_reasons: dict[str, int]


class JamendoClient:
    """访问 Jamendo tracks API，并校验响应结构。"""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=settings.jamendo_timeout_seconds)
        self._owns_client = client is None

    def close(self) -> None:
        """关闭内部 HTTP 客户端。"""
        if self._owns_client:
            self._client.close()

    def fetch_page(self, *, offset: int, limit: int) -> JamendoPage:
        """分页读取歌曲并保留原始数量和清洗失败原因。"""
        if not settings.jamendo_client_id:
            raise JamendoImportError("未配置 JAMENDO_CLIENT_ID，无法抓取 Jamendo 数据")
        response = self._request_with_retry(offset=offset, limit=limit)
        try:
            payload = response.json()
        except ValueError as error:
            raise JamendoImportError("Jamendo 返回的内容不是合法 JSON") from error
        headers = payload.get("headers") if isinstance(payload, Mapping) else None
        if not isinstance(headers, Mapping):
            raise JamendoImportError("Jamendo 响应缺少 headers 对象")
        if headers.get("status") != "success":
            raise JamendoImportError(_api_error_message(headers))
        results = payload.get("results")
        if not isinstance(results, list):
            raise JamendoImportError("Jamendo 响应缺少 results 数组")
        tracks: list[JamendoTrack] = []
        reasons: Counter[str] = Counter()
        for item in results:
            track, reason = normalize_track_result(item)
            if track is not None:
                tracks.append(track)
            elif reason is not None:
                reasons[reason] += 1
        return JamendoPage(
            raw_count=len(results),
            tracks=tracks,
            failure_reasons=dict(reasons),
        )

    def fetch_tracks(self, *, offset: int, limit: int) -> list[JamendoTrack]:
        """兼容脚本和既有调用，只返回有效歌曲。"""
        return self.fetch_page(offset=offset, limit=limit).tracks

    def _request_with_retry(self, *, offset: int, limit: int) -> httpx.Response:
        """对网络错误、限流和服务端错误执行指数退避重试。"""
        last_error: Exception | None = None
        for attempt in range(settings.jamendo_max_retries + 1):
            try:
                response = self._client.get(
                    f"{settings.jamendo_base_url.rstrip('/')}/tracks",
                    params={
                        "client_id": settings.jamendo_client_id,
                        "format": "json",
                        "include": "musicinfo",
                        "offset": offset,
                        "limit": min(limit, 200),
                    },
                )
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response
                last_error = httpx.HTTPStatusError(
                    "Jamendo 暂时不可用",
                    request=response.request,
                    response=response,
                )
            except httpx.RequestError as error:
                last_error = error
            if attempt < settings.jamendo_max_retries:
                time.sleep(settings.jamendo_retry_base_seconds * (2**attempt))
        raise JamendoImportError(f"Jamendo 请求重试后仍失败：{last_error}") from last_error


def normalize_track(item: object) -> JamendoTrack | None:
    """将 Jamendo 原始记录转换为可入库字段；缺少关键 ID 的记录跳过。"""
    return normalize_track_result(item)[0]


def normalize_track_result(item: object) -> tuple[JamendoTrack | None, str | None]:
    """转换单条记录，并返回稳定的失败原因代码。"""
    if not isinstance(item, Mapping):
        return None, "invalid_record"
    source_id = _text(item.get("id"))
    title = _text(item.get("name"))
    artist_source_id = _text(item.get("artist_id"))
    artist_name = _text(item.get("artist_name"))
    if not source_id or not title or not artist_source_id or not artist_name:
        return None, "missing_identity"
    musicinfo = _mapping(item.get("musicinfo"))
    tags = _mapping(musicinfo.get("tags"))
    genre_values = tags.get("genres") if isinstance(tags.get("genres"), list) else []
    genre = _text(genre_values[0]) if genre_values else None
    melody = _mapping(musicinfo.get("melody"))
    features = {
        "bpm": _number(melody.get("bpm")),
        "music_key": _text(melody.get("key")),
        "energy": _number(musicinfo.get("energy")),
        "valence": _number(musicinfo.get("valence")),
        "danceability": _number(musicinfo.get("danceability")),
        "loudness": _number(musicinfo.get("loudness")),
    }
    return JamendoTrack(
        source_id=source_id,
        title=title,
        artist_source_id=artist_source_id,
        artist_name=artist_name,
        album=_text(item.get("album_name")),
        audio_url=_text(item.get("audio")) or _text(item.get("audiodownload")),
        duration=_integer(item.get("duration")),
        genre=genre,
        avatar_url=_text(item.get("image")),
        features=features,
    ), None


class JamendoImportService:
    """在数据库事务中批量幂等写入 Jamendo 歌曲。"""

    def __init__(self, db: Session) -> None:
        self.artists = ArtistRepository(db)
        self.songs = SongRepository(db)

    def import_tracks(self, tracks: list[JamendoTrack], *, dry_run: bool = False) -> ImportReport:
        """创建或更新记录；不在 service 内提交事务。"""
        report = ImportReport(fetched=len(tracks))
        for track in tracks:
            if not track.audio_url:
                report.skipped += 1
                report.failure_reasons["missing_audio"] = (
                    report.failure_reasons.get("missing_audio", 0) + 1
                )
                continue
            artist = self.artists.get_by_source_id(JAMENDO_SOURCE, track.artist_source_id)
            song = self.songs.get_by_source_id(JAMENDO_SOURCE, track.source_id)
            if dry_run:
                if song is None:
                    report.created += 1
                else:
                    report.updated += 1
                continue
            if artist is None:
                artist = self.artists.create(
                    track.artist_name,
                    track.avatar_url,
                    source=JAMENDO_SOURCE,
                    source_id=track.artist_source_id,
                )
            elif artist.name != track.artist_name or artist.avatar_url != track.avatar_url:
                self.artists.update(
                    artist,
                    {"name": track.artist_name, "avatar_url": track.avatar_url},
                )

            values = {
                "title": track.title,
                "artist_id": artist.id,
                "album": track.album,
                "genre": track.genre,
                "duration": track.duration,
                "audio_url": track.audio_url,
                "source": JAMENDO_SOURCE,
                "source_id": track.source_id,
                **track.features,
            }
            if song is None:
                self.songs.create(values)
                report.created += 1
            else:
                self.songs.update(song, values)
                report.updated += 1
        return report


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _mapping(value: object) -> Mapping[str, Any]:
    """将未知对象安全收窄为字符串键映射。"""
    return value if isinstance(value, Mapping) else {}


def _api_error_message(headers: Mapping[object, object]) -> str:
    """将 Jamendo 的失败响应转成可诊断且不包含请求凭证的错误。"""
    code = _text(headers.get("code")) or str(headers.get("code") or "unknown")
    detail = _text(headers.get("error_message")) or "上游服务未提供失败原因"
    return f"Jamendo 请求失败（代码 {code}）：{detail[:300]}"


def _integer(value: object) -> int | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _number(value: object) -> float | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
