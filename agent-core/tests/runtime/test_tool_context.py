from app.runtime.tool import ToolContext
import pytest


@pytest.mark.asyncio
async def test_tool_context_emit_callback_is_invoked():
    called = {"event": None, "payload": None}

    async def emit(event, payload):
        called["event"] = event
        called["payload"] = payload

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
    )

    await ctx.emit("tool_progress", {"status": "searching"})

    assert called["event"] == "tool_progress"
    assert called["payload"]["status"] == "searching"


def test_tool_context_without_emit_still_works():
    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
    )
    assert ctx.emit is None
    assert ctx.conversation_id == "c1"
    assert ctx.tool_call_id is None


def test_tool_context_accepts_tool_call_id():
    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        tool_call_id="call_abc123",
    )
    assert ctx.tool_call_id == "call_abc123"
