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
