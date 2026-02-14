"""工具注册与执行入口。

导入各命名空间子包以触发 @register_tool 装饰器注册。
新增命名空间时只需在此添加一行 import。
"""

# 运行时工具（闭包工厂，不走 Registry）
from app.tools import runtime_tools  # noqa: F401

# 内置工具（按命名空间组织，通过 @register_tool 自动注册到 Registry）
from app.tools import shell  # noqa: F401
from app.tools import fs  # noqa: F401
from app.tools import util  # noqa: F401
