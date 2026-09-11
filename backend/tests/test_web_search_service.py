"""联网搜索工具与结果归一化测试。"""

from __future__ import annotations

from typing import Any

import pytest
from app.core.config import settings
from app.services.agent.music_tools import MusicAgentTools
from app.services.agent.policy import ToolDecision, evaluate_tool_call
from app.services.agent.registry import ToolOperation, ToolRegistry
from app.services.web_search_service import (
    FRESHNESS_TIMELIMIT,
    MAX_SNIPPET_CHARS,
    DuckDuckGoWebSearchService,
    WebSearchError,
    WebSearchNotConfiguredError,
    _normalize_results,
)
from sqlalchemy.orm import Session


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
    """关闭联网搜索时抛确定性错误，且不导入第三方依赖。"""
    monkeypatch.setattr(settings, "web_search_enabled", False)

    with pytest.raises(WebSearchNotConfiguredError):
        DuckDuckGoWebSearchService().search("shoegaze", 3)


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
