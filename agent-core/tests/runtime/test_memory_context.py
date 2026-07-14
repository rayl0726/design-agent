from app.runtime.memory_manager import MemoryManager
from app.runtime.context_manager import ContextManager, AgentContext


class FakeMemoryStore:
    def __init__(self):
        self.data = {}

    async def get(self, cid):
        return self.data.get(cid, {})

    async def set(self, cid, value):
        self.data[cid] = value


def test_context_compression_keeps_key_fields():
    store = FakeMemoryStore()
    mm = MemoryManager(store)
    ctx = AgentContext(
        conversation_id="c1",
        agent_type="meichen",
        user_input="继续",
        working_memory={"theme": "海洋", "space_type": "购物中心中庭", "budget": "15万"},
        recent_messages=[{"role": "user", "content": "hi"}] * 20,
    )
    cm = ContextManager(max_tokens=4000)
    context = cm.build_context(ctx)
    assert "海洋" in context
    assert "购物中心中庭" in context
