import pytest
from unittest.mock import AsyncMock, patch

from app.runtime.agent_loop import AgentLoop
from app.runtime.tool_registry import ToolRegistry
from app.runtime.models import AgentContext
from app.runtime.request_analyzer import RequestAnalyzer
from app.agents.registry import AgentRegistry
from app.tools.ask_user import AskUserTool
from app.tools.respond_to_user import RespondToUserTool
from app.tools.invoke_meichen_workflow import InvokeMeichenWorkflowTool


REGISTRY_YAML = """
agents:
  - id: meichen
    name: 美陈 Agent
    enabled: true
    handler_class: app.agents.meichen.agent.MeichenAgent
    task_templates:
      - id: information_gathering
        required_fields: [theme, space_type, budget]
      - id: generate_ideas
        dependencies: [information_gathering]
"""


@pytest.mark.asyncio
async def test_generic_agent_invokes_meichen_workflow(tmp_path):
    path = tmp_path / "agents.yaml"
    path.write_text(REGISTRY_YAML, encoding="utf-8")
    registry = AgentRegistry.load(str(path))

    tool_registry = ToolRegistry()
    tool_registry.register(AskUserTool())
    tool_registry.register(RespondToUserTool())
    tool_registry.register(InvokeMeichenWorkflowTool())

    with patch("app.agents.meichen.workflow.run_meichen_workflow", new_callable=AsyncMock) as mock:
        mock.return_value = {"l2_output": {"ideas": [{"name": "海洋之梦"}]}}
        analyzer = RequestAnalyzer(registry)
        ctx = AgentContext(
            conversation_id="c1",
            agent_type="meichen",
            user_input="海洋主题购物中心中庭，预算15万",
        )
        plan = await analyzer.analyze(ctx)
        loop = AgentLoop(tool_registry, max_iterations=3)
        result = await loop.run(ctx, plan)
        assert "l2_output" in result.final_answer or result.final_answer.get("status") == "incomplete"
        mock.assert_awaited_once()
