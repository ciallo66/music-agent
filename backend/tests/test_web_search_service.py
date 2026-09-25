"""联网搜索工具与结果归一化测试。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.core.config import settings
from app.services.agent.music_tools import MusicAgentTools
from app.services.agent.policy import ToolDecision, evaluate_tool_call
from app.services.agent.registry import ToolOperation, ToolRegistry
from app.services.web_search_service import (
    BING_FRESHNESS_FILTER,
    FRESHNESS_TIMELIMIT,
    MAX_SNIPPET_CHARS,
    TAVILY_SNIPPET_CHARS,
    BingCnWebSearchService,
    DuckDuckGoWebSearchService,
    TavilyWebSearchService,
    WebSearchError,
    WebSearchNotConfiguredError,
    _normalize_results,
    _parse_bing_results,
    build_web_search_provider,
)
from sqlalchemy.orm import Session

# 必应结果页的最小样本：两条结果 + 一条缺链接的噪音块。
BING_SAMPLE_PAGE = """
<html><body>
<ol id="b_results">
  <li class="b_algo"><h2><a href="https://example.com/jazz">Jazz &amp; History</a></h2>
    <p>Jazz is a music genre that originated in the African-American communities.</p></li>
  <li class="b_algo"><h2><a href="https://example.com/rock">Rock music</a></h2>
    <p>1 day ago - Rock music is a broad genre of popular music.</p></li>
  <li class="b_algo"><h2><a href="/relative/link">Relative link</a></h2><p>skip me</p></li>
</ol>
</body></html>
"""


class _FakeSearch:
    """记录调用参数的假搜索实现，测试不发真实请求。"""

    def __init__(self, items: list[dict[str, str]] | None = None) -> None:
        """保存待返回结果，并准备记录收到的参数。"""
        self.items = items or []
        self.calls: list[tuple[str, int, str | None]] = []

    def search(self, query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
        """记录参数并返回预设结果。"""
        self.calls.append((query, limit, freshness))
        return self.items


def test_normalize_results_trims_fields_and_snippet() -> None:
    """结果应裁剪为三字段、截断超长摘要、跳过缺少链接的条目。"""
    raw: list[Any] = [
        {"title": " A ", "href": "https://a", "body": "x" * 900},
        {"title": "no url", "href": "", "body": "y"},
        "not a dict",
    ]

    items = _normalize_results(raw, limit=5)

    assert items == [
        {"title": "A", "url": "https://a", "snippet": "x" * MAX_SNIPPET_CHARS},
    ]


def test_normalize_results_respects_limit() -> None:
    """超过 limit 的结果要被丢弃。"""
    raw = [{"title": str(index), "href": f"https://{index}", "body": ""} for index in range(5)]

    items = _normalize_results(raw, limit=2)

    assert [item["title"] for item in items] == ["0", "1"]


def test_normalize_results_extracts_published_date() -> None:
    """摘要开头的日期应抽成 published 字段，正文里不再保留该前缀。"""
    raw: list[Any] = [
        {"title": "A", "href": "https://a", "body": "December 12, 2025 - 瞪鞋摇滚简介"},
        {"title": "B", "href": "https://b", "body": "1 day ago - Shoegaze is a genre"},
    ]

    items = _normalize_results(raw, limit=5)

    assert items[0]["published"] == "December 12, 2025"
    assert items[0]["snippet"] == "瞪鞋摇滚简介"
    assert items[1]["published"] == "1 day ago"
    assert items[1]["snippet"] == "Shoegaze is a genre"


def test_freshness_mapping_matches_search_engine_contract() -> None:
    """freshness 取值必须映射到搜索引擎认识的时间范围缩写。"""
    assert FRESHNESS_TIMELIMIT == {"day": "d", "week": "w", "month": "m", "year": "y"}


def test_normalize_results_rejects_invalid_payload() -> None:
    """返回体不是列表时按搜索失败处理。"""
    with pytest.raises(WebSearchError):
        _normalize_results({"results": []}, limit=3)


def test_disabled_search_raises_deterministic_error(monkeypatch: Any) -> None:
    """关闭联网搜索时抛确定性错误，且不发起任何请求。"""
    monkeypatch.setattr(settings, "web_search_enabled", False)

    with pytest.raises(WebSearchNotConfiguredError):
        DuckDuckGoWebSearchService().search("shoegaze", 3)

    with pytest.raises(WebSearchNotConfiguredError):
        BingCnWebSearchService().search("shoegaze", 3)


def test_parse_bing_results_extracts_title_url_and_snippet() -> None:
    """必应结果块应解析成标题、链接、摘要，并跳过缺链接的条目。"""
    items = _parse_bing_results(BING_SAMPLE_PAGE, limit=5)

    assert [item["title"] for item in items] == ["Jazz & History", "Rock music"]
    assert items[0]["url"] == "https://example.com/jazz"
    assert items[0]["snippet"].startswith("Jazz is a music genre")
    # 日期前缀抽成 published，摘要里不再保留
    assert items[1]["published"] == "1 day ago"
    assert items[1]["snippet"] == "Rock music is a broad genre of popular music."


def test_parse_bing_results_respects_limit() -> None:
    """解析结果条数受 limit 约束。"""
    items = _parse_bing_results(BING_SAMPLE_PAGE, limit=1)

    assert len(items) == 1
    assert items[0]["title"] == "Jazz & History"


def test_bing_search_raises_readable_error_when_page_changes(monkeypatch: Any) -> None:
    """结果页结构变化（解析不到结果）时给出可读错误，而不是静默返回空。"""

    class _Response:
        status_code = 200
        text = "<html><body>没有结果块</body></html>"

        def raise_for_status(self) -> None:
            """模拟正常状态码。"""

    monkeypatch.setattr(
        "app.services.web_search_service.httpx.get",
        lambda *args, **kwargs: _Response(),
    )

    with pytest.raises(WebSearchError, match="结构已变化"):
        BingCnWebSearchService().search("shoegaze", 3)


def test_bing_search_maps_freshness_to_filter(monkeypatch: Any) -> None:
    """freshness 应映射成必应的时间筛选参数。"""
    captured: dict[str, Any] = {}

    class _Response:
        status_code = 200
        text = BING_SAMPLE_PAGE

        def raise_for_status(self) -> None:
            """模拟正常状态码。"""

    def fake_get(url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        captured.update(kwargs.get("params") or {})
        return _Response()

    monkeypatch.setattr("app.services.web_search_service.httpx.get", fake_get)

    items = BingCnWebSearchService().search("shoegaze", 2, "week")

    assert captured["filters"] == f'ex1:"{BING_FRESHNESS_FILTER["week"]}"'
    assert captured["q"] == "shoegaze"
    assert len(items) == 2


def test_provider_factory_follows_config(monkeypatch: Any) -> None:
    """搜索源按配置选择；默认是境内可达的必应中国。"""
    monkeypatch.setattr(settings, "web_search_provider", "bing_cn")
    assert isinstance(build_web_search_provider(), BingCnWebSearchService)

    monkeypatch.setattr(settings, "web_search_provider", "duckduckgo")
    assert isinstance(build_web_search_provider(), DuckDuckGoWebSearchService)

    monkeypatch.setattr(settings, "web_search_provider", "tavily")
    assert isinstance(build_web_search_provider(), TavilyWebSearchService)


class _TavilyResponse:
    """模拟 Tavily 的 HTTP 响应。"""

    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        """保存待返回的负载与状态码。"""
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """状态码非 2xx 时抛出 httpx 的 HTTPStatusError（与真实调用一致）。"""
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.tavily.com/search")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> dict[str, Any]:
        """返回预设负载。"""
        return self._payload


def test_tavily_search_returns_full_content(monkeypatch: Any) -> None:
    """Tavily 返回的是已抽取正文，应保留到更大上限（而不是几十字摘要）。"""
    captured: dict[str, Any] = {}
    payload = {
        "results": [
            {
                "title": "City Pop - 维基百科",
                "url": "https://zh.wikipedia.org/wiki/City_pop",
                "content": "正" * 5000,
            }
        ]
    }

    def fake_post(url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        captured.update(kwargs.get("json") or {})
        return _TavilyResponse(payload)

    monkeypatch.setattr(settings, "web_search_provider", "tavily")
    monkeypatch.setattr(settings, "web_search_api_key", "test-key")
    monkeypatch.setattr("app.services.web_search_service.httpx.post", fake_post)

    items = TavilyWebSearchService().search("City Pop 是什么", 3)

    assert captured["url"] == settings.web_search_tavily_url
    assert captured["api_key"] == "test-key"
    assert captured["include_answer"] is False
    assert len(items) == 1
    assert len(items[0]["snippet"]) == TAVILY_SNIPPET_CHARS


def test_tavily_requires_api_key(monkeypatch: Any) -> None:
    """没有 key 时给确定性错误，不去发请求。"""
    monkeypatch.setattr(settings, "web_search_enabled", True)
    monkeypatch.setattr(settings, "web_search_api_key", "")

    with pytest.raises(WebSearchNotConfiguredError):
        TavilyWebSearchService().search("anything", 3)


def test_tavily_maps_freshness_to_time_range(monkeypatch: Any) -> None:
    """freshness 应映射成 Tavily 的 time_range 参数。"""
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> Any:
        captured.update(kwargs.get("json") or {})
        return _TavilyResponse({"results": [{"title": "t", "url": "https://a", "content": "正文"}]})

    monkeypatch.setattr(settings, "web_search_api_key", "test-key")
    monkeypatch.setattr("app.services.web_search_service.httpx.post", fake_post)

    TavilyWebSearchService().search("music festival", 2, "week")

    assert captured["time_range"] == "week"


def test_tavily_reports_invalid_credentials(monkeypatch: Any) -> None:
    """凭证无效属于确定性失败，不能被当成可重试的网络错误。"""
    monkeypatch.setattr(settings, "web_search_api_key", "bad-key")
    monkeypatch.setattr(
        "app.services.web_search_service.httpx.post",
        lambda *args, **kwargs: _TavilyResponse({}, status_code=401),
    )

    with pytest.raises(WebSearchNotConfiguredError):
        TavilyWebSearchService().search("anything", 3)


def test_tavily_reports_rate_limit_as_retryable(monkeypatch: Any) -> None:
    """额度用尽/限流应归入可重试错误，而不是凭证错误。"""
    monkeypatch.setattr(settings, "web_search_api_key", "test-key")
    monkeypatch.setattr(
        "app.services.web_search_service.httpx.post",
        lambda *args, **kwargs: _TavilyResponse({}, status_code=429),
    )

    with pytest.raises(WebSearchError, match="额度"):
        TavilyWebSearchService().search("anything", 3)


def test_tool_returns_normalized_items(db_session: Session) -> None:
    """工具层应把搜索实现的结果原样归一化后返回。"""
    fake = _FakeSearch([{"title": "t", "url": "https://u", "snippet": "s"}])
    tools = MusicAgentTools(db_session, user_id=1, web_search=fake)

    result = tools.search_web({"query": "shoegaze", "limit": 3})

    assert result == {"items": [{"title": "t", "url": "https://u", "snippet": "s"}], "count": 1}
    assert fake.calls == [("shoegaze", 3, None)]


def test_tool_passes_freshness_to_provider(db_session: Session) -> None:
    """模型要求的时间范围要透传给搜索实现。"""
    fake = _FakeSearch()
    tools = MusicAgentTools(db_session, user_id=1, web_search=fake)

    tools.search_web({"query": "shoegaze", "limit": 2, "freshness": "week"})

    assert fake.calls == [("shoegaze", 2, "week")]


def test_tool_caps_limit_by_config(db_session: Session, monkeypatch: Any) -> None:
    """模型传入的条数不能超过配置上限。"""
    monkeypatch.setattr(settings, "web_search_max_results", 2)
    fake = _FakeSearch()
    tools = MusicAgentTools(db_session, user_id=1, web_search=fake)

    tools.search_web({"query": "shoegaze", "limit": 8})

    assert fake.calls == [("shoegaze", 2, None)]


def test_search_web_is_registered_and_read_only(db_session: Session) -> None:
    """联网搜索以只读工具注册，对模型可见，且合法参数直接放行。"""
    registry = ToolRegistry()
    MusicAgentTools(db_session, user_id=1).register_all(registry)

    tool = registry.get("search_web")
    assert tool is not None
    assert tool.operation is ToolOperation.READ
    assert "search_web" in [item["function"]["name"] for item in registry.definitions()]
    assert (
        evaluate_tool_call(tool, {"query": "shoegaze", "limit": 3}).decision is ToolDecision.ALLOW
    )
