"""Tests for RAG search logging."""
import asyncio
import threading
import time
import pytest
from unittest.mock import AsyncMock, patch
import app.services.rag_logger as rag_logger_mod
from app.services.rag_logger import (
    log_rag_search,
    log_rag_search_sync,
    set_main_loop,
    _send_rag_log,
)


@pytest.fixture(autouse=True)
def _reset_main_loop():
    """Reset the module-level _main_loop before and after each test so the
    lazily-captured loop from one test does not leak into another."""
    saved = rag_logger_mod._main_loop
    rag_logger_mod._main_loop = None
    yield
    rag_logger_mod._main_loop = saved


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


@pytest.mark.asyncio
async def test_log_rag_search_sync_in_async_context():
    """log_rag_search_sync should schedule via create_task when a loop is running."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    with patch("app.services.rag_logger._send_rag_log", side_effect=fake_send):
        log_rag_search_sync(
            project_id="proj-sync-1",
            query_text="async context query",
            search_type="structured",
            result_count=2,
            duration_ms=42,
            cache_hit=False,
            timed_out=False,
        )
        # Yield control so the scheduled task can run.
        await asyncio.sleep(0)

    assert captured == {
        "projectId": "proj-sync-1",
        "queryText": "async context query",
        "searchType": "structured",
        "resultCount": 2,
        "durationMs": 42,
        "cacheHit": False,
        "timedOut": False,
    }


def test_log_rag_search_sync_in_thread_without_running_loop():
    """log_rag_search_sync should use run_coroutine_threadsafe when called from a
    thread pool thread with no running event loop.

    This reproduces the production path: knowledge_retrieval.py calls
    structured_query via loop.run_in_executor, which runs the sync function in a
    worker thread that has no running event loop. The sync wrapper must still
    deliver the log via run_coroutine_threadsafe on the main thread's loop
    (captured via set_main_loop).
    """
    captured = {}
    ready = threading.Event()

    async def fake_send(**kwargs):
        captured.update(kwargs)

    # Run a dedicated event loop in a background "main" thread so we can drive
    # it while the test thread (acting as the worker) calls log_rag_search_sync.
    main_loop = asyncio.new_event_loop()

    def run_main_loop():
        asyncio.set_event_loop(main_loop)
        main_loop.run_forever()

    main_thread = threading.Thread(target=run_main_loop)
    main_thread.start()

    # Register the background loop as the "main" loop, mirroring what
    # main.py's lifespan handler does at app startup.
    set_main_loop(main_loop)
    try:
        # Wait for the main loop to be running.
        deadline = 50
        while not main_loop.is_running() and deadline > 0:
            time.sleep(0.01)
            deadline -= 1
        assert main_loop.is_running(), "main loop failed to start"

        def worker():
            # Inside a worker thread there is no running event loop, so
            # asyncio.create_task would raise RuntimeError. The sync wrapper
            # must fall back to run_coroutine_threadsafe on the captured loop.
            with patch("app.services.rag_logger._send_rag_log", side_effect=fake_send):
                log_rag_search_sync(
                    project_id="proj-thread-1",
                    query_text="thread pool query",
                    search_type="structured",
                    result_count=7,
                    duration_ms=99,
                    cache_hit=True,
                    timed_out=False,
                )
            ready.set()

        t = threading.Thread(target=worker)
        t.start()

        # Wait for the worker to schedule the coroutine via
        # run_coroutine_threadsafe, then give the main loop time to execute it.
        deadline = 100
        while not ready.is_set() and deadline > 0:
            time.sleep(0.01)
            deadline -= 1
        # Allow the scheduled coroutine to actually run on the main loop.
        time.sleep(0.1)

        t.join(timeout=5.0)

        assert ready.is_set(), "worker thread did not signal completion in time"
        assert captured == {
            "projectId": "proj-thread-1",
            "queryText": "thread pool query",
            "searchType": "structured",
            "resultCount": 7,
            "durationMs": 99,
            "cacheHit": True,
            "timedOut": False,
        }
    finally:
        main_loop.call_soon_threadsafe(main_loop.stop)
        main_thread.join(timeout=5.0)
        main_loop.close()
