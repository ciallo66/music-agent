"""为会话消息增加工具痕迹/实体清单列。

背景：为了让模型知道"哪些查询已经做过、上次查到了哪些实体"，需要把工具痕迹与实体清单
随助手消息持久化；但它们**不能混进 content**——content 会直接渲染到界面，
混进去就会在气泡里露出 `tool:search_songs(...)` 这类内部标记（已实测过这个泄漏）。

因此单独加一列 `agent_notes`（JSON 文本），只回灌给模型上下文：
- 工具痕迹解决"重复查同一件事"；
- 实体清单解决"把第三首加进歌单"这类指代断裂（旧工具结果原文不再进历史）。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_17"
down_revision: str | None = "20260923_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增 agent_notes 列，允许为空（历史消息没有该字段）。"""
    op.add_column("chat_messages", sa.Column("agent_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """删除 agent_notes 列。"""
    op.drop_column("chat_messages", "agent_notes")
