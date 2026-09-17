"""歌曲向量化文本构造：把歌曲转成只含音乐属性的描述文本。

批量向量化与 Agent 相似歌曲检索共用本模块，确保库内向量与查询向量
出自同一套文本规则，避免两侧语义空间不一致。

文本刻意不包含歌名、歌手和专辑：这些专有名词会让向量偏向「文本相似」，
而相似歌曲需要的是「音乐相似」。
"""

from __future__ import annotations

from app.models.song import Song

# 情绪标签的否定前缀，标签值形如 "happy" / "not_happy"。
_NEGATIVE_PREFIX = "not_"


def _mood_words(mood_labels: object) -> list[str]:
    """把 AcousticBrainz 情绪标签中命中的项转成描述词。"""
    if not isinstance(mood_labels, dict):
        return []
    words = []
    for label, value in sorted(mood_labels.items()):
        if not isinstance(value, str) or not value:
            continue
        # 只保留命中项，not_ 前缀表示该情绪未命中。
        if value.startswith(_NEGATIVE_PREFIX) or label.startswith(_NEGATIVE_PREFIX):
            continue
        words.append(str(label))
    return words


def _genre_words(genre_labels: object) -> list[str]:
    """把多套流派标注体系的取值转成描述词。"""
    if not isinstance(genre_labels, dict):
        return []
    return [value for _, value in sorted(genre_labels.items()) if isinstance(value, str) and value]


def _voice_word(song: Song) -> str | None:
    """把歌声/器乐判定转成描述词。"""
    if not song.voice_instrumental:
        return None
    return "器乐" if song.voice_instrumental == "instrumental" else "含人声"


def _tonal_word(song: Song) -> str | None:
    """提取调性描述，例如「F 小调」。"""
    tonal = song.tonal_features
    if not isinstance(tonal, dict):
        return None
    key = tonal.get("key_key")
    scale = tonal.get("key_scale")
    if not key or not scale:
        return None
    scale_word = "小调" if scale == "minor" else "大调"
    return f"{key} {scale_word}"


def _tempo_word(bpm: float | None) -> str | None:
    """把 BPM 归入速度档位，便于向量捕捉「快慢」语义。"""
    if bpm is None or bpm <= 0:
        return None
    if bpm < 80:
        return "慢速"
    if bpm < 110:
        return "中速"
    if bpm < 140:
        return "中快"
    return "快速"


def _dissonance_word(song: Song) -> str | None:
    """用不和谐度均值粗略描述音色粗糙程度。"""
    spectral = song.spectral_features
    if not isinstance(spectral, dict):
        return None
    dissonance = spectral.get("dissonance")
    if not isinstance(dissonance, dict):
        return None
    mean = dissonance.get("mean")
    if not isinstance(mean, int | float):
        return None
    if mean < 0.3:
        return "音色柔和"
    if mean < 0.45:
        return "音色适中"
    return "音色粗粝"


def build_song_text(song: Song) -> str:
    """构造歌曲的向量化文本。

    Args:
        song: 歌曲实体，未加载的关联字段不会被访问。

    Returns:
        以 " | " 连接的属性描述；字段普遍缺失时可能为空字符串。
    """
    parts: list[str] = []

    moods = _mood_words(song.mood_labels)
    if moods:
        parts.append("情绪:" + "/".join(moods))

    genres = _genre_words(song.genre_labels)
    if genres:
        parts.append("风格:" + "/".join(dict.fromkeys(genres)))

    for word in (_voice_word(song), _tonal_word(song), _tempo_word(song.bpm)):
        if word:
            parts.append(word)

    dissonance = _dissonance_word(song)
    if dissonance:
        parts.append(dissonance)

    # 基础分类区分度有限，仅在没有其他线索时作为兜底。
    if song.genre and not genres:
        parts.append(f"分类:{song.genre}")

    return " | ".join(parts)
