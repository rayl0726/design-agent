import pytest

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.taxonomy_loader import load_taxonomy


class _ThrowingFewShot:
    async def retrieve(self, space_type=None, theme=None, top_k=3):
        raise RuntimeError("embedding API 429")


class _StubLLM:
    async def complete(self, system_prompt, user_prompt, json_mode=False, temperature=0.7):
        return '{"space_type": null, "theme": "圣诞节"}'


@pytest.mark.asyncio
async def test_extract_swallows_few_shot_failure():
    extractor = IntentLLMExtractor(
        taxonomy=load_taxonomy(),
        llm_client=_StubLLM(),
        few_shot_library=_ThrowingFewShot(),
    )
    # Must not raise; few-shot failure is non-fatal
    result = await extractor.extract("圣诞节")
    assert result is not None
    assert result.theme == "圣诞节"
