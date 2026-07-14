from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class Task:
    id: str
    goal: str
    type: str = "generic"
    required_fields: list[str] = field(default_factory=list)
    success_criteria: str = ""
    confidence_threshold: float = 0.95
    dependencies: list[str] = field(default_factory=list)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: dict[str, Any] = field(default_factory=dict)
    evaluation: Evaluation | None = None


@dataclass
class TaskPlan:
    tasks: list[Task]

    def next_executable(self) -> Task | None:
        completed = {t.id for t in self.tasks if t.status == "completed"}
        for task in self.tasks:
            if task.status == "pending" and set(task.dependencies).issubset(completed):
                return task
        return None

    def mark_complete(self, task_id: str) -> None:
        for task in self.tasks:
            if task.id == task_id:
                task.status = "completed"

    def overall_confidence(self) -> float:
        completed = [t for t in self.tasks if t.status == "completed" and t.evaluation]
        if not completed:
            return 0.0
        return sum(t.evaluation.confidence for t in completed) / len(completed)


@dataclass
class Evaluation:
    confidence: float
    reason: str
    suggested_action: Literal["accept", "retry", "retrieve_more", "ask_user", "fail"]

    def is_acceptable(self, threshold: float) -> bool:
        return self.confidence >= threshold


@dataclass
class ToolCall:
    iteration: int
    tool_name: str
    inputs: dict[str, Any]
    output_summary: str
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentLoopResult:
    final_answer: dict[str, Any]
    tool_calls: list[ToolCall]
    reasoning_trace: list[dict[str, Any]]


@dataclass
class AgentContext:
    conversation_id: str
    agent_type: str
    user_input: str
    working_memory: dict[str, Any] = field(default_factory=dict)
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    conversation_summary: str = ""
    user_profile: dict[str, Any] = field(default_factory=dict)
