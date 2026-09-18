"""反馈信号对推荐排序的加权。

本平台不托管音频、也没有可播放音源，因此「收听行为」基本为空；
推荐能用的真实信号是用户主动产生的收藏与反馈。这里把反馈显式转成权重：
- 喜欢（like）：同风格加权，并在候选排序里提升
- 不感兴趣（dislike）：直接排除
- 已看过（seen）：降权，避免反复推同一条
"""

from __future__ import annotations

# 各反馈动作对排序的影响权重，正数提升、负数降低。
ACTION_WEIGHTS: dict[str, float] = {
    "like": 0.25,
    "similar": 0.15,
    "seen": -0.2,
    "dislike": -1.0,
    "less": -0.5,
}

# 不感兴趣与减少此类内容：直接排除，不再出现在推荐里。
EXCLUDED_ACTIONS = frozenset({"dislike", "less"})


def action_weight(action: str) -> float:
    """取某个反馈动作的排序权重；未知动作按 0 处理。"""
    return ACTION_WEIGHTS.get(action, 0.0)


def preferred_genre_bonus(genres: list[str], liked_genres: dict[str, int]) -> float:
    """按用户点赞过的风格给候选加分，最多 0.3。"""
    if not genres or not liked_genres:
        return 0.0
    hits = sum(liked_genres.get(genre, 0) for genre in genres)
    return min(0.3, 0.1 * hits)
