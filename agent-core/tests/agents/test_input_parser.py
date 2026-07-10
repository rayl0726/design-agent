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
