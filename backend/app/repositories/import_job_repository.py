"""外部数据导入任务的数据访问。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_job import ImportJob, ImportJobStatus


class ImportJobRepository:
    """封装导入任务查询与写入。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: int) -> ImportJob | None:
        """按主键查询任务。"""
        return self.db.get(ImportJob, job_id)

    def get_active(self, source: str) -> ImportJob | None:
        """查询指定来源尚未结束的任务。"""
        statement = select(ImportJob).where(
            ImportJob.source == source,
            ImportJob.status.in_([ImportJobStatus.PENDING.value, ImportJobStatus.RUNNING.value]),
        )
        return self.db.scalar(statement)

    def list_recent(self, limit: int) -> list[ImportJob]:
        """返回最近创建的任务。"""
        statement = select(ImportJob).order_by(ImportJob.id.desc()).limit(limit)
        return list(self.db.scalars(statement))

    def create(self, source: str, requested_limit: int, batch_size: int) -> ImportJob:
        """创建待执行任务并刷新主键。"""
        job = ImportJob(
            source=source,
            requested_limit=requested_limit,
            batch_size=batch_size,
        )
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)
        return job

    def update(self, job: ImportJob, values: Mapping[str, Any]) -> ImportJob:
        """更新任务字段。"""
        for field_name, value in values.items():
            setattr(job, field_name, value)
        self.db.flush()
        self.db.refresh(job)
        return job
