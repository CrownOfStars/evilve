"""数据库连接与会话管理。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
import app.models  # noqa: F401


def create_engine() -> AsyncEngine:
    """创建异步数据库引擎。"""

    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, future=True)


ENGINE = create_engine()
AsyncSessionLocal = async_sessionmaker(ENGINE, expire_on_commit=False)


async def init_db() -> None:
    """初始化数据库结构。"""

    async with ENGINE.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话。"""

    async with AsyncSessionLocal() as session:
        yield session
