"""fs.read_file — 读取指定路径的文件内容。

安全限制：
- 仅允许读取 allowed_root 下的文件（通过路径前缀校验）
- 大文件支持行范围读取
"""

from __future__ import annotations

import os

from agents import function_tool

from app.tools.registry import register_tool

# 默认允许的根路径（可通过配置覆盖）
_DEFAULT_ALLOWED_ROOT = os.getcwd()

# 最大读取大小
_MAX_READ_BYTES = 1024 * 1024  # 1MB


def _is_path_allowed(filepath: str, allowed_root: str) -> bool:
    """校验路径是否在允许的根目录下。"""

    real_path = os.path.realpath(filepath)
    real_root = os.path.realpath(allowed_root)
    return real_path.startswith(real_root + os.sep) or real_path == real_root


@register_tool(tool_id="fs.read_file", name="ReadFile", version="0.1.0")
@function_tool
def read_file(
    path: str,
    offset: int = 0,
    limit: int = 0,
) -> str:
    """Read the contents of a file at the given path.

    Args:
        path: Absolute or relative file path to read.
        offset: Start reading from this line number (1-based, 0 means from start).
        limit: Maximum number of lines to read (0 means read all).

    Returns:
        File contents as string, or error message.
    """

    import json

    if not _is_path_allowed(path, _DEFAULT_ALLOWED_ROOT):
        return json.dumps(
            {"error": f"Access denied: path must be under {_DEFAULT_ALLOWED_ROOT}"},
            ensure_ascii=False,
        )

    if not os.path.isfile(path):
        return json.dumps(
            {"error": f"File not found: {path}"},
            ensure_ascii=False,
        )

    try:
        file_size = os.path.getsize(path)
        if file_size > _MAX_READ_BYTES and offset == 0 and limit == 0:
            return json.dumps(
                {
                    "error": f"File too large ({file_size} bytes). "
                    f"Use offset/limit to read a portion.",
                    "size_bytes": file_size,
                },
                ensure_ascii=False,
            )

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if offset > 0 or limit > 0:
                lines = f.readlines()
                start = max(0, offset - 1) if offset > 0 else 0
                end = start + limit if limit > 0 else len(lines)
                content = "".join(lines[start:end])
            else:
                content = f.read(_MAX_READ_BYTES)

        return json.dumps(
            {"content": content, "path": path},
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
