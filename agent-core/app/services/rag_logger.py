"""RAG search logging for fire-and-forget instrumentation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_pending_tasks: set = set()

# Reference to the main thread's event loop, captured so that sync callers
# running in thread pool threads (e.g. via loop.run_in_executor) can schedule
# log coroutines via asyncio.run_coroutine_threadsafe. Set explicitly via
# set_main_loop() at app startup, and auto-captured lazily by log_rag_search().
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Capture a reference to the main thread's event loop.

    Should be called once at app startup (e.g. from the FastAPI lifespan
    handler) so that sync code running in thread pool threads can schedule
    fire-and-forget log coroutines via run_coroutine_threadsafe.
    """
    global _main_loop
    _main_loop = loop


async def _send_rag_log(**kwargs: Any) -> None:
    """Send a RAG search log record to agent-api. Swallows all errors."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.agent_api_base_url}/api/v1/internal/rag-search-logs",
                json=kwargs,
            )
    except Exception as e:
        logger.debug("Failed to send RAG search log: %s", e)


async def log_rag_search(
    *,
    project_id: str | None,
    query_text: str,
    search_type: str,
    result_count: int,
    duration_ms: int,
    cache_hit: bool = False,
    timed_out: bool = False,
) -> None:
    """Log a RAG search operation. Fire-and-forget, swallows all errors."""
    # Lazily capture the running loop so sync callers in thread pool threads
    # can use it later via log_rag_search_sync.
    global _main_loop
    if _main_loop is None:
        try:
            _main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
    payload = {
        "projectId": project_id,
        "queryText": query_text,
        "searchType": search_type,
        "resultCount": result_count,
        "durationMs": duration_ms,
        "cacheHit": cache_hit,
        "timedOut": timed_out,
    }
    try:
        task = asyncio.create_task(_send_rag_log(**payload))
        _pending_tasks.add(task)
        task.add_done_callback(_pending_tasks.discard)
    except RuntimeError:
        pass


def log_rag_search_sync(
    *,
    project_id: str | None,
    query_text: str,
    search_type: str,
    result_count: int,
    duration_ms: int,
    cache_hit: bool = False,
    timed_out: bool = False,
) -> None:
    """Sync wrapper for log_rag_search — works from both sync and async contexts.

    Use this from sync code that may be called from either a coroutine (running
    event loop present) or a thread pool thread (no running loop, e.g. via
    ``loop.run_in_executor``). In the async case it schedules via
    ``asyncio.create_task``; in the thread case it schedules via
    ``asyncio.run_coroutine_threadsafe`` on the main thread's event loop
    (captured at startup via set_main_loop() or lazily by log_rag_search()).
    """
    payload = {
        "projectId": project_id,
        "queryText": query_text,
        "searchType": search_type,
        "resultCount": result_count,
        "durationMs": duration_ms,
        "cacheHit": cache_hit,
        "timedOut": timed_out,
    }
    # Try the async-context path first: create_task requires a running loop.
    coro = _send_rag_log(**payload)
    try:
        task = asyncio.create_task(coro)
        _pending_tasks.add(task)
        task.add_done_callback(_pending_tasks.discard)
        return
    except RuntimeError:
        # No running event loop in the current thread — close the orphaned
        # coroutine to avoid a "coroutine was never awaited" warning, then
        # fall through to the thread-safe path below.
        coro.close()
    # Thread context (e.g. run_in_executor): schedule on the main thread's
    # event loop via run_coroutine_threadsafe, using the captured reference.
    loop = _main_loop
    if loop is not None and loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(_send_rag_log(**payload), loop)
        except RuntimeError:
            # Loop stopped between the is_running check and the call — give up
            # silently. Logging is best-effort and must never break the caller.
            pass
