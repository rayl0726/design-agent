from pathlib import Path

from app.services.prompt_template_loader import PromptTemplateLoader


def test_load_generic_template():
    loader = PromptTemplateLoader(template_dir=Path("data/prompt_templates"))
    template = loader.load("generic_commercial_display")
    assert template.name == "generic_commercial_display"
    assert template.version == "1.0"
    assert "subject" in template.sections
    assert "negative" in template.sections


def test_select_template_by_space_type():
    loader = PromptTemplateLoader(template_dir=Path("data/prompt_templates"))
    name = loader.select_for_space_type("购物中心中庭")
    assert name == "shopping_mall_atrium"


def test_select_fallback_for_unknown_space_type():
    loader = PromptTemplateLoader(template_dir=Path("data/prompt_templates"))
    name = loader.select_for_space_type("未知空间")
    assert name == "generic_commercial_display"
