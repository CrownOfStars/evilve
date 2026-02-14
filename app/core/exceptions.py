"""服务层异常定义。"""

from __future__ import annotations


class ServiceError(Exception):
    """服务层通用异常，用于向上游报告可控错误。"""


class NotFoundError(ServiceError):
    """资源不存在。"""


class ValidationError(ServiceError):
    """业务规则校验失败。"""
