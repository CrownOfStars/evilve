"""fs.write_file — 写入内容到指定路径的文件。

安全限制：
- 仅允许写入 allowed_root 下的文件（通过路径前缀校验）
- 支持覆盖写和追加写
"""

from __future__ import annotations

import os

from agents import function_tool

from app.tools.registry import register_tool

# 默认允许的根路径
_DEFAULT_ALLOWED_ROOT = os.getcwd()


def _is_path_allowed(filepath: str, allowed_root: str) -> bool:
    """校验路径是否在允许的根目录下。"""

    real_path = os.path.realpath(filepath)
    real_root = os.path.realpath(allowed_root)
    return real_path.startswith(real_root + os.sep) or real_path == real_root


@register_tool(tool_id="fs.write_file", name="WriteFile", version="0.1.0")
@function_tool
def write_file(
    path: str,
    content: str,
    append: bool = False,
) -> str:
    """Write content to a file at the given path.

    Parent directories are created automatically if they don't exist.

    Args:
        path: Absolute or relative file path to write.
        content: The text content to write.
        append: If True, append to the file instead of overwriting.

    Returns:
        JSON string with success status and bytes written.
    """

    import json

    if not _is_path_allowed(path, _DEFAULT_ALLOWED_ROOT):
        return json.dumps(
            {"error": f"Access denied: path must be under {_DEFAULT_ALLOWED_ROOT}"},
            ensure_ascii=False,
        )

    try:
        # 自动创建父目录
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            bytes_written = f.write(content)

        return json.dumps(
            {
                "success": True,
                "path": path,
                "bytes_written": bytes_written,
                "mode": "append" if append else "overwrite",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps(
            {"error": str(exc), "success": False},
            ensure_ascii=False,
        )
