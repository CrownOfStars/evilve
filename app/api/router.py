"""API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import agents, chat, crud_skills, llms, logs, providers, sessions, tools
from app.api.health import router as health_router
from app.api.handoff import router as handoff_router
from app.api.skills import router as skill_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(handoff_router)
api_router.include_router(skill_router)

# 编排 CRUD API（/api 前缀在 main.py 中挂载）
orchestration_router = APIRouter()
orchestration_router.include_router(agents.router)
orchestration_router.include_router(crud_skills.router)
orchestration_router.include_router(tools.router)
orchestration_router.include_router(providers.router)
orchestration_router.include_router(llms.router)
orchestration_router.include_router(sessions.router)
orchestration_router.include_router(chat.router)
orchestration_router.include_router(logs.router)