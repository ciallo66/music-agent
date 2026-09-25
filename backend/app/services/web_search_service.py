"""联网搜索服务：可替换的搜索源实现。

背景（境内服务器的硬约束）：生产服务器在国内，实测 DuckDuckGo 全线
`Network is unreachable`（DNS 还被污染），因此默认改用抓取**必应中国**。
搜索结果页结构一变就会失效，所以解析失败必须给出可读错误，并且保留
可替换的 provider 接口 —— 以后换 Tavily / 博查只需新增一个实现类。

依赖只有 `httpx`（项目已有），不再需要 `ddgs`。
"""

from __future__ import annotations

import html
import re
from typing import Any, Protocol

import httpx

from app.core.config import settings

# 单条搜索结果摘要的字符上限，避免把大段网页正文灌进上下文。
MAX_SNIPPET_CHARS = 500

# Tavily 返回的是已抽取正文，单条可以给到更大的上限（整体仍由工具结果截断兜底）。
TAVILY_SNIPPET_CHARS = 2000

# 工具层的 freshness 取值到搜索引擎时间范围的映射。
FRESHNESS_TIMELIMIT = {"day": "d", "week": "w", "month": "m", "year": "y"}

# Tavily 的时间范围取值。
TAVILY_TIME_RANGE = {"day": "day", "week": "week", "month": "month", "year": "year"}

# 必应时间过滤参数的取值（默认按天往前推）。
BING_FRESHNESS_FILTER = {"day": "ez1", "week": "ez2", "month": "ez3"}

# 搜索结果摘要常以日期开头（如 "December 12, 2025 - "、"1 day ago - "），
# 单独抽成 published 字段，正文里不留这段噪音。
PUBLISHED_PREFIX = re.compile(
    r"^\s*(?P<published>"
    r"\d+\s+(?:minute|hour|day|week|month|year)s?\s+ago"
    r"|[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\s*[-–—·]\s*"
)

# 浏览器 UA：不伪装会被必应返回空结果页。
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 必应结果块：以 class 里含 b_algo 的 <li> 为界切开，比整段正则更耐 HTML 瑕疵。
_BING_RESULT_MARKER = re.compile(r'<li class="[^"]*b_algo[^"]*"')
_BING_TITLE = re.compile(r'<h2[^>]*>\s*<a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.S)
_BING_SNIPPET = re.compile(r"<p[^>]*>(?P<body>.*?)</p>", re.S)
_TAG = re.compile(r"<[^>]+>")


class WebSearchError(RuntimeError):
    """联网搜索请求失败，属于可重试的瞬时故障。"""


class WebSearchNotConfiguredError(WebSearchError):
    """联网搜索未启用或依赖缺失，重试不会成功。"""


class WebSearchProvider(Protocol):
    """联网搜索最小接口，便于替换搜索供应商和编写测试。"""

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """执行一次搜索，返回归一化后的结果列表。"""
        ...


class BingCnWebSearchService:
    """抓取必应中国（cn.bing.com）搜索结果页。

    境内服务器实测：首页与结果页均在 200ms 级可达，DuckDuckGo 则完全不可达。
    """

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """执行一次搜索，返回标题、链接和摘要；freshness 用于限定时间范围。"""
        if not settings.web_search_enabled:
            raise WebSearchNotConfiguredError("联网搜索未启用")
        params: dict[str, str] = {
            "q": query,
            "setlang": settings.web_search_market,
            "mkt": settings.web_search_market,
            "ensearch": "0",
        }
        # 必应把「最近一天/一周/一月」做成筛选参数；"year" 没有对应值，不给参数。
        if freshness in BING_FRESHNESS_FILTER:
            params["filters"] = f'ex1:"{BING_FRESHNESS_FILTER[freshness]}"'
        try:
            response = httpx.get(
                settings.web_search_bing_url,
                params=params,
                headers=BROWSER_HEADERS,
                timeout=settings.web_search_timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise WebSearchError("联网搜索超时") from error
        except httpx.HTTPStatusError as error:
            raise WebSearchError(f"联网搜索返回异常状态：{error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise WebSearchError("联网搜索请求失败") from error
        items = _parse_bing_results(response.text, limit)
        if not items:
            raise WebSearchError("搜索结果页结构已变化或没有结果，请检查搜索源")
        return items


class DuckDuckGoWebSearchService:
    """通过 DuckDuckGo 搜索接口获取站外资料（境外服务器可用，境内不可达）。

    依赖在调用时才导入：一是让上层能注入假实现做测试，二是避免未安装该依赖时
    整个服务无法启动。
    """

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


class TavilyWebSearchService:
    """调用 Tavily 搜索 API（专为 AI 设计的搜索服务）。

    相对抓取必应结果页的优势：**直接返回已抽取的网页正文**（单条上千字），
    而不只是几十字的摘要——这决定了模型能不能真的"读懂"外部资料。
    代价：需要 API key，且有月度额度。
    """

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """执行一次搜索，返回标题、链接和正文片段；freshness 限定时间范围。"""
        if not settings.web_search_enabled:
            raise WebSearchNotConfiguredError("联网搜索未启用")
        if not settings.web_search_api_key:
            raise WebSearchNotConfiguredError("未配置 WEB_SEARCH_API_KEY")
        body = self._request(query, limit, freshness)
        raw_results = body.get("results") if isinstance(body, dict) else None
        if not isinstance(raw_results, list):
            raise WebSearchError("联网搜索返回格式无效")
        items = _normalize_tavily_results(raw_results, limit)
        if not items:
            raise WebSearchError("联网搜索没有返回可用结果")
        return items

    @staticmethod
    def _request(query: str, limit: int, freshness: str | None) -> dict[str, Any]:
        """发一次 Tavily 请求；把 HTTP 层面的失败翻译成可读的搜索错误。"""
        payload: dict[str, Any] = {
            "api_key": settings.web_search_api_key,
            "query": query,
            "max_results": limit,
            "search_depth": settings.web_search_tavily_depth,
            # 让 Tavily 返回原始正文片段，而不是它自己润色过的答案
            "include_answer": False,
        }
        if freshness in TAVILY_TIME_RANGE:
            payload["time_range"] = TAVILY_TIME_RANGE[freshness]
        try:
            response = httpx.post(
                settings.web_search_tavily_url,
                json=payload,
                timeout=settings.web_search_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as error:
            raise WebSearchError("联网搜索超时") from error
        except httpx.HTTPStatusError as error:
            raise _tavily_status_error(error.response.status_code) from error
        except (httpx.HTTPError, ValueError) as error:
            raise WebSearchError("联网搜索请求失败") from error
        if not isinstance(body, dict):
            raise WebSearchError("联网搜索返回格式无效")
        return body


def _tavily_status_error(status: int) -> WebSearchError:
    """把 Tavily 的 HTTP 状态码翻译成确定的错误类型。"""
    if status in {401, 403}:
        return WebSearchNotConfiguredError("联网搜索凭证无效")
    if status == 429:
        return WebSearchError("联网搜索额度已用尽或触发限流")
    return WebSearchError(f"联网搜索返回异常状态：{status}")


def _normalize_tavily_results(raw_results: list[Any], limit: int) -> list[dict[str, str]]:
    """把 Tavily 的结果裁剪为标题、链接、正文片段三字段。"""
    items: list[dict[str, str]] = []
    for raw in raw_results[:limit]:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        if not url:
            continue
        body_text = str(raw.get("content") or "").strip()
        item = {
            "title": str(raw.get("title") or "").strip(),
            "url": url,
            # Tavily 的 content 本身就是正文抽取结果，可以放宽截断上限
            "snippet": body_text[:TAVILY_SNIPPET_CHARS],
        }
        if match := PUBLISHED_PREFIX.match(body_text):
            item["published"] = match.group("published")
            item["snippet"] = body_text[match.end() :][:TAVILY_SNIPPET_CHARS]
        items.append(item)
    return items


def build_web_search_provider() -> WebSearchProvider:
    """按配置构造搜索源；未知取值按默认的必应中国处理。"""
    if settings.web_search_provider == "tavily":
        return TavilyWebSearchService()
    if settings.web_search_provider == "duckduckgo":
        return DuckDuckGoWebSearchService()
    return BingCnWebSearchService()


def _parse_bing_results(page: str, limit: int) -> list[dict[str, str]]:
    """从必应结果页中抽取标题、链接和摘要。"""
    # 按结果块标记切段：每段就是一条结果所在的 HTML 片段。
    starts = [match.start() for match in _BING_RESULT_MARKER.finditer(page)]
    items: list[dict[str, str]] = []
    for index, start in enumerate(starts):
        if len(items) >= limit:
            break
        end = starts[index + 1] if index + 1 < len(starts) else len(page)
        block = page[start:end]
        title_match = _BING_TITLE.search(block)
        if title_match is None:
            continue
        url = html.unescape(title_match.group("url")).strip()
        if not url.startswith("http"):
            continue
        title = _strip_tags(title_match.group("title"))
        snippet_match = _BING_SNIPPET.search(block)
        body = _strip_tags(snippet_match.group("body")) if snippet_match else ""
        item = {"title": title, "url": url, "snippet": body[:MAX_SNIPPET_CHARS]}
        if match := PUBLISHED_PREFIX.match(body):
            item["published"] = match.group("published")
            item["snippet"] = body[match.end() :][:MAX_SNIPPET_CHARS]
        items.append(item)
    return items


def _strip_tags(fragment: str) -> str:
    """去掉标签与多余空白；HTML 实体在此还原。"""
    text = _TAG.sub(" ", fragment)
    text = html.unescape(text)
    # 页面里混有 en-space 等窄空白字符，统一压成普通空格。
    text = text.replace("\u2002", " ").replace("\u2003", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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
