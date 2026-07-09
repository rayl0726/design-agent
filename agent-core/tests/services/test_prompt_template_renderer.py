import pytest
from pathlib import Path

from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer


@pytest.mark.asyncio
async def test_render_atrium_emphasizes_center():
    loader = PromptTemplateLoader(template_dir=Path("data/prompt_templates"))
    template = loader.load("shopping_mall_atrium")
    renderer = PromptTemplateRenderer()
    result = await renderer.render(
        template,
        {
            "theme": "圣诞节",
            "space_type": "购物中心中庭",
            "budget_level": "high",
            "style": "现代简约",
            "negative_prompts": ["cluttered background", "people"],
        },
    )
    assert "central" in result.positive.lower() or "中庭" in result.positive
    assert "background" in result.negative.lower() or "people" in result.negative
    assert result.version == "shopping_mall_atrium:1.0"
