import pytest
from unittest.mock import AsyncMock
from app.tools.web_summarizer import summarize


@pytest.mark.asyncio
async def test_summarize_returns_llm_output_with_sources():
    mock_client = AsyncMock()
    mock_client.complete.return_value = "这是摘要。"

    fetched = [
        {"title": "T1", "link": "https://a.com", "text": "正文一", "used_snippet_fallback": False},
        {"title": "T2", "link": "https://b.com", "text": "正文二", "used_snippet_fallback": True},
    ]
    result = await summarize("北京天气", fetched, mock_client)

    assert "这是摘要。" in result
    assert "1. T1" in result
    assert "https://a.com" in result
    assert "2. T2" in result
    assert "https://b.com" in result


@pytest.mark.asyncio
async def test_summarize_fallback_when_llm_fails():
    mock_client = AsyncMock()
    mock_client.complete.side_effect = Exception("rate limit")

    fetched = [
        {"title": "T1", "link": "https://a.com", "text": "正文一", "used_snippet_fallback": False},
    ]
    result = await summarize("北京天气", fetched, mock_client)

    assert "未能生成摘要" in result
    assert "https://a.com" in result
    assert "正文一" in result
    assert "链接：" in result
    assert "1. T1" in result
