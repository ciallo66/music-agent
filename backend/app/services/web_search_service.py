"""联网搜索服务（DuckDuckGo 实现，可替换）。

依赖在调用时才导入：一是让上层能注入假实现做测试，二是避免未安装该依赖时
整个服务无法启动。
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from app.core.config import settings

# 单条搜索结果摘要的字符上限，避免把大段网页正文灌进上下文。
MAX_SNIPPET_CHARS = 500

# 工具层的 freshness 取值到搜索引擎时间范围的映射。
FRESHNESS_TIMELIMIT = {"day": "d", "week": "w", "month": "m", "year": "y"}

# 搜索结果摘要常以日期开头（如 "December 12, 2025 - "、"1 day ago - "），
# 单独抽成 published 字段，正文里不留这段噪音。
PUBLISHED_PREFIX = re.compile(
    r"^\s*(?P<published>"
    r"\d+\s+(?:minute|hour|day|week|month|year)s?\s+ago"
    r"|[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\s*[-–—·]\s*"
)


class WebSearchError(RuntimeError):
    """联网搜索请求失败，属于可重试的瞬时故障。"""


class WebSearchNotConfiguredError(WebSearchError):
    """联网搜索未启用或依赖缺失，重试不会成功。"""


class WebSearchProvider(Protocol):
    """联网搜索最小接口，便于替换搜索供应商和编写测试。"""

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """执行一次搜索，返回归一化后的结果列表。"""
        ...


class DuckDuckGoWebSearchService:
    """通过 DuckDuckGo 搜索接口获取站外资料。"""

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """执行一次搜索，返回标题、链接和摘要；freshness 用于限定时间范围。"""
        if not settings.web_search_enabled:
            raise WebSearchNotConfiguredError("联网搜索未启用")
        try:
            from ddgs import DDGS
            from ddgs.exceptions import DDGSException, RatelimitException
        except ImportError as error:  # 依赖缺失时给出可读错误，而不是 ImportError
            raise WebSearchNotConfiguredError("未安装联网搜索依赖 ddgs") from error
        try:
            raw_results = DDGS(timeout=settings.web_search_timeout_seconds).text(
                query,
                region=settings.web_search_region,
                safesearch="moderate",
                max_results=limit,
                timelimit=FRESHNESS_TIMELIMIT.get(freshness or ""),
            )
        except RatelimitException as error:
            raise WebSearchError("联网搜索被限流，请稍后再试") from error
        except DDGSException as error:
            raise WebSearchError("联网搜索请求失败") from error
        except Exception as error:  # 网络层异常统一按可重试处理
            raise WebSearchError("联网搜索请求失败") from error
        return _normalize_results(raw_results, limit)


def _normalize_results(raw_results: Any, limit: int) -> list[dict[str, str]]:
    """把搜索结果裁剪为标题、链接、摘要三个字段。"""
    if not isinstance(raw_results, list):
        raise WebSearchError("联网搜索返回格式无效")
    items: list[dict[str, str]] = []
    for raw in raw_results[:limit]:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("href") or raw.get("url") or "").strip()
        if not url:
            continue
        body = str(raw.get("body") or "").strip()
        item = {
            "title": str(raw.get("title") or "").strip(),
            "url": url,
            "snippet": body[:MAX_SNIPPET_CHARS],
        }
        if match := PUBLISHED_PREFIX.match(body):
            item["published"] = match.group("published")
            item["snippet"] = body[match.end() :][:MAX_SNIPPET_CHARS]
        items.append(item)
    return items
