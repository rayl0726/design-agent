import pytest
from app.tools.ask_user import AskUserTool
from app.tools.respond_to_user import RespondToUserTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_ask_user_returns_question():
    tool = AskUserTool()
    ctx = ToolContext(conversation_id="c1", agent_type="generic", working_memory={})
    result = await tool.execute({"question": "预算多少？"}, ctx)
    assert result.observation == "向用户提问"
    assert result.data["question"] == "预算多少？"


@pytest.mark.asyncio
async def test_respond_to_user_returns_answer():
    tool = RespondToUserTool()
    ctx = ToolContext(conversation_id="c1", agent_type="generic", working_memory={})
    result = await tool.execute({"answer": "已完成"}, ctx)
    assert result.data["answer"] == "已完成"
