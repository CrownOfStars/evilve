"""util.datetime_now — 获取当前日期和时间。

LLM 不知道实时时间，此工具提供精确的当前时间戳。
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents import function_tool

from app.tools.registry import register_tool


@register_tool(tool_id="util.datetime_now", name="DatetimeNow", version="0.1.0")
@function_tool
def datetime_now(tz_offset_hours: int = 0) -> str:
    """Get the current date and time.

    Args:
        tz_offset_hours: Timezone offset from UTC in hours (e.g., 8 for CST/Beijing).

    Returns:
        JSON string with ISO formatted datetime, unix timestamp, and timezone info.
    """

    import json
    from datetime import timedelta

    tz = timezone(timedelta(hours=tz_offset_hours))
    now = datetime.now(tz)

    return json.dumps(
        {
            "iso": now.isoformat(),
            "unix_timestamp": int(now.timestamp()),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.strftime("%A"),
            "tz_offset": f"UTC{tz_offset_hours:+d}",
        },
        ensure_ascii=False,
    )
