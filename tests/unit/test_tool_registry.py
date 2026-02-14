"""工具注册与持久化测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.tool import ToolSchema
from app.services.tool_service import get_tool, list_tools_by_namespace, sync_registry_to_db, upsert_tool
from app.tools.registry import ToolRegistry, register_tool


@pytest.mark.asyncio
async def test_tool_registry_and_db_sync() -> None:
    """注册工具并同步到数据库。"""

    ToolRegistry.clear()

    @register_tool(tool_id="util.echo", name="Echo")
    def echo(text: str) -> str:
        """Echo text."""

        return text

    @register_tool(tool_id="util.reverse", name="Reverse")
    def reverse(text: str) -> str:
        """Reverse text."""

        return text[::-1]

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        synced = await sync_registry_to_db(session)
        assert len(synced) == 2

        fetched = await get_tool(session, "util.echo")
        assert fetched.docstring == "Echo text."
        assert fetched.namespace == "util"

        # 按命名空间查询
        util_tools = await list_tools_by_namespace(session, "util")
        assert len(util_tools) == 2

        # 更新工具
        updated = await upsert_tool(
            session,
            ToolSchema(
                tool_id="util.echo",
                namespace="util",
                name="Echo",
                docstring="Echo text updated.",
                version="1.0.0",
            ),
        )
        assert updated.version == "1.0.0"


def test_parse_tool_id_validation() -> None:
    """tool_id 格式校验。"""

    ToolRegistry.clear()

    with pytest.raises(ValueError, match="namespace.name"):
        @register_tool(tool_id="no_namespace", name="Bad")
        def bad_tool() -> str:
            """This should fail."""

            return ""


def test_list_namespaces() -> None:
    """列出所有命名空间。"""

    ToolRegistry.clear()

    @register_tool(tool_id="math.add", name="Add")
    def add(a: int, b: int) -> int:
        """Add two integers."""

        return a + b

    @register_tool(tool_id="text.upper", name="Upper")
    def upper(s: str) -> str:
        """Uppercase text."""

        return s.upper()

    namespaces = ToolRegistry.list_namespaces()
    assert namespaces == ["math", "text"]


def test_list_by_namespace() -> None:
    """按命名空间筛选工具。"""

    ToolRegistry.clear()

    @register_tool(tool_id="math.add", name="Add")
    def add(a: int, b: int) -> int:
        """Add two integers."""

        return a + b

    @register_tool(tool_id="math.multiply", name="Multiply")
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""

        return a * b

    @register_tool(tool_id="text.upper", name="Upper")
    def upper(s: str) -> str:
        """Uppercase text."""

        return s.upper()

    math_tools = ToolRegistry.list_by_namespace("math")
    assert len(math_tools) == 2
    assert {t.tool_id for t in math_tools} == {"math.add", "math.multiply"}

    text_tools = ToolRegistry.list_by_namespace("text")
    assert len(text_tools) == 1
