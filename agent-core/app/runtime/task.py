from __future__ import annotations

from app.runtime.models import Task, TaskPlan
from app.agents.registry import AgentConfig


class TaskPlanner:
    def create_plan(self, agent_config: AgentConfig, understanding: dict) -> TaskPlan:
        tasks = []
        for tmpl in agent_config.task_templates:
            tasks.append(Task(
                id=tmpl.id,
                goal=tmpl.id,
                required_fields=tmpl.required_fields,
                dependencies=tmpl.dependencies,
                confidence_threshold=tmpl.confidence_threshold or 0.95,
            ))
        return TaskPlan(tasks=tasks)
