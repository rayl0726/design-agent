from __future__ import annotations

import pytest

from app.services.intent_recognition import IntentRecognitionService
from app.services.semantic_matcher import SemanticMatcher
from tests.intent.evaluator import evaluate


class DummyLLMClient:
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return "{}"


class FakeSemanticMatcher(SemanticMatcher):
    def __init__(self) -> None:
        pass

    async def match(self, text: str, field_type: str) -> tuple[str | None, float]:
        if field_type == "space_type" and "商场入口" in text:
            return "百货入口", 0.9
        if field_type == "style" and "中式" in text:
            return "国潮", 0.9
        return None, 0.0


@pytest.fixture
def service() -> IntentRecognitionService:
    return IntentRecognitionService(
        llm_client=DummyLLMClient(),
        semantic_matcher=FakeSemanticMatcher(),
    )


@pytest.mark.asyncio
async def test_golden_case_accuracy(service: IntentRecognitionService) -> None:
    report = await evaluate(service)
    assert report["accuracy"] >= 0.8, f"Accuracy {report['accuracy']} below 0.8: {report['failures']}"
