"""Tests for @log_ai_call decorator."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.call_logger import log_ai_call, _send_log


@pytest.mark.asyncio
async def test_decorator_success_logs_correctly():
    """Decorator should send a success log with correct fields."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    class FakeClient:
        model = "GLM-4.7-Flash"
        _last_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            return "result"

    with patch("app.services.call_logger._send_log", side_effect=fake_send):
        client = FakeClient()
        result = await client.complete("sys", "user")

    assert result == "result"
    assert captured["call_type"] == "llm"
    assert captured["provider"] == "zhipu"
    assert captured["model"] == "GLM-4.7-Flash"
    assert captured["status"] == "success"
    assert captured["duration_ms"] >= 0
    assert captured["input_tokens"] == 100
    assert captured["output_tokens"] == 50
    assert captured["total_tokens"] == 150


@pytest.mark.asyncio
async def test_decorator_failed_logs_error():
    """Decorator should log failed status when exception is raised."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    class FakeClient:
        model = "GLM-4.7-Flash"

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            raise RuntimeError("API error")

    with patch("app.services.call_logger._send_log", side_effect=fake_send):
        client = FakeClient()
        with pytest.raises(RuntimeError):
            await client.complete("sys", "user")

    assert captured["status"] == "failed"
    assert "API error" in captured["error_message"]


@pytest.mark.asyncio
async def test_decorator_swallows_send_errors():
    """Decorator should not raise if _send_log fails."""
    class FakeClient:
        model = "GLM-4.7-Flash"

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            return "ok"

    async def failing_send(**kwargs):
        raise ConnectionError("network down")

    with patch("app.services.call_logger._send_log", side_effect=failing_send):
        client = FakeClient()
        result = await client.complete("sys", "user")

    assert result == "ok"


@pytest.mark.asyncio
async def test_send_log_posts_to_correct_url():
    """_send_log should POST to agent-api internal endpoint."""
    import httpx
    from app.services.call_logger import _send_log

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        await _send_log(
            call_type="llm",
            provider="zhipu",
            model="GLM-4.7-Flash",
            status="success",
            duration_ms=100,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )

    assert mock_post.called
    call_args = mock_post.call_args
    assert "/api/v1/internal/ai-call-logs" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["call_type"] == "llm"
    assert body["provider"] == "zhipu"
