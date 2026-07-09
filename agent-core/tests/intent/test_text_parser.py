import pytest

from app.agents.input_parser import TextParser


@pytest.mark.asyncio
async def test_text_parser_recognizes_pop_up() -> None:
    parser = TextParser()
    data = await parser.parse("新春国潮快闪店，预算15万")
    assert data["space_type"] == "快闪店"
    assert data["budget"] == 150000
    assert data["_recognition_meta"]["space_type_source"] == "exact"
