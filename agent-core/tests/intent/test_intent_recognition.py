from __future__ import annotations

import pytest

from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_recognition_result import FieldSource, IntentRecognitionResult, RecognizedField
from app.services.semantic_matcher import SemanticMatcher


class DummyLLMClient:
    def __init__(self, response: str = "{}") -> None:
        self.response = response

    async def complete(self, system: str, prompt: str, json_mode: bool = True) -> str:
        return self.response


class DummySemanticMatcher(SemanticMatcher):
    def __init__(self) -> None:
        pass

    async def match(self, text: str, field_type: str) -> tuple[str | None, float]:
        return None, 0.0


@pytest.fixture
def service() -> IntentRecognitionService:
    return IntentRecognitionService(
        llm_client=DummyLLMClient(),
        semantic_matcher=DummySemanticMatcher(),
    )


@pytest.mark.asyncio
async def test_exact_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("购物中心中庭海洋主题")
    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"
    assert result.space_type.source == FieldSource.EXACT


@pytest.mark.asyncio
async def test_alias_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("popup store 快闪")
    assert result.space_type is not None
    assert result.space_type.value == "快闪店"
    assert result.space_type.source == FieldSource.ALIAS


@pytest.mark.asyncio
async def test_fuzzy_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("百货入口国潮美陈")
    assert result.space_type is not None
    assert result.space_type.value == "百货入口"


@pytest.mark.asyncio
async def test_extract_budget(service: IntentRecognitionService) -> None:
    result = await service.recognize("购物中心中庭，预算15万")
    assert result.budget is not None
    assert result.budget.value == 150000


@pytest.mark.asyncio
async def test_match_points(service: IntentRecognitionService) -> None:
    result = await service.recognize("新春快闪店，门头×2，DP点×3")
    names = [str(p.value.get("name", "")) for p in result.points]
    assert "门头" in names
    assert "DP点" in names


@pytest.mark.asyncio
async def test_apply_defaults(service: IntentRecognitionService) -> None:
    result = await service.recognize("快闪店")
    result = service.apply_defaults(result)
    names = [str(p.value.get("name")) for p in result.points]
    assert "门头" in names
    assert "DP点" in names
    assert "合影墙" in names
    assert result.timeline is not None


def test_fill_missing_from_context(service: IntentRecognitionService) -> None:
    previous = IntentRecognitionResult(
        style=RecognizedField(name="style", value="国潮", source=FieldSource.EXACT, confidence=1.0),
        color_preference=RecognizedField(
            name="color_preference", value="红色", source=FieldSource.EXACT, confidence=1.0
        ),
    )
    current = IntentRecognitionResult(raw_text="购物中心中庭")
    filled = service.fill_missing_from_context(current, previous)
    assert filled.style is not None
    assert filled.style.value == "国潮"
    assert filled.color_preference is not None
    assert filled.color_preference.value == "红色"
