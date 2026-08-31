"""Jamendo 导入后台任务及其独立事务边界。"""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.import_job import ImportJob, ImportJobStatus
from app.repositories.import_job_repository import ImportJobRepository
from app.services.jamendo_import_service import JamendoClient, JamendoImportService, JamendoTrack


def run_jamendo_import_job(job_id: int) -> None:
    """执行后台任务；每一页由本 worker 独立提交事务。"""
    job = _wait_for_job(job_id)
    if job is None:
        return
    client = JamendoClient()
    try:
        _mark_running(job_id)
        offset = job.fetched
        while offset < job.requested_limit:
            requested = min(job.batch_size, job.requested_limit - offset)
            page = client.fetch_page(offset=offset, limit=requested)
            if page.raw_count == 0:
                break
            _import_page(job_id, page.raw_count, page.tracks, page.failure_reasons)
            offset += page.raw_count
            if page.raw_count < requested:
                break
        _finish_job(job_id, ImportJobStatus.COMPLETED, None)
    except Exception as error:
        _finish_job(job_id, ImportJobStatus.FAILED, _safe_error(error))
    finally:
        client.close()


def _wait_for_job(job_id: int) -> ImportJob | None:
    """等待请求事务提交，避免后台任务抢先读取。"""
    for _attempt in range(10):
        with SessionLocal() as db:
            job = ImportJobRepository(db).get(job_id)
            if job is not None:
                db.expunge(job)
                return job
        time.sleep(0.05)
    return None


def _mark_running(job_id: int) -> None:
    """标记任务开始。"""
    with SessionLocal() as db:
        job = _require_job(db, job_id)
        ImportJobRepository(db).update(
            job,
            {
                "status": ImportJobStatus.RUNNING.value,
                "started_at": datetime.now(timezone.utc),
            },
        )
        db.commit()


def _import_page(
    job_id: int,
    raw_count: int,
    tracks: list[JamendoTrack],
    normalization_reasons: dict[str, int],
) -> None:
    """在单个事务中写入一页歌曲和对应进度。"""
    with SessionLocal() as db:
        job = _require_job(db, job_id)
        report = JamendoImportService(db).import_tracks(tracks)
        reasons = Counter(job.failure_reasons)
        reasons.update(normalization_reasons)
        reasons.update(report.failure_reasons)
        skipped = sum(normalization_reasons.values()) + report.skipped
        ImportJobRepository(db).update(
            job,
            {
                "fetched": job.fetched + raw_count,
                "created": job.created + report.created,
                "updated": job.updated + report.updated,
                "skipped": job.skipped + skipped,
                "failure_reasons": dict(reasons),
            },
        )
        db.commit()


def _finish_job(job_id: int, status: ImportJobStatus, error_message: str | None) -> None:
    """记录任务最终状态；若任务尚未提交则静默退出。"""
    with SessionLocal() as db:
        job = ImportJobRepository(db).get(job_id)
        if job is None:
            return
        ImportJobRepository(db).update(
            job,
            {
                "status": status.value,
                "error_message": error_message,
                "finished_at": datetime.now(timezone.utc),
            },
        )
        db.commit()


def _require_job(db: Session, job_id: int) -> ImportJob:
    """后台执行时获取任务。"""
    job = ImportJobRepository(db).get(job_id)
    if job is None:
        raise RuntimeError("导入任务不存在")
    return job


def _safe_error(error: Exception) -> str:
    """限制持久化错误长度，避免保存堆栈和超大响应。"""
    message = str(error).strip() or error.__class__.__name__
    return message[:1000]
