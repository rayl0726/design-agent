import pytest
from unittest.mock import AsyncMock, Mock
from app.tools.web_fetcher import fetch_pages


@pytest.mark.asyncio
async def test_fetch_pages_uses_snippet_when_request_fails():
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("timeout")

    results = [
        {"title": "T", "link": "https://example.com", "snippet": "fallback snippet", "source": "bing"},
    ]
    out = await fetch_pages(results, client=mock_client, max_pages=1)
    assert len(out) == 1
    assert out[0]["text"] == "fallback snippet"
    assert out[0]["used_snippet_fallback"] is True


@pytest.mark.asyncio
async def test_fetch_pages_extracts_main_content():
    html = """
    <html><body>
      <nav> nav content </nav>
      <article>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
      </article>
      <footer> footer </footer>
    </body></html>
    """
    mock_client = AsyncMock()
    response = AsyncMock()
    response.text = html
    response.raise_for_status = Mock(return_value=None)
    mock_client.get.return_value = response

    results = [
        {"title": "T", "link": "https://example.com", "snippet": "s", "source": "bing"},
    ]
    out = await fetch_pages(results, client=mock_client, max_pages=1)
    assert out[0]["text"].startswith("First paragraph.")
    assert "nav content" not in out[0]["text"]
    assert out[0]["used_snippet_fallback"] is False


@pytest.mark.asyncio
async def test_fetch_pages_uses_snippet_when_extracted_text_empty():
    mock_client = AsyncMock()
    response = AsyncMock()
    response.text = "<html><body></body></html>"
    response.raise_for_status = Mock(return_value=None)
    mock_client.get.return_value = response

    results = [
        {"title": "T", "link": "https://example.com", "snippet": "fallback snippet", "source": "bing"},
    ]
    out = await fetch_pages(results, client=mock_client, max_pages=1)
    assert out[0]["text"] == "fallback snippet"
    assert out[0]["used_snippet_fallback"] is True
