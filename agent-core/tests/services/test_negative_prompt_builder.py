from pathlib import Path

from app.services.negative_prompt_builder import NegativePromptBuilder


def test_default_negative_prompts_applied():
    builder = NegativePromptBuilder(config_dir=Path("data/negative_prompts"))
    result = builder.build(space_type="购物中心中庭")
    assert "cluttered background" in result
    assert "people" in result


def test_user_override_replaces_defaults():
    builder = NegativePromptBuilder(config_dir=Path("data/negative_prompts"))
    result = builder.build(space_type="购物中心中庭", user_negative=["text", "watermark"])
    assert result == "text, watermark"
