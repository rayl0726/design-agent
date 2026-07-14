import pytest
from app.runtime.request_analyzer import RequestAnalyzer
from app.runtime.models import AgentContext
from app.agents.registry import AgentRegistry

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
async def test_analyzer_creates_meichen_plan(tmp_path):
    path = tmp_path / "agents.yaml"
    path.write_text(REGISTRY_YAML, encoding="utf-8")
    registry = AgentRegistry.load(str(path))
    analyzer = RequestAnalyzer(registry)
    ctx = AgentContext(
        conversation_id="c1",
        agent_type="meichen",
        user_input="海洋主题购物中心中庭，预算15万",
    )
    plan = await analyzer.analyze(ctx)
    assert any(t.id == "information_gathering" for t in plan.tasks)
    assert any(t.id == "generate_ideas" for t in plan.tasks)


@pytest.mark.asyncio
async def test_analyzer_raises_for_unknown_agent(tmp_path):
    path = tmp_path / "agents.yaml"
    path.write_text(REGISTRY_YAML, encoding="utf-8")
    registry = AgentRegistry.load(str(path))
    analyzer = RequestAnalyzer(registry)
    ctx = AgentContext(
        conversation_id="c1",
        agent_type="unknown",
        user_input="海洋主题购物中心中庭，预算15万",
    )
    with pytest.raises(ValueError, match="Unknown agent: unknown"):
        await analyzer.analyze(ctx)
