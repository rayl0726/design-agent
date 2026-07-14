from __future__ import annotations
from dataclasses import dataclass
from app.runtime.models import AgentContext


@dataclass
class ContextManager:
    max_tokens: int = 4000
    summary_turn_threshold: int = 5
    compress_turn_threshold: int = 15

    def build_context(self, ctx: AgentContext) -> str:
        parts = []
        parts.append(self._system_prompt(ctx.agent_type))
        if ctx.user_profile:
            parts.append(f"User Profile: {ctx.user_profile}")
        if ctx.conversation_summary:
            parts.append(f"Conversation Summary: {ctx.conversation_summary}")
        recent = self._compress_messages(ctx.recent_messages)
        for msg in recent:
            parts.append(f"{msg['role']}: {msg['content']}")
        if ctx.working_memory:
            parts.append(f"Working Memory: {ctx.working_memory}")
        parts.append(f"User: {ctx.user_input}")
        context = "\n".join(parts)
        return self._truncate(context)

    def _system_prompt(self, agent_type: str) -> str:
        return f"You are a helpful assistant. Current agent mode: {agent_type}."

    def _compress_messages(self, messages: list) -> list:
        if len(messages) > self.compress_turn_threshold:
            return messages[-3:]
        if len(messages) > self.summary_turn_threshold:
            return messages[-5:]
        return messages

    def _truncate(self, text: str) -> str:
        # Naive token estimation: 1 token ~= 4 chars for CJK
        if len(text) > self.max_tokens * 4:
            return text[: self.max_tokens * 4]
        return text
