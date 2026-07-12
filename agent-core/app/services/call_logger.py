"""AI call logging decorator for fire-and-forget instrumentation."""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_pending_tasks: set = set()


async def _send_log(**kwargs: Any) -> None:
    """Send a log record to agent-api internal endpoint. Swallows all errors."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.agent_api_base_url}/api/v1/internal/ai-call-logs",
                json=kwargs,
            )
    except Exception as e:
        logger.debug("Failed to send AI call log: %s", e)


def log_ai_call(call_type: str, provider: str):
    """Decorator that logs AI model calls to agent-api.

    Wraps an async method on a client class. Captures duration, status,
    and token usage (from self._last_usage if available).

    Args:
        call_type: One of 'llm', 'vlm', 'embedding', 'image_gen'
        provider: Provider name like 'zhipu', 'siliconflow', 'ollama'
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start = asyncio.get_event_loop().time()
            status = "success"
            error_message = None
            try:
                result = await func(self, *args, **kwargs)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    status = "rate_limited"
                else:
                    status = "failed"
                error_message = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                raise
            except httpx.TimeoutException:
                status = "timeout"
                error_message = "Request timed out"
                raise
            except Exception as e:
                status = "failed"
                error_message = f"{type(e).__name__}: {e}"
                raise
            finally:
                duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
                model = getattr(self, "model", "unknown")
                usage = getattr(self, "_last_usage", None) or {}
                input_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
                output_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
                total_tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0

                log_payload = {
                    "call_type": call_type,
                    "provider": provider,
                    "model": model,
                    "status": status,
                    "duration_ms": duration_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
                if error_message:
                    log_payload["error_message"] = error_message
                project_id = getattr(self, "_log_project_id", None)
                if project_id:
                    log_payload["project_id"] = project_id
                node_name = getattr(self, "_log_node_name", None)
                if node_name:
                    log_payload["node_name"] = node_name

                try:
                    task = asyncio.create_task(_send_log(**log_payload))
                    _pending_tasks.add(task)
                    task.add_done_callback(_pending_tasks.discard)
                except RuntimeError:
                    pass

        return wrapper

    return decorator
