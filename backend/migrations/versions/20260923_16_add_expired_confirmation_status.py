"""待确认调用新增 expired 终态。

背景：线上实测有 2 条 `tool_confirmations` 长期停在 `pending`——用户没确认就离开了页面。
它们虽然被 `expires_at` 过滤掉（不会真的执行），但状态一直是 pending，语义含糊，
排查时也无法区分"还在等用户"和"早就过期了"。

这条迁移把状态约束扩展为包含 `expired`，并**顺手把已过期的 pending 记录清理成终态**，
避免历史残留继续误导后续排查与会话恢复。
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260923_16"
down_revision: str | None = "20260923_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """扩展状态约束并把已过期的 pending 记录置为 expired。"""
    op.drop_constraint("ck_tool_confirmations_status", "tool_confirmations", type_="check")
    op.create_check_constraint(
        "ck_tool_confirmations_status",
        "tool_confirmations",
        "status IN ('pending', 'confirmed', 'rejected', 'expired')",
    )
    op.execute(
        "UPDATE tool_confirmations SET status = 'expired' "
        "WHERE status = 'pending' AND expires_at <= now()"
    )


def downgrade() -> None:
    """把 expired 记录退回 pending，并还原原状态约束。"""
    op.execute("UPDATE tool_confirmations SET status = 'pending' WHERE status = 'expired'")
    op.drop_constraint("ck_tool_confirmations_status", "tool_confirmations", type_="check")
    op.create_check_constraint(
        "ck_tool_confirmations_status",
        "tool_confirmations",
        "status IN ('pending', 'confirmed', 'rejected')",
    )
