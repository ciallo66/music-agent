"""数据导入任务创建、查询和后台执行。"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.import_job_repository import ImportJobRepository
from app.schemas.import_job import ImportJobResponse, JamendoImportRequest
from app.services.jamendo_import_service import JAMENDO_SOURCE


class ImportAlreadyRunningError(Exception):
    """同一来源已有活动任务。"""


class ImportJobNotFoundError(Exception):
    """导入任务不存在。"""


class JamendoNotConfiguredError(Exception):
    """尚未配置 Jamendo 客户端 ID。"""


class ImportJobService:
    """编排导入任务的创建和查询。"""

    def __init__(self, db: Session) -> None:
        self.jobs = ImportJobRepository(db)

    def create_jamendo_job(self, payload: JamendoImportRequest) -> ImportJobResponse:
        """创建 Jamendo 任务；唯一索引负责最终并发保护。"""
        if not settings.jamendo_client_id:
            raise JamendoNotConfiguredError
        if self.jobs.get_active(JAMENDO_SOURCE) is not None:
            raise ImportAlreadyRunningError
        try:
            job = self.jobs.create(JAMENDO_SOURCE, payload.limit, payload.batch_size)
        except IntegrityError as error:
            raise ImportAlreadyRunningError from error
        return ImportJobResponse.model_validate(job)

    def get_job(self, job_id: int) -> ImportJobResponse:
        """返回指定任务。"""
        job = self.jobs.get(job_id)
        if job is None:
            raise ImportJobNotFoundError
        return ImportJobResponse.model_validate(job)

    def list_jobs(self, limit: int) -> list[ImportJobResponse]:
        """返回最近的任务。"""
        return [ImportJobResponse.model_validate(job) for job in self.jobs.list_recent(limit)]
