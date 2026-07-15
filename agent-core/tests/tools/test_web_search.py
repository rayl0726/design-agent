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
