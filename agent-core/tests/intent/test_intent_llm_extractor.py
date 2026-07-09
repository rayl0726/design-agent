from unittest.mock import AsyncMock

import pytest

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.learning.few_shot_library import Example, FewShotLibrary


@pytest.mark.asyncio
async def test_extractor_includes_few_shot_examples(monkeypatch):
    lib = FewShotLibrary(data_dir="/tmp/few_shot_test")
    monkeypatch.setattr(
        lib,
        "retrieve",
        AsyncMock(
            return_value=[
                Example(input_text="圣诞节 30万 中庭", space_type="购物中心中庭", theme="圣诞节"),
            ]
        ),
    )

    extractor = IntentLLMExtractor(few_shot_library=lib)
    extractor.taxonomy = AsyncMock()
    extractor._llm_client = AsyncMock()
    extractor._llm_client.complete = AsyncMock(
        return_value='{"space_type":"购物中心中庭","theme":"圣诞节"}'
    )

    await extractor.extract("圣诞节 中庭")
    call_args = extractor._llm_client.complete.call_args.kwargs
    prompt = call_args["user_prompt"]
    assert "圣诞节 30万 中庭" in prompt
