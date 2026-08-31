"""数据导入任务请求与响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class JamendoImportRequest(BaseModel):
    """管理员创建 Jamendo 导入任务。"""

    limit: Annotated[int, Field(ge=1, le=10000)] = 100
    batch_size: Annotated[int, Field(ge=1, le=200)] = 50

    model_config = ConfigDict(extra="forbid")


class ImportJobResponse(BaseModel):
    """导入任务状态与统计。"""

    id: int
    source: str
    status: str
    requested_limit: int
    batch_size: int
    fetched: int
    created: int
    updated: int
    skipped: int
    failure_reasons: dict[str, int]
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
