import pytest

from app.agents.meichen.skills.input_parser import TextParser
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
async def test_text_parser_recognizes_space_type_and_budget(text_parser: TextParser) -> None:
    data = await text_parser.parse("主题为春节，国潮快闪店，预算15万")
    assert data["space_type"] == "快闪店"
    assert data["budget"] == 150000


@pytest.mark.asyncio
async def test_text_parser_omits_clarification_when_missing_required(text_parser: TextParser) -> None:
    data = await text_parser.parse("做个美陈")
    assert "needs_clarification" not in data
    assert "missing_fields" not in data
    assert "clarification_question" not in data
