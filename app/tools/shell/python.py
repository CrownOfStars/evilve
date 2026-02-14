"""shell.python — 执行 Python 代码片段。

当前为直接 exec 执行，不做沙箱隔离。
未来可替换为 subprocess + 虚拟环境或 Docker 容器。
"""

from __future__ import annotations

import io
import sys
import traceback

from agents import function_tool

from app.tools.registry import register_tool

# 默认超时（秒）—— 通过信号实现，仅 Unix 支持
_DEFAULT_TIMEOUT = 30

# 输出截断上限
_MAX_OUTPUT_CHARS = 100_000


@register_tool(tool_id="shell.python", name="Python", version="0.1.0")
@function_tool
def python_exec(code: str) -> str:
    """Execute a Python code snippet and return its stdout output.

    The code runs in a fresh namespace. Use print() to produce output.
    Variables defined in the code are not persisted across calls.

    Args:
        code: Python source code to execute.

    Returns:
        JSON-formatted string with stdout, stderr (if any), and success flag.
    """

    import json

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    old_stdout, old_stderr = sys.stdout, sys.stderr

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        exec_globals: dict[str, object] = {"__builtins__": __builtins__}
        exec(code, exec_globals)  # noqa: S102

        stdout_text = stdout_capture.getvalue()[:_MAX_OUTPUT_CHARS]
        stderr_text = stderr_capture.getvalue()[:_MAX_OUTPUT_CHARS]

        return json.dumps(
            {"stdout": stdout_text, "stderr": stderr_text, "success": True},
            ensure_ascii=False,
        )
    except Exception:
        stdout_text = stdout_capture.getvalue()[:_MAX_OUTPUT_CHARS]
        error_text = traceback.format_exc()[:_MAX_OUTPUT_CHARS]

        return json.dumps(
            {"stdout": stdout_text, "error": error_text, "success": False},
            ensure_ascii=False,
        )
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
