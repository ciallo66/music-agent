"""API v1 路由聚合：把各业务路由挂载到这里。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

# 子路由注册示例（后续按模块添加）：
# from app.api.v1.routes import songs, playlists
# router.include_router(songs.router, prefix="/songs", tags=["songs"])
# router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
