"""新增 Agent 高风险工具调用的待确认表。

Revision ID: 20260910_11
Revises: 20260831_10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_11"
down_revision: str | None = "20260831_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建待确认表及按用户和状态的索引。"""
    op.create_table(
        "tool_confirmations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("call_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("arguments", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected')",
            name="ck_tool_confirmations_status",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_confirmations_session_id", "tool_confirmations", ["session_id"], unique=False
    )
    op.create_index(
        "ix_tool_confirmations_user_status",
        "tool_confirmations",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """删除待确认表。"""
    op.drop_index("ix_tool_confirmations_user_status", table_name="tool_confirmations")
    op.drop_index("ix_tool_confirmations_session_id", table_name="tool_confirmations")
    op.drop_table("tool_confirmations")
