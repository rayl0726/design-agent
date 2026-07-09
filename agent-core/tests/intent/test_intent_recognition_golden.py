from __future__ import annotations

import os

import pytest

from app.services.intent_recognition import IntentRecognitionService


@pytest.fixture
def service() -> IntentRecognitionService:
    return IntentRecognitionService()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_theme_christmas(service: IntentRecognitionService) -> None:
    result = await service.recognize("圣诞节主题，购物中心中庭，预算30万")
    assert result.theme is not None
    assert "圣诞" in str(result.theme.value)
    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"
    assert result.budget is not None
    assert result.budget.value == 300000


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_budget_variants(service: IntentRecognitionService) -> None:
    result = await service.recognize("二十万到三十万，快闪店，新春主题")
    assert result.budget is not None
    assert 200000 <= int(result.budget.value) <= 300000


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_alias_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("商场中庭，预算15万，国潮主题")
    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_material_restrictions(service: IntentRecognitionService) -> None:
    result = await service.recognize("购物中心中庭，不要真植物，亚克力可以，预算20万，春天主题")
    assert result.material_restrictions
    restriction_names = [str(m.value) for m in result.material_restrictions]
    assert any("真植物" in name for name in restriction_names)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_context_inheritance(service: IntentRecognitionService) -> None:
    previous = await service.recognize("购物中心中庭，国潮风格，预算30万，春节主题")
    current = await service.recognize("预算加到50万", previous_intent=previous)
    assert current.space_type is not None
    assert current.space_type.value == "购物中心中庭"
    assert current.budget is not None
    assert current.budget.value == 500000


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ZHIPU_API_KEY") and not os.environ.get("SKIP_LLM_TESTS"),
    reason="ZHIPU_API_KEY not set",
)
async def test_clarification_for_unknown_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("做个美陈")
    assert result.clarification is not None
    assert result.clarification.needs_clarification is True
    assert "space_type" in result.clarification.missing_fields
