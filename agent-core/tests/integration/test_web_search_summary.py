import pytest
from app.tools.web_search import WebSearchTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_web_search_end_to_end_with_mock_clients():
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    tool = WebSearchTool()

    # Mock clients to avoid real HTTP in CI
    class FakeClient:
        async def search(self, query, limit=5):
            return [
                {"title": f"{query} 结果1", "link": "https://example.com/1", "snippet": "摘要1", "source": "bing"},
                {"title": f"{query} 结果2", "link": "https://example.com/2", "snippet": "摘要2", "source": "baidu"},
            ]

    tool.bing_client = FakeClient()
    tool.baidu_client = FakeClient()
    async def fake_fetcher(*args, **kwargs):
        return [
            {"title": "结果1", "link": "https://example.com/1", "text": "正文1", "used_snippet_fallback": False},
        ]

    async def fake_summarizer(query, fetched, client):
        return f"关于 {query} 的摘要。"

    tool.fetcher = fake_fetcher
    tool.summarizer = fake_summarizer

    ctx = ToolContext("c1", "generic", {}, emit=emit)
    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "北京天气" in result.observation
    assert any(e == "tool_progress" for e, _ in emitted)
