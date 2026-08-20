"""API v1 路由聚合：把各业务路由挂载到这里。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
