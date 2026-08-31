"""外部数据导入任务模型。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportJobStatus(str, Enum):
    """导入任务生命周期状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportJob(Base):
    """记录导入进度、结果和失败原因。"""

    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_import_jobs_status",
        ),
        CheckConstraint("requested_limit > 0", name="ck_import_jobs_requested_limit_positive"),
        CheckConstraint("batch_size > 0", name="ck_import_jobs_batch_size_positive"),
        Index(
            "uq_import_jobs_active_source",
            "source",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ImportJobStatus.PENDING.value,
        server_default=ImportJobStatus.PENDING.value,
    )
    requested_limit: Mapped[int] = mapped_column(Integer)
    batch_size: Mapped[int] = mapped_column(Integer)
    fetched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    skipped: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failure_reasons: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
