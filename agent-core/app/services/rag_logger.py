"""RAG search logging for fire-and-forget instrumentation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_pending_tasks: set = set()


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
