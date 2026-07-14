# agent-core/tests/agents/test_registry.py
from app.agents.registry import AgentRegistry

REGISTRY_YAML = """
agents:
  - id: generic
    name: 通用 Agent
    description: 通用问题求解
    default: true
    enabled: true
    handler_class: app.agents.generic.agent.GenericAgent
    task_templates:
      - id: understand
      - id: plan
    tools:
      - ask_user
      - respond_to_user
  - id: meichen
    name: 美陈 Agent
    enabled: true
    handler_class: app.agents.meichen.agent.MeichenAgent
    task_templates:
      - id: information_gathering
        required_fields: [theme, space_type, budget]
    tools:
      - ask_user
      - invoke_meichen_workflow
  - id: football
    name: 足球数据 Agent
    enabled: false
    handler_class: app.agents.football.agent.FootballAgent
    task_templates: []
    tools: []
"""


def test_registry_loads_enabled_agents(tmp_path):
    path = tmp_path / "agents.yaml"
    path.write_text(REGISTRY_YAML, encoding="utf-8")
    registry = AgentRegistry.load(str(path))
    assert len(registry.list_enabled()) == 2
    assert registry.default_agent().id == "generic"
    assert registry.get("meichen").task_templates[0].required_fields == ["theme", "space_type", "budget"]
    assert registry.get("football") is None  # disabled not returned
