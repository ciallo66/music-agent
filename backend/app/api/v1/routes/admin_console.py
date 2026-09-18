"""管理后台：概览统计与账号管理接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import AdminOverview, AdminUserPage, AdminUserUpdate
from app.services.admin_service import (
    AdminService,
    AdminUserNotFoundError,
    AdminValidationError,
)

router = APIRouter()

AdminUser = Annotated[User, Depends(require_admin)]
Database = Annotated[Session, Depends(get_db)]


@router.get("/overview", response_model=AdminOverview)
def get_overview(db: Database, _: AdminUser) -> AdminOverview:
    """后台首页统计：库表计数与流派分布。"""
    return AdminService(db).overview()


@router.get("/users", response_model=AdminUserPage)
def list_users(
    db: Database,
    _: AdminUser,
    keyword: Annotated[str, Query(max_length=64)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminUserPage:
    """分页查询账号列表。"""
    return AdminService(db).list_users(keyword=keyword, page=page, page_size=page_size)


@router.patch("/users/{user_id}", response_model=AdminUserPage)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Database,
    _: AdminUser,
    keyword: Annotated[str, Query(max_length=64)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminUserPage:
    """修改账号角色或状态，并返回更新后的列表。"""
    service = AdminService(db)
    try:
        service.update_user(user_id, role=payload.role, status=payload.status)
        db.commit()
    except AdminUserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在") from error
    except AdminValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return service.list_users(keyword=keyword, page=page, page_size=page_size)
