import pytest
from app.runtime.agent_loop import AgentLoop
from app.runtime.models import AgentContext, TaskPlan, Task
from app.runtime.tool import BaseTool, ToolContext, ToolResult
from app.runtime.tool_registry import ToolRegistry

class DummyFinalTool(BaseTool):
    name = "respond_to_user"
    description = "final response"
    parameters = {}

    async def execute(self, inputs, context):
        return ToolResult(observation="done", data={"answer": "ok"})

@pytest.mark.asyncio
async def test_loop_terminates_on_respond():
    registry = ToolRegistry()
    registry.register(DummyFinalTool())
    loop = AgentLoop(registry, max_iterations=5)
    context = AgentContext(conversation_id="c1", agent_type="generic", user_input="hi")
    plan = TaskPlan(tasks=[Task(id="t1", goal="respond", dependencies=[])])
    result = await loop.run(context, plan)
    assert result.final_answer["answer"] == "ok"
