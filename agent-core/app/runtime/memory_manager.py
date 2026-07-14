from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


class MemoryStore(Protocol):
    async def get(self, conversation_id: str) -> dict[str, Any]: ...
    async def set(self, conversation_id: str, value: dict[str, Any]) -> None: ...


@dataclass
class MemoryManager:
    store: MemoryStore

    async def load(self, conversation_id: str) -> dict[str, Any]:
        return await self.store.get(conversation_id)

    async def save(self, conversation_id: str, state: dict[str, Any]) -> None:
        await self.store.set(conversation_id, state)
