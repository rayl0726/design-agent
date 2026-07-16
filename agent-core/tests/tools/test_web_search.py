import pytest
from unittest.mock import AsyncMock
from app.tools.web_search import WebSearchTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_web_search_emits_progress_and_returns_summary():
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
        tool_call_id="call_abc123",
    )

    tool = WebSearchTool()
    # Mock 内部客户端
    tool.bing_client = AsyncMock()
    tool.baidu_client = AsyncMock()
    tool.fetcher = AsyncMock()
    tool.summarizer = AsyncMock()

    tool.bing_client.search.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "snippet": "bing snippet", "source": "bing"}
    ]
    tool.baidu_client.search.return_value = []
    tool.fetcher.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "text": "fetched text", "used_snippet_fallback": False}
    ]
    tool.summarizer.return_value = "摘要结果。"

    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "摘要结果。" in result.observation
    events = [e for e, _ in emitted]
    assert "tool_progress" in events
    assert any(p.get("status") == "summarizing" for _, p in emitted)

    progress_payloads = [p for e, p in emitted if e == "tool_progress"]
    assert all(p.get("id") == "call_abc123" for p in progress_payloads)


@pytest.mark.asyncio
async def test_web_search_fewer_than_three_results_handles_gracefully():
    """当两个来源返回的结果合计不足 3 条时，应优雅返回现有结果。"""
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
        tool_call_id="call_few",
    )

    tool = WebSearchTool()
    tool.bing_client = AsyncMock()
    tool.baidu_client = AsyncMock()
    tool.fetcher = AsyncMock()
    tool.summarizer = AsyncMock()

    tool.bing_client.search.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "snippet": "bing snippet", "source": "bing"}
    ]
    tool.baidu_client.search.return_value = [
        {"title": "Baidu Title", "link": "https://baidu.com", "snippet": "baidu snippet", "source": "baidu"}
    ]
    tool.fetcher.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "text": "fetched text", "used_snippet_fallback": False}
    ]
    tool.summarizer.return_value = "摘要结果。"

    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "摘要结果。" in result.observation
    assert len(result.data["results"]) == 2
    assert tool.bing_client.search.call_args.kwargs["limit"] >= 10
    assert tool.baidu_client.search.call_args.kwargs["limit"] >= 10


@pytest.mark.asyncio
async def test_web_search_includes_source_failure_note():
    """当某个搜索源失败时，结果中应包含仅使用可用源的说明。"""
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
        tool_call_id="call_fail",
    )

    tool = WebSearchTool()
    tool.bing_client = AsyncMock()
    tool.baidu_client = AsyncMock()
    tool.fetcher = AsyncMock()
    tool.summarizer = AsyncMock()

    tool.bing_client.search.side_effect = RuntimeError("bing down")
    tool.baidu_client.search.return_value = [
        {"title": "Baidu Title", "link": "https://baidu.com", "snippet": "baidu snippet", "source": "baidu"}
    ]
    tool.fetcher.return_value = [
        {"title": "Baidu Title", "link": "https://baidu.com", "text": "fetched text", "used_snippet_fallback": False}
    ]
    tool.summarizer.return_value = "摘要结果。"

    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "Bing 搜索源暂时不可用" in result.observation
    assert "仅来自 Baidu" in result.observation
    assert "摘要结果。" in result.observation


@pytest.mark.asyncio
async def test_web_search_ensures_at_least_three_results():
    """当原始结果充足时，应至少保留 3 条有效结果。"""
    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=None,
        tool_call_id="call_three",
    )

    tool = WebSearchTool()
    tool.bing_client = AsyncMock()
    tool.baidu_client = AsyncMock()
    tool.fetcher = AsyncMock()
    tool.summarizer = AsyncMock()

    tool.bing_client.search.return_value = [
        {"title": "Bing 1", "link": "https://b1.com", "snippet": "s1", "source": "bing"},
        {"title": "Bing 2", "link": "https://b2.com", "snippet": "s2", "source": "bing"},
    ]
    tool.baidu_client.search.return_value = [
        {"title": "Baidu 1", "link": "https://bd1.com", "snippet": "s3", "source": "baidu"},
        {"title": "Baidu 2", "link": "https://bd2.com", "snippet": "s4", "source": "baidu"},
    ]
    tool.fetcher.return_value = [
        {"title": "Bing 1", "link": "https://b1.com", "text": "t1", "used_snippet_fallback": False}
    ]
    tool.summarizer.return_value = "摘要结果。"

    result = await tool.execute({"query": "北京天气"}, ctx)

    assert len(result.data["results"]) == 3


@pytest.mark.asyncio
async def test_web_search_empty_query_returns_chinese_message():
    """空查询应返回中文提示。"""
    tool = WebSearchTool()
    result = await tool.execute({"query": "   "}, None)

    assert result.observation == "查询词为空"
    assert result.data["results"] == []
