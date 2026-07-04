import pytest

from app.agents.input_parser import TextParser, InputMerger
from app.agents.requirement_analyst import RequirementAnalyst
from app.models.database import init_db

init_db()


@pytest.mark.asyncio
async def test_text_parser():
    parser = TextParser()
    text = "夏日海洋主题中庭吊饰，预算15万，工期2周，目标人群为年轻家庭"
    result = await parser.parse(text)
    assert result["source_type"] == "text"
    assert "夏日海洋" in result.get("theme", "")


@pytest.mark.asyncio
async def test_input_merger():
    merger = InputMerger()
    parsed = [
        {"source_type": "text", "theme": "夏日海洋", "budget": "15万", "space_type": "中庭"},
        {"source_type": "photo", "space_type": "中庭", "estimated_area": "约300平米"},
    ]
    result = await merger.merge(parsed)
    assert result["theme"] == "夏日海洋"
    assert result["space_type"] == "中庭"


@pytest.mark.asyncio
async def test_requirement_analyst():
    analyst = RequirementAnalyst()
    merged = {
        "theme": "夏日海洋",
        "style": "清新",
        "space_type": "中庭",
        "budget": "15万",
        "target_audience": "年轻家庭",
        "timeline": "2周",
        "material_restrictions": [],
        "special_requirements": [],
        "references": [],
        "raw_inputs": [],
    }
    result = await analyst.analyze(merged)
    assert result["budget_level"] is not None
    assert "conflicts" in result
