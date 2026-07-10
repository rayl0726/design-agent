import pytest

from app.services.intent_recognition import IntentRecognitionService


class DummyLLMClient:
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return '{"theme": "情人节"}'


@pytest.mark.asyncio
async def test_merge_rule_fallback_for_missing_space_and_budget():
    service = IntentRecognitionService(
        llm_client=DummyLLMClient(),
    )
    result = await service.recognize("情人节快闪店30万")
    assert result.theme.value == "情人节"
    assert result.space_type.value == "快闪店"
    assert result.budget.value == 300000
    assert result.trace_id is not None
