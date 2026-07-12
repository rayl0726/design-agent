"""Tests for RAG search logging."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from app.services.rag_logger import log_rag_search, _send_rag_log


@pytest.mark.asyncio
async def test_log_rag_search_sends_correct_payload():
    """log_rag_search should fire-and-forget with correct camelCase payload."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    with patch("app.services.rag_logger._send_rag_log", side_effect=fake_send):
        await log_rag_search(
            project_id="proj-1",
            query_text="modern office design",
            search_type="semantic",
            result_count=5,
            duration_ms=120,
            cache_hit=False,
            timed_out=False,
        )
        await asyncio.sleep(0)

    assert captured == {
        "projectId": "proj-1",
        "queryText": "modern office design",
        "searchType": "semantic",
        "resultCount": 5,
        "durationMs": 120,
        "cacheHit": False,
        "timedOut": False,
    }


@pytest.mark.asyncio
async def test_log_rag_search_swallows_errors():
    """log_rag_search should not raise if _send_rag_log fails."""
    async def failing_send(**kwargs):
        raise ConnectionError("network down")

    with patch("app.services.rag_logger._send_rag_log", side_effect=failing_send):
        # Should not raise
        await log_rag_search(
            project_id="proj-1",
            query_text="test",
            search_type="fallback",
            result_count=0,
            duration_ms=0,
            cache_hit=False,
            timed_out=True,
        )
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_send_rag_log_posts_to_correct_url():
    """_send_rag_log should POST to agent-api internal endpoint."""
    from unittest.mock import MagicMock

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        await _send_rag_log(
            projectId="proj-1",
            queryText="test query",
            searchType="semantic",
            resultCount=3,
            durationMs=50,
            cacheHit=False,
            timedOut=False,
        )

    assert mock_post.called
    call_args = mock_post.call_args
    assert "/api/v1/internal/rag-search-logs" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["projectId"] == "proj-1"
    assert body["queryText"] == "test query"
    assert body["searchType"] == "semantic"
