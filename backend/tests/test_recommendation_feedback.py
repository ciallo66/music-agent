"""推荐反馈加权测试：点赞提升、不感兴趣排除、已看过降权。"""

from __future__ import annotations

from app.services.recommendation_feedback import (
    EXCLUDED_ACTIONS,
    action_weight,
    preferred_genre_bonus,
)


def test_like_boosts_and_seen_demotes() -> None:
    """点赞权重为正、已看过为负、不感兴趣最负。"""
    assert action_weight("like") > 0
    assert action_weight("seen") < 0
    assert action_weight("dislike") < action_weight("seen")


def test_unknown_action_has_no_effect() -> None:
    """未知动作不影响排序。"""
    assert action_weight("whatever") == 0.0


def test_dislike_and_less_are_excluded() -> None:
    """明确不想再看到的两类动作属于排除集。"""
    assert "dislike" in EXCLUDED_ACTIONS
    assert "less" in EXCLUDED_ACTIONS
    assert "like" not in EXCLUDED_ACTIONS


def test_liked_genre_bonus_is_capped() -> None:
    """同风格加分有上限，避免个别风格压过所有候选。"""
    assert preferred_genre_bonus(["摇滚"], {"摇滚": 1}) > 0
    assert preferred_genre_bonus(["摇滚"], {"摇滚": 99}) <= 0.3
    assert preferred_genre_bonus([], {"摇滚": 5}) == 0.0
    assert preferred_genre_bonus(["爵士"], {"摇滚": 5}) == 0.0
