"""URL 工具函数"""
from __future__ import annotations

from urllib.parse import urlparse


def is_https_url(url: str | None) -> bool:
    """判断是否为 https URL"""
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)
