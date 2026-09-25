"""为会话增加滚动摘要列。

背景：历史按条数窗口裁剪后，更早的内容只剩一句计数，模型拿不到信息——
长对话里最先丢失的是**用户最初提的限制条件**（"只要器乐、BPM 90-110"）与已有结论，
于是"接着刚才的条件再筛一下"这类追问会答偏。

行业做法是「滑动窗口 + 滚动摘要」。这里为会话增加两个字段：
- `chat_summary`：已经滑出窗口部分的要点；
- `summarized_through_id`：摘要覆盖到哪条消息，用于**增量**压缩（不必每轮重算）。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_18"
down_revision: str | None = "20260923_17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增滚动摘要字段，允许为空（历史会话没有摘要）。"""
    op.add_column("chat_sessions", sa.Column("chat_summary", sa.Text(), nullable=True))
    op.add_column("chat_sessions", sa.Column("summarized_through_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    """删除滚动摘要字段。"""
    op.drop_column("chat_sessions", "summarized_through_id")
    op.drop_column("chat_sessions", "chat_summary")
