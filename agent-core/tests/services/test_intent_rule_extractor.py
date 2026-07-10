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
    assert output.theme is None


@pytest.mark.asyncio
async def test_extract_points():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("中庭门头")
    assert "中庭" in output.points
    assert "门头" in output.points


@pytest.mark.asyncio
async def test_extract_budget_level_not_theme():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("低成本快闪店")
    assert output.space_type == "快闪店"
    assert output.theme is None


@pytest.mark.asyncio
async def test_extract_style():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("国潮风快闪店")
    assert output.style == "国潮"
    assert output.space_type == "快闪店"
    assert output.theme is None


@pytest.mark.asyncio
async def test_extract_theme_with_marker():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("我要做一个情人节主题的快闪店")
    assert output.theme == "情人节"
    assert output.space_type == "快闪店"


@pytest.mark.asyncio
async def test_extract_material_restrictions():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("不要用亚克力，避免金属框架")
    assert "亚克力" in output.material_restrictions
    assert "金属框架" in output.material_restrictions


@pytest.mark.asyncio
async def test_extract_allowed_materials():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("木材和玻璃可以用")
    assert "木材" in output.allowed_materials
    assert "玻璃" in output.allowed_materials


@pytest.mark.asyncio
async def test_extract_allowed_materials_with_keyi_prefix():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("可以用亚克力")
    assert "亚克力" in output.allowed_materials


@pytest.mark.asyncio
async def test_extract_timeline():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("工期1个月")
    assert output.timeline == "1个月"


@pytest.mark.asyncio
async def test_extract_color_preference():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("颜色：红色")
    assert output.color_preference == "红色"


@pytest.mark.asyncio
async def test_extract_budget_range():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("预算20万-30万")
    assert output.budget == "20万-30万"


@pytest.mark.asyncio
async def test_extract_space_type_alias():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("商场中庭")
    assert output.space_type == "购物中心中庭"


@pytest.mark.asyncio
async def test_extract_space_type_substring_and_alias():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("popup store")
    assert output.space_type == "快闪店"


@pytest.mark.asyncio
async def test_extract_explicit_theme_filters_known_non_theme():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("主题为快闪店")
    assert output.theme is None
    assert output.space_type == "快闪店"


@pytest.mark.asyncio
async def test_extract_explicit_theme_allows_style_alias():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("主题为国潮")
    assert output.theme == "国潮"
