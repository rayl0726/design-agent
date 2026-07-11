import pytest

from app.agents.input_parser import TextParser
from app.services.intent_recognition import IntentRecognitionService


class DummyLLMClient:
    def __init__(self, response: str = "{}") -> None:
        self.response = response

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return self.response


@pytest.fixture
def text_parser() -> TextParser:
    service = IntentRecognitionService(llm_client=DummyLLMClient())
    parser = TextParser()
    parser._intent_service = service
    return parser


@pytest.mark.asyncio
async def test_parse_text_omits_clarification_fields(text_parser: TextParser):
    """parse-text must not decide completeness; only extract fields."""
    result = await text_parser.parse("圣诞节")
    assert "needs_clarification" not in result
    assert "clarification_question" not in result
    assert "missing_fields" not in result
    assert "low_confidence_fields" not in result


@pytest.mark.asyncio
async def test_parse_text_passes_project_id_to_recognize(monkeypatch):
    """project_id must be threaded through to recognize() so traces are correlatable."""
    captured_project_id = {}

    class StubService:
        async def recognize(self, text, previous_intent=None, project_id=None):
            captured_project_id["value"] = project_id
            from app.services.intent_recognition_result import ValidatedIntent
            return ValidatedIntent(raw_text=text)

    monkeypatch.setattr("app.agents.input_parser.get_intent_service", lambda: StubService())
    parser = TextParser()
    await parser.parse("圣诞节", project_id="proj-abc-123")
    assert captured_project_id["value"] == "proj-abc-123"


@pytest.mark.asyncio
async def test_parse_text_returns_enriched_recognition_meta(monkeypatch):
    """_recognition_meta must include source/confidence for all core fields."""
    from app.services.intent_recognition_result import (
        FieldSource,
        RecognizedField,
        ValidatedIntent,
    )

    class StubService:
        async def recognize(self, text, previous_intent=None, project_id=None):
            return ValidatedIntent(
                raw_text=text,
                theme=RecognizedField(name="theme", value="圣诞节", source=FieldSource.LLM, confidence=0.85, raw_text="圣诞节"),
                space_type=RecognizedField(name="space_type", value="购物中心中庭", source=FieldSource.LLM, confidence=1.0, raw_text="购物中心中庭"),
                budget=RecognizedField(name="budget", value=300000, source=FieldSource.VALIDATED, confidence=0.95, raw_text="30万"),
            )

    monkeypatch.setattr("app.agents.input_parser.get_intent_service", lambda: StubService())
    parser = TextParser()
    result = await parser.parse("圣诞节，购物中心中庭，30万")
    meta = result["_recognition_meta"]
    # theme
    assert meta["theme_source"] == "llm"
    assert meta["theme_confidence"] == 0.85
    assert meta["theme_raw_text"] == "圣诞节"
    # space_type
    assert meta["space_type_source"] == "llm"
    assert meta["space_type_confidence"] == 1.0
    # budget
    assert meta["budget_source"] == "validated"
    assert meta["budget_confidence"] == 0.95
    # missing field (style not set)
    assert meta["style_source"] is None
    assert meta["style_confidence"] == 0.0
