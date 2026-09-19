"""管理员数据导入任务接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_real_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.import_job import ImportJobResponse, JamendoImportRequest
from app.services.import_job_service import (
    ImportAlreadyRunningError,
    ImportJobNotFoundError,
    ImportJobService,
    JamendoNotConfiguredError,
)
from app.workers.import_job_worker import run_jamendo_import_job

router = APIRouter()


@router.post(
    "/jamendo",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_jamendo_import(
    payload: JamendoImportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> ImportJobResponse:
    """创建 Jamendo 后台导入任务。"""
    try:
        job = ImportJobService(db).create_jamendo_job(payload)
    except JamendoNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="尚未配置 Jamendo Client ID",
        ) from error
    except ImportAlreadyRunningError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Jamendo 导入任务正在执行",
        ) from error
    background_tasks.add_task(run_jamendo_import_job, job.id)
    return job


@router.get("", response_model=list[ImportJobResponse])
def list_import_jobs(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ImportJobResponse]:
    """查询最近的导入任务。"""
    return ImportJobService(db).list_jobs(limit)


@router.get("/{job_id}", response_model=ImportJobResponse)
def read_import_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_real_admin)],
) -> ImportJobResponse:
    """查询单个导入任务进度。"""
    try:
        return ImportJobService(db).get_job(job_id)
    except ImportJobNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="导入任务不存在"
        ) from error
