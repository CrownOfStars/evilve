"""工具注册表。

提供装饰器与注册表，统一管理可执行工具与其元数据。
工具采用 namespace.name 格式标识，如 math.add、runtime.send_message。
"""

from __future__ import annotations

from collections.abc import Callable

from app.schemas.tool import ToolSchema


def _parse_tool_id(tool_id: str) -> tuple[str, str]:
    """解析 tool_id 为 (namespace, name)。

    Args:
        tool_id: 格式 'namespace.name'，如 'math.add'。

    Returns:
        (namespace, name) 二元组。

    Raises:
        ValueError: tool_id 格式不合法。
    """

    parts = tool_id.split(".", maxsplit=1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"tool_id 必须为 'namespace.name' 格式，收到: '{tool_id}'"
        )
    return parts[0], parts[1]


class ToolRegistry:
    """工具注册表。

    工具统一使用 namespace.name 格式标识（如 math.add）。
    """

    _tools: dict[str, Callable] = {}
    _schemas: dict[str, ToolSchema] = {}

    @classmethod
    def register(cls, schema: ToolSchema, func: Callable) -> None:
        """注册工具与元数据。"""

        cls._tools[schema.tool_id] = func
        cls._schemas[schema.tool_id] = schema

    @classmethod
    def get_callable(cls, tool_id: str) -> Callable:
        """获取工具可执行函数。"""

        return cls._tools[tool_id]

    @classmethod
    def has(cls, tool_id: str) -> bool:
        """判断工具是否已注册。"""

        return tool_id in cls._tools

    @classmethod
    def resolve_tools(cls, tool_ids: list[str]) -> list[Callable]:
        """批量解析 tool_id 为可执行对象，跳过未注册的。"""

        resolved: list[Callable] = []
        for tool_id in tool_ids:
            if cls.has(tool_id):
                resolved.append(cls.get_callable(tool_id))
        return resolved

    @classmethod
    def list_by_namespace(cls, namespace: str) -> list[ToolSchema]:
        """列出指定命名空间下的所有工具。"""

        return [
            schema
            for schema in cls._schemas.values()
            if schema.namespace == namespace
        ]

    @classmethod
    def get_schema(cls, tool_id: str) -> ToolSchema:
        """获取工具元数据。"""

        return cls._schemas[tool_id]

    @classmethod
    def list_schemas(cls) -> list[ToolSchema]:
        """列出所有工具元数据。"""

        return list(cls._schemas.values())

    @classmethod
    def list_namespaces(cls) -> list[str]:
        """列出所有已注册的命名空间。"""

        return sorted({schema.namespace for schema in cls._schemas.values()})

    @classmethod
    def clear(cls) -> None:
        """清空注册表，用于测试场景。"""

        cls._tools.clear()
        cls._schemas.clear()


def register_tool(
    tool_id: str,
    name: str,
    *,
    version: str | None = None,
    docstring: str | None = None,
) -> Callable[[Callable], Callable]:
    """注册工具装饰器。

    Args:
        tool_id: 工具唯一标识，格式 'namespace.name'，如 'math.add'。
        name: 工具展示名称。
        version: 工具版本。
        docstring: 工具说明文档，未提供时从函数 __doc__ 读取。
    """

    namespace, short_name = _parse_tool_id(tool_id)

    def decorator(func: Callable) -> Callable:
        resolved_docstring = docstring or func.__doc__
        if not resolved_docstring:
            raise ValueError("Tool must define docstring")

        schema = ToolSchema(
            tool_id=tool_id,
            namespace=namespace,
            name=name,
            docstring=resolved_docstring.strip(),
            version=version,
        )
        ToolRegistry.register(schema=schema, func=func)
        return func

    return decorator
