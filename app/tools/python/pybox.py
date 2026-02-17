"""python.sandbox_exec — 在隔离的 Docker 沙箱中执行 Python 代码。

安全限制：
- 代码在受限的 Docker 容器中运行
- 禁止网络访问（依赖容器配置）
- 执行超时时间默认为 30 秒
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from agents import function_tool
from app.tools.registry import register_tool

# 沙箱容器名称 (建议通过环境变量注入，这里提供默认值)
_CONTAINER_NAME = os.getenv("SANDBOX_CONTAINER_NAME", "agent_sandbox")

# 默认超时时间 (秒)
_DEFAULT_TIMEOUT = 30

# 最大输出长度限制 (字符数)，防止 Agent 上下文溢出
_MAX_OUTPUT_LEN = 4000


def _truncate_output(text: str, max_len: int) -> str:
    """截断过长的输出，保留头部和尾部信息。"""
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return text[:half] + f"\n... [Output truncated, total {len(text)} chars] ...\n" + text[-half:]


@register_tool(tool_id="python.sandbox_exec", name="PythonInterpreter", version="0.1.0")
@function_tool
def sandbox_exec(
    code: str,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """Execute Python code in a secure Docker sandbox.

    Args:
        code: The Python code snippet to execute.
        timeout: Execution timeout in seconds (default: 30).

    Returns:
        JSON string containing execution status, stdout, and stderr.
    """
    
    # 1. 基础校验
    if not code.strip():
        return json.dumps(
            {"status": "error", "error": "Code cannot be empty"},
            ensure_ascii=False
        )

    # 2. 构造 Docker 命令
    # 使用 docker exec -i 通过标准输入管道传输代码，避免 shell 转义问题
    cmd = ["docker", "exec", "-i", _CONTAINER_NAME, "python3", "-"]

    try:
        # 3. 执行代码
        result = subprocess.run(
            cmd,
            input=code.encode("utf-8"),  # 将代码编码为 bytes 传入 stdin
            capture_output=True,          # 捕获 stdout 和 stderr
            timeout=timeout,
            check=False                   # 不要在非零退出码时抛出异常，我们需要捕获 stderr
        )

        stdout_str = result.stdout.decode("utf-8", errors="replace")
        stderr_str = result.stderr.decode("utf-8", errors="replace")

        # 4. 处理结果
        response: dict[str, Any] = {
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": _truncate_output(stdout_str, _MAX_OUTPUT_LEN),
            "stderr": _truncate_output(stderr_str, _MAX_OUTPUT_LEN),
        }
        
        # 如果是 Docker 本身报错（例如容器没启动），通常 stderr 会有内容且 exit_code 非 0
        if result.returncode != 0 and "No such container" in stderr_str:
             return json.dumps(
                {
                    "status": "error", 
                    "error": f"Sandbox environment not ready (Container '{_CONTAINER_NAME}' not found)."
                },
                ensure_ascii=False
            )

        return json.dumps(response, ensure_ascii=False)

    except subprocess.TimeoutExpired:
        return json.dumps(
            {
                "status": "timeout",
                "error": f"Execution timed out after {timeout} seconds.",
                # 尝试获取已有的输出（虽然超时通常没有完整输出，但可能有部分）
                "stdout": "", 
                "stderr": "Terminated due to timeout."
            },
            ensure_ascii=False
        )
    
    except Exception as exc:
        return json.dumps(
            {
                "status": "system_error",
                "error": str(exc)
            },
            ensure_ascii=False
        )