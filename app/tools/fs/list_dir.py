"""fs.list_dir — 列出指定目录的内容。

安全限制：
- 仅允许浏览 allowed_root 下的目录
- 隐藏文件（以 . 开头）默认不显示
"""

from __future__ import annotations

import os

from agents import function_tool

from app.tools.registry import register_tool

# 默认允许的根路径
_DEFAULT_ALLOWED_ROOT = os.getcwd()

# 最大返回条目数
_MAX_ENTRIES = 500


def _is_path_allowed(dirpath: str, allowed_root: str) -> bool:
    """校验路径是否在允许的根目录下。"""

    real_path = os.path.realpath(dirpath)
    real_root = os.path.realpath(allowed_root)
    return real_path.startswith(real_root + os.sep) or real_path == real_root


@register_tool(tool_id="fs.list_dir", name="ListDir", version="0.1.0")
@function_tool
def list_dir(
    path: str = ".",
    show_hidden: bool = False,
) -> str:
    """List the contents of a directory.

    Args:
        path: Directory path to list (default: current directory).
        show_hidden: Whether to include hidden files/directories (starting with dot).

    Returns:
        JSON string with entries list, each having name, type (file/dir), and size.
    """

    import json

    if not _is_path_allowed(path, _DEFAULT_ALLOWED_ROOT):
        return json.dumps(
            {"error": f"Access denied: path must be under {_DEFAULT_ALLOWED_ROOT}"},
            ensure_ascii=False,
        )

    if not os.path.isdir(path):
        return json.dumps(
            {"error": f"Directory not found: {path}"},
            ensure_ascii=False,
        )

    try:
        raw_entries = sorted(os.listdir(path))
        entries: list[dict[str, object]] = []

        for name in raw_entries:
            if not show_hidden and name.startswith("."):
                continue
            if len(entries) >= _MAX_ENTRIES:
                break

            full_path = os.path.join(path, name)
            entry: dict[str, object] = {"name": name}

            if os.path.isdir(full_path):
                entry["type"] = "dir"
            else:
                entry["type"] = "file"
                try:
                    entry["size_bytes"] = os.path.getsize(full_path)
                except OSError:
                    entry["size_bytes"] = -1

            entries.append(entry)

        return json.dumps(
            {
                "path": os.path.realpath(path),
                "count": len(entries),
                "entries": entries,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
