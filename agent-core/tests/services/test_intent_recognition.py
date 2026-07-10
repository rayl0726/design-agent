from __future__ import annotations

import pytest

from app.services.intent_recognition import IntentRecognitionService, _merge_intent_outputs
from app.services.intent_schemas import IntentOutput


class DummyLLMClient:
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return '{"theme": "情人节"}'


class DummySemanticMatcher:
    async def match(self, text: str, field_type: str) -> tuple[str | None, float]:
        return None, 0.0


@pytest.mark.asyncio
async def test_merge_rule_fallback_for_missing_space_and_budget():
    service = IntentRecognitionService(
        llm_client=DummyLLMClient(),
        semantic_matcher=DummySemanticMatcher(),
    )
    result = await service.recognize("情人节快闪店30万")
    assert result.theme.value == "情人节"
    assert result.space_type.value == "快闪店"
    assert result.budget.value == 300000
    assert result.trace_id is not None


def test_merge_prefers_llm_scalar():
    llm = IntentOutput(theme="情人节")
    rule = IntentOutput(theme="春节")
    merged = _merge_intent_outputs(llm, rule)
    assert merged.theme == "情人节"


def test_merge_fills_missing_scalar_from_rule():
    llm = IntentOutput(theme=None)
    rule = IntentOutput(theme="春节")
    merged = _merge_intent_outputs(llm, rule)
    assert merged.theme == "春节"


def test_merge_fills_list_fields_from_rule():
    llm = IntentOutput(points=[])
    rule = IntentOutput(points=["中庭"])
    merged = _merge_intent_outputs(llm, rule)
    assert merged.points == ["中庭"]


def test_merge_keeps_llm_list_when_present():
    llm = IntentOutput(points=["门头"])
    rule = IntentOutput(points=["中庭"])
    merged = _merge_intent_outputs(llm, rule)
    assert merged.points == ["门头"]


def test_merge_uses_rule_when_llm_output_is_none():
    rule = IntentOutput(space_type="快闪店", budget="30万")
    merged = _merge_intent_outputs(None, rule)
    assert merged.space_type == "快闪店"
    assert merged.budget == "30万"


def test_merge_returns_defaults_when_both_empty():
    merged = _merge_intent_outputs(IntentOutput(), IntentOutput())
    assert merged.theme is None
    assert merged.points == []
    assert merged.material_restrictions == []
