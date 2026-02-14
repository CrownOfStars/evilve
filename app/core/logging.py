"""日志初始化。

统一日志格式，便于后续接入可观测性体系。
"""

from __future__ import annotations

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    """配置日志输出格式。"""

    settings = get_settings()
    logger.remove()
    logger.add(
        sink=lambda message: print(message, end=""),
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
