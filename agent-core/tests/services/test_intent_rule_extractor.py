import pytest

from app.services.intent_rule_extractor import IntentRuleExtractor
from app.services.taxonomy_loader import load_taxonomy


@pytest.mark.asyncio
async def test_extract_bare_theme():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("情人节")
    assert output.theme == "情人节"
    assert output.space_type is None


@pytest.mark.asyncio
async def test_extract_space_type_and_budget():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("快闪店30万")
    assert output.space_type == "快闪店"
    assert output.budget == "30万"


@pytest.mark.asyncio
async def test_extract_points():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("中庭门头")
    assert "中庭" in output.points
    assert "门头" in output.points
