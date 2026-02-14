"""API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.handoff import router as handoff_router
from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(handoff_router)
