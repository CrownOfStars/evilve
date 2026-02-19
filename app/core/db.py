"""数据库连接与会话管理。

合并自 backend/database.py：保留 SQLite 默认配置与 get_db 依赖，
采用异步 SQLModel 实现以符合项目规范。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
import app.models  # noqa: F401


# 兼容 backend：原 SQLALCHEMY_DATABASE_URL = "sqlite:///./gpost_agents.db"
# 现通过 config.database_url 配置，默认 evilve.db


def create_engine() -> AsyncEngine:
    """创建异步数据库引擎。"""

    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, future=True)


ENGINE = create_engine()
AsyncSessionLocal = async_sessionmaker(
    ENGINE, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """初始化数据库结构。"""

    async with ENGINE.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话。"""

    async with AsyncSessionLocal() as session:
        yield session


# 兼容 backend/main.py 中 Depends(get_db) 的用法
get_db = get_session
