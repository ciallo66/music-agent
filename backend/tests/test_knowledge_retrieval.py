"""知识库检索改进测试：中文 n-gram 兜底 + 知识库独立阈值。

对应线上实测的两个问题：
① 阈值 0.35 太松——"今天天气怎么样"也会返回 5 条音乐知识（相似度 0.41）；
② 关键词兜底按空格切词，中文整句匹配不到——"什么是萨克斯"命中 0 条，而"萨克斯"命中 1 条。
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.models.music_knowledge import MusicKnowledge
from app.repositories.music_knowledge_repository import build_terms
from app.services.rag_service import MusicKnowledgeService


def test_build_terms_splits_chinese_into_ngrams() -> None:
    """中文没有空格，必须切成 n-gram 才能命中库里的词。"""
    terms = build_terms("什么是萨克斯")

    assert "萨克斯" in terms  # 3 字片段
    assert "萨克" in terms  # 2 字片段
    assert "什么是萨克斯" not in terms  # 整句不该作为一个词


def test_build_terms_keeps_english_words() -> None:
    """英文与数字保持按词切分，不做 n-gram。"""
    terms = build_terms("Danceability 是什么")

    assert "danceability" in terms
    assert "dance" not in terms


def test_build_terms_drops_punctuation_only_tokens() -> None:
    """纯标点不产生检索片段。"""
    assert build_terms("？？？") == []


def test_build_terms_drops_generic_fragments() -> None:
    """通用问句词与跨领域名词要被过滤，否则会误命中音乐条目。"""
    terms = build_terms("推荐几部好看的电影")

    for noise in ("推荐", "电影", "好看", "几部"):
        assert noise not in terms


def test_lexical_search_does_not_match_unrelated_topics(db_session: Any) -> None:
    """跨领域问题不能因为通用词命中知识库（修复前"推荐几部好看的电影"会命中 2 条）。"""
    db_session.add_all(
        [
            MusicKnowledge(
                content="混音与母带是录音后的处理环节，用于平衡音量与声场。", source="test"
            ),
            MusicKnowledge(content="动态范围指音乐中最轻与最响部分之间的差距。", source="test"),
        ]
    )
    db_session.flush()

    result = MusicKnowledgeService(db_session, None).search("推荐几部好看的电影", 5)

    assert result["count"] == 0
    assert result["relevant"] is False


def test_lexical_search_matches_chinese_question(db_session: Any) -> None:
    """关键词兜底要能用整句中文问题命中条目（修复前命中 0 条）。"""
    db_session.add(
        MusicKnowledge(content="萨克斯（Saxophone）是爵士乐的代表性管乐器。", source="test")
    )
    db_session.flush()

    result = MusicKnowledgeService(db_session, None).search("什么是萨克斯", 5)

    assert result["mode"] == "lexical"
    assert result["relevant"] is True
    assert "萨克斯" in result["items"][0]["content"]


def test_lexical_search_prefers_longer_fragments(db_session: Any) -> None:
    """长片段优先：有 3 字以上匹配时，不因为 2 字片段把无关条目也捞进来。"""
    db_session.add_all(
        [
            MusicKnowledge(content="贝斯（Bass）负责低频与和声根基。", source="test"),
            MusicKnowledge(content="拍号（Time Signature）表示每小节的拍数。", source="test"),
        ]
    )
    db_session.flush()

    result = MusicKnowledgeService(db_session, None).search("贝斯在乐队里起什么作用", 5)

    assert result["count"] == 1
    assert "贝斯" in result["items"][0]["content"]


def test_lexical_search_returns_empty_for_unrelated_question(db_session: Any) -> None:
    """完全无关的问题不命中任何条目。"""
    db_session.add(MusicKnowledge(content="爵士乐起源于新奥尔良。", source="test"))
    db_session.flush()

    result = MusicKnowledgeService(db_session, None).search("怎么做红烧肉", 5)

    assert result["count"] == 0
    assert result["relevant"] is False


def test_noise_ratio_uses_whole_corpus_not_coarse_candidates(db_session: Any) -> None:
    """片段的噪声占比必须按全量知识库算，不能用粗召回结果集当分母。

    修复前的行为：候选集本身就是「包含这些片段」的文档，于是每个片段的比例都接近
    100%，唯一能命中的那个片段也被当噪声剔除，检索空手而归。这里构造一个只有
    "和声" 能命中的查询，并让该片段出现在全部候选文档里（模拟真实漏检场景）。
    """
    for index in range(5):
        db_session.add(
            MusicKnowledge(content=f"第{index}条补充说明，主要讲和声的构成与听感。", source="test")
        )
    db_session.add(
        MusicKnowledge(
            content="和声指多个音同时发响所形成的组合，是纵向的音高组织方式。", source="test"
        )
    )
    for index in range(23):
        db_session.add(
            MusicKnowledge(content=f"第{index}条无关条目，讨论节奏与速度。", source="test")
        )
    db_session.flush()

    result = MusicKnowledgeService(db_session, None).search("什么是和声", 5)

    assert result["mode"] == "lexical"
    assert result["count"] >= 1
    assert any("和声指多个音同时发响" in item["content"] for item in result["items"])


def test_knowledge_threshold_is_stricter_than_song_similarity() -> None:
    """知识库阈值必须比歌曲相似度阈值严（定标数据：命中 0.60+、无关 0.46-）。"""
    assert settings.embedding_knowledge_threshold > settings.embedding_similarity_threshold
    assert 0.45 <= settings.embedding_knowledge_threshold <= 0.60
