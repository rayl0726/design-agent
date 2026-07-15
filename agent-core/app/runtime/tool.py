from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Awaitable


@dataclass
class ToolContext:
    conversation_id: str
    agent_type: str
    working_memory: dict[str, Any]
    emit: Callable[[str, dict], Awaitable[None] | None] | None = None


@dataclass
class ToolResult:
    observation: str
    data: dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def execute(self, inputs: dict[str, Any], context: ToolContext) -> ToolResult:
        ...
