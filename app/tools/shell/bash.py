"""shell.bash — 在指定工作目录下执行 Bash 命令。

安全限制：
- 禁止 sudo 命令
- 可限定工作目录
- 超时保护
"""

from __future__ import annotations

import subprocess

from agents import function_tool

from app.tools.registry import register_tool

# 禁止执行的命令前缀
_BLOCKED_PREFIXES = ("sudo ",)

# 默认超时（秒）
_DEFAULT_TIMEOUT = 120

# 输出截断上限（字节）
_MAX_OUTPUT_BYTES = 512 * 1024  # 512KB


@register_tool(tool_id="shell.bash", name="Bash", version="0.1.0")
@function_tool
def bash(
    command: str,
    cwd: str = ".",
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> str:
    """Execute a bash command in the specified working directory.

    Args:
        command: The bash command to execute.
        cwd: Working directory (default: current directory).
        timeout_seconds: Maximum execution time in seconds (default: 120).

    Returns:
        JSON-formatted string with stdout, stderr, and exit_code.
    """

    # 安全检查
    stripped = command.strip().lower()
    for prefix in _BLOCKED_PREFIXES:
        if stripped.startswith(prefix):
            return f'{{"error": "Blocked: commands starting with \\"{prefix.strip()}\\" are not allowed", "exit_code": -1}}'

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        stdout = result.stdout[:_MAX_OUTPUT_BYTES]
        stderr = result.stderr[:_MAX_OUTPUT_BYTES]

        return (
            f'{{"stdout": {_escape_json(stdout)}, '
            f'"stderr": {_escape_json(stderr)}, '
            f'"exit_code": {result.returncode}}}'
        )
    except subprocess.TimeoutExpired:
        return f'{{"error": "Command timed out after {timeout_seconds}s", "exit_code": -1}}'
    except Exception as exc:
        return f'{{"error": {_escape_json(str(exc))}, "exit_code": -1}}'


def _escape_json(s: str) -> str:
    """简单 JSON 字符串转义。"""

    import json
    return json.dumps(s, ensure_ascii=False)
