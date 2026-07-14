from __future__ import annotations

from app.runtime.models import AgentContext, TaskPlan
from app.agents.registry import AgentRegistry
from app.runtime.task import TaskPlanner


class RequestAnalyzer:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.planner = TaskPlanner()

    async def analyze(self, context: AgentContext) -> TaskPlan:
        agent_config = self.registry.get(context.agent_type)
        if not agent_config:
            raise ValueError(f"Unknown agent: {context.agent_type}")
        # TODO: replace with LLM structured output in production
        extracted_fields = self._extract_fields(context.user_input)
        context.working_memory["extracted_fields"] = extracted_fields
        understanding = {
            "agent_mode": agent_config.id,
            "intent": "design" if "meichen" in context.user_input or agent_config.id == "meichen" else "chat",
            "extracted_fields": extracted_fields,
        }
        return self.planner.create_plan(agent_config, understanding)

    def _extract_fields(self, text: str) -> dict:
        fields = {}
        if "海洋" in text:
            fields["theme"] = "海洋"
        if "购物中心中庭" in text:
            fields["space_type"] = "购物中心中庭"
        if "15万" in text:
            fields["budget"] = "15万"
        return fields
