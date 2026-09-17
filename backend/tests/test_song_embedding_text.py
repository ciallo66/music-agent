"""歌曲向量化文本构造的单元测试。"""

from __future__ import annotations

from app.models.song import Song
from app.services.song_embedding_text import build_song_text


def _song(**overrides: object) -> Song:
    """构造未持久化的歌曲实例，便于单独测试文本构造。"""
    defaults: dict[str, object] = {"title": "示例歌曲", "artist_id": 1}
    defaults.update(overrides)
    return Song(**defaults)


def test_includes_music_attributes() -> None:
    """完整特征应转成情绪、风格、人声、调性与速度描述。"""
    song = _song(
        mood_labels={"happy": "happy", "sad": "not_sad"},
        genre_labels={"rosamerica": "roc", "electronic": "trance"},
        voice_instrumental="instrumental",
        tonal_features={"key_key": "F", "key_scale": "minor"},
        bpm=148.0,
    )

    text = build_song_text(song)

    assert "情绪:happy" in text
    # 多套标注体系的流派值合并成一项，按体系名排序
    assert "风格:trance/roc" in text
    assert "器乐" in text
    assert "F 小调" in text
    assert "快速" in text


def test_excludes_proper_nouns() -> None:
    """歌名、歌手与专辑不得进入文本，否则向量会偏向文本相似。"""
    song = _song(
        title="All the Small Things",
        artist_id=1,
        album="Enema of the State",
        genre="electronic",
        mood_labels={"happy": "happy"},
    )

    text = build_song_text(song)

    assert "All the Small Things" not in text
    assert "Enema of the State" not in text


def test_filters_negative_mood_labels() -> None:
    """not_ 前缀表示情绪未命中，不应出现在文本里。"""
    song = _song(mood_labels={"happy": "not_happy", "relaxed": "relaxed"})

    text = build_song_text(song)

    assert "happy" not in text
    assert "relaxed" in text


def test_handles_missing_features() -> None:
    """特征全空时应返回空字符串而不是抛错。"""
    song = _song()

    assert build_song_text(song) == ""


def test_falls_back_to_genre_without_labels() -> None:
    """没有 AcousticBrainz 风格标签时，用基础分类兜底。"""
    song = _song(genre="jazz")

    assert build_song_text(song) == "分类:jazz"


def test_prefers_labels_over_genre() -> None:
    """存在风格标签时不再附加区分度较低的基础分类。"""
    song = _song(genre="electronic", genre_labels={"rosamerica": "cla"})

    text = build_song_text(song)

    assert "风格:cla" in text
    assert "分类:electronic" not in text


def test_tempo_buckets() -> None:
    """BPM 应映射到速度档位。"""
    assert "慢速" in build_song_text(_song(bpm=70.0))
    assert "中速" in build_song_text(_song(bpm=95.0))
    assert "中快" in build_song_text(_song(bpm=125.0))
    assert "快速" in build_song_text(_song(bpm=160.0))


def test_ignores_invalid_json_payloads() -> None:
    """JSONB 字段类型异常时不应抛错。"""
    song = _song(
        mood_labels=["not", "a", "dict"],  # type: ignore[arg-type]
        genre_labels="roc",  # type: ignore[arg-type]
        tonal_features={"key_key": "F"},  # 缺少 key_scale
        spectral_features={"dissonance": "unexpected"},  # type: ignore[dict-item]
    )

    assert build_song_text(song) == ""
