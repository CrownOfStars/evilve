"""工具元数据读写服务。"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.tool import ToolRecord
from app.schemas.tool import ToolSchema
from app.tools.registry import ToolRegistry


def _schema_to_record(schema: ToolSchema) -> ToolRecord:
    """将 ToolSchema 转为数据库记录。"""

    return ToolRecord(
        tool_id=schema.tool_id,
        namespace=schema.namespace,
        name=schema.name,
        docstring=schema.docstring,
        version=schema.version,
    )


def _record_to_schema(record: ToolRecord) -> ToolSchema:
    """将数据库记录转为 ToolSchema。"""

    return ToolSchema(
        tool_id=record.tool_id,
        namespace=record.namespace,
        name=record.name,
        docstring=record.docstring,
        version=record.version,
    )


async def upsert_tool(session: AsyncSession, schema: ToolSchema) -> ToolSchema:
    """创建或更新工具元数据。"""

    record = await session.get(ToolRecord, schema.tool_id)
    if record:
        record.namespace = schema.namespace
        record.name = schema.name
        record.docstring = schema.docstring
        record.version = schema.version
    else:
        record = _schema_to_record(schema)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _record_to_schema(record)


async def get_tool(session: AsyncSession, tool_id: str) -> ToolSchema:
    """获取工具元数据。"""

    record = await session.get(ToolRecord, tool_id)
    if not record:
        raise NotFoundError(f"Tool not found: {tool_id}")
    return _record_to_schema(record)


async def list_tools(session: AsyncSession) -> list[ToolSchema]:
    """列出工具元数据。"""

    result = await session.exec(select(ToolRecord))
    return [_record_to_schema(record) for record in result.all()]


async def list_tools_by_namespace(
    session: AsyncSession, namespace: str
) -> list[ToolSchema]:
    """按命名空间列出工具。"""

    result = await session.exec(
        select(ToolRecord).where(ToolRecord.namespace == namespace)
    )
    return [_record_to_schema(record) for record in result.all()]


async def sync_registry_to_db(session: AsyncSession) -> list[ToolSchema]:
    """同步 Registry 中的工具到数据库。"""

    synced: list[ToolSchema] = []
    for schema in ToolRegistry.list_schemas():
        synced.append(await upsert_tool(session, schema))
    return synced
