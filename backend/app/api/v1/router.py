"""API v1 路由聚合：把各业务路由挂载到这里。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    admin_auth,
    admin_catalog,
    agent,
    auth,
    catalog,
    library,
    recommendation,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
router.include_router(catalog.router, tags=["catalog"])
router.include_router(library.router, tags=["library"])
router.include_router(recommendation.router, tags=["recommendation"])
router.include_router(agent.router, tags=["agent"])
router.include_router(admin_catalog.router, prefix="/admin", tags=["admin-catalog"])
