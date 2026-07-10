import pytest

from app.agents.input_parser import TextParser


@pytest.mark.asyncio
async def test_parse_text_omits_clarification_fields():
    """parse-text must not decide completeness; only extract fields."""
    parser = TextParser()
    result = await parser.parse("圣诞节")
    assert "needs_clarification" not in result
    assert "clarification_question" not in result
    assert "missing_fields" not in result
    assert "low_confidence_fields" not in result
    assert result["theme"] == "圣诞节"
