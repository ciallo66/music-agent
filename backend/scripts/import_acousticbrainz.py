"""按 MusicBrainz recording MBID 导入 AcousticBrainz 音乐特征。"""

from __future__ import annotations

import argparse

import httpx
from app.core.database import SessionLocal
from app.models.artist import Artist
from app.models.song import Song
from sqlalchemy import select

SOURCE = "acousticbrainz"
USER_AGENT = "music-agent-acousticbrainz-import/1.0"

# 对外展示用的主分类取自 rosamerica 体系：它的八分类分布均衡，
# 而 dortmund 体系面向电子音乐细分，在本数据集上 83% 会落进 electronic，
# 用作展示几乎没有区分度。完整的多体系标注仍保存在 genre_labels 中。
GENRE_DISPLAY_BY_ROSAMERICA = {
    "cla": "古典",
    "roc": "摇滚",
    "rhy": "节奏布鲁斯",
    "pop": "流行",
    "dan": "舞曲",
    "jaz": "爵士",
    "hip": "嘻哈",
    "spe": "语音",
}


def display_genre(rosamerica: object, fallback: object) -> str | None:
    """把 rosamerica 分类码转成中文展示名；缺失时回退到 dortmund 原值。"""
    if isinstance(rosamerica, str):
        mapped = GENRE_DISPLAY_BY_ROSAMERICA.get(rosamerica)
        if mapped:
            return mapped
    return fallback if isinstance(fallback, str) and fallback else None


def fetch_json(url: str) -> dict:
    """请求并校验一个 JSON 接口。"""
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.json()


def import_recording(mbid: str) -> dict[str, object]:
    """导入单条 recording 的 MusicBrainz 元数据和 AcousticBrainz 特征。"""
    high = fetch_json(f"https://acousticbrainz.org/api/v1/{mbid}/high-level")["highlevel"]
    low_response = fetch_json(f"https://acousticbrainz.org/api/v1/{mbid}/low-level")
    low = low_response["lowlevel"]
    rhythm = low_response["rhythm"]
    tonal = low_response["tonal"]
    recording = fetch_json(
        f"https://musicbrainz.org/ws/2/recording/{mbid}?fmt=json&inc=artists+releases"
    )
    credits = recording.get("artist-credit") or []
    artist_name = str(credits[0].get("name", "")).strip() if credits else ""
    title = str(recording.get("title", "")).strip()
    if not title or not artist_name:
        raise ValueError(f"MusicBrainz recording {mbid} 缺少真实曲名或艺术家")
    release = (recording.get("releases") or [{}])[0]

    def value(key: str) -> object:
        return high.get(key, {}).get("value")

    def probability(key: str) -> object:
        return high.get(key, {}).get("probability")

    mood = {key.removeprefix("mood_"): value(key) for key in high if key.startswith("mood_")}
    genre = {key.removeprefix("genre_"): value(key) for key in high if key.startswith("genre_")}
    rhythm_features = {key: rhythm[key] for key in ("bpm", "beats_count", "onset_rate")}
    tonal_features = {
        key: tonal[key]
        for key in ("chords_key", "chords_scale", "key_key", "key_scale", "key_strength")
    }
    spectral_features = {
        key: item
        for key, item in low.items()
        if key.startswith("spectral_")
        or key in ("average_loudness", "dynamic_complexity", "dissonance")
    }
    values = {
        "title": title,
        "album": release.get("title"),
        "genre": display_genre(value("genre_rosamerica"), value("genre_dortmund")),
        "source": SOURCE,
        "source_id": mbid,
        "popularity": 0,
        "bpm": rhythm.get("bpm"),
        "music_key": tonal.get("key_key"),
        "danceability": high.get("danceability", {}).get("all", {}).get("danceable"),
        "loudness": low.get("average_loudness"),
        "voice_instrumental": value("voice_instrumental"),
        "voice_probability": probability("voice_instrumental"),
        "rhythm_features": rhythm_features,
        "tonal_features": tonal_features,
        "spectral_features": spectral_features,
        "mood_labels": mood,
        "genre_labels": genre,
        "analysis_metadata": {"source": "AcousticBrainz", "mbid": mbid},
        "feature_completeness": 1.0,
    }
    with SessionLocal() as db:
        artist = db.scalar(
            select(Artist).where(Artist.source == SOURCE, Artist.source_id == artist_name)
        )
        if artist is None:
            artist = Artist(name=artist_name, source=SOURCE, source_id=artist_name)
            db.add(artist)
            db.flush()
        values["artist_id"] = artist.id
        song = db.scalar(select(Song).where(Song.source == SOURCE, Song.source_id == mbid))
        if song is None:
            db.add(Song(**values))
            result = "created"
        else:
            for key, item in values.items():
                setattr(song, key, item)
            result = "updated"
        db.commit()
    return {"result": result, "title": values["title"], "artist": artist_name, "mbid": mbid}


def main() -> None:
    """解析参数并导入 AcousticBrainz recording。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("mbid", help="MusicBrainz recording MBID")
    args = parser.parse_args()
    print(import_recording(args.mbid))


if __name__ == "__main__":
    main()
