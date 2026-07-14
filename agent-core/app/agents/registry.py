from __future__ import annotations
import yaml
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskTemplate:
    id: str
    required_fields: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    confidence_threshold: float | None = None
    success_criteria: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskTemplate":
        return cls(
            id=data["id"],
            required_fields=data.get("required_fields", []),
            dependencies=data.get("dependencies", []),
            confidence_threshold=data.get("confidence_threshold"),
            success_criteria=data.get("success_criteria", ""),
        )


@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    default: bool
    enabled: bool
    handler_class: str
    task_templates: list[TaskTemplate] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            default=data.get("default", False),
            enabled=data.get("enabled", True),
            handler_class=data["handler_class"],
            task_templates=[TaskTemplate.from_dict(t) for t in data.get("task_templates", [])],
            tools=data.get("tools", []),
        )


class AgentRegistry:
    def __init__(self, agents: dict[str, AgentConfig]):
        self._agents = agents

    @classmethod
    def load(cls, path: str) -> "AgentRegistry":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        agents = {
            a["id"]: AgentConfig.from_dict(a)
            for a in data.get("agents", [])
        }
        return cls(agents)

    def get(self, agent_id: str) -> AgentConfig | None:
        agent = self._agents.get(agent_id)
        return agent if agent and agent.enabled else None

    def list_enabled(self) -> list[AgentConfig]:
        return [a for a in self._agents.values() if a.enabled]

    def default_agent(self) -> AgentConfig:
        defaults = [a for a in self.list_enabled() if a.default]
        if defaults:
            return defaults[0]
        enabled = self.list_enabled()
        if not enabled:
            raise ValueError("No enabled agents in registry")
        return enabled[0]
