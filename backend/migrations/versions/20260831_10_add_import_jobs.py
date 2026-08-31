"""新增外部数据导入任务表。"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_10"
down_revision: str | None = "20260830_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建导入任务表和单来源活动任务唯一索引。"""
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_reasons", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_import_jobs_status",
        ),
        sa.CheckConstraint("requested_limit > 0", name="ck_import_jobs_requested_limit_positive"),
        sa.CheckConstraint("batch_size > 0", name="ck_import_jobs_batch_size_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_source", "import_jobs", ["source"], unique=False)
    op.create_index(
        "uq_import_jobs_active_source",
        "import_jobs",
        ["source"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )


def downgrade() -> None:
    """删除导入任务表。"""
    op.drop_index("uq_import_jobs_active_source", table_name="import_jobs")
    op.drop_index("ix_import_jobs_source", table_name="import_jobs")
    op.drop_table("import_jobs")
