import pytest

from app.agents.input_parser import TextParser
from app.services.intent_recognition_result import (
    ClarificationRequest,
    RecognizedField,
    ValidatedIntent,
)


class FakeIntentRecognitionService:
    async def recognize(self, text: str, previous_intent=None, project_id=None) -> ValidatedIntent:
        return ValidatedIntent(
            theme=RecognizedField(name="theme", value="情人节", source="llm", confidence=0.9),
            clarification=ClarificationRequest(
                needs_clarification=True,
                missing_fields=["space_type", "budget"],
                low_confidence_fields=[],
                clarification_question="请提供空间类型和预算",
            ),
            trace_id="trace-123",
        )


@pytest.fixture(autouse=True)
def fake_intent_service(monkeypatch):
    monkeypatch.setattr(
        "app.agents.input_parser.get_intent_service", lambda: FakeIntentRecognitionService()
    )


@pytest.mark.asyncio
async def test_parse_text_returns_partial_fields_without_clarification():
    parser = TextParser()
    result = await parser.parse("情人节")
    assert result["theme"] == "情人节"
    assert "needs_clarification" not in result
    assert "clarification_question" not in result
    assert "missing_fields" not in result
    assert "space_type" in result
    assert "budget" in result
    assert "trace_id" in result
