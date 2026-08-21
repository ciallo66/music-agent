"""新增用户角色和账号状态。

Revision ID: 20260821_03
Revises: 20260820_02
Create Date: 2026-08-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_03"
down_revision: str | None = "20260820_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为用户表增加角色、状态及取值约束。"""
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.create_check_constraint(
        "ck_users_status",
        "users",
        "status IN ('active', 'disabled')",
    )


def downgrade() -> None:
    """移除用户角色和账号状态。"""
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "status")
    op.drop_column("users", "role")
