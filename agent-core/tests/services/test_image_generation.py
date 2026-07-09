import pytest

from app.services.image_generation import ImageGenerationService


@pytest.mark.asyncio
async def test_generate_from_intent_uses_template(monkeypatch):
    service = ImageGenerationService()
    called = {}

    async def fake_generate(prompt, aspect_ratio="16:9", _style="realistic"):
        called["prompt"] = prompt
        called["aspect_ratio"] = aspect_ratio
        return "fake.png"

    monkeypatch.setattr(service, "generate", fake_generate)

    result = await service.generate_from_intent(
        {
            "theme": "圣诞节",
            "space_type": "购物中心中庭",
            "budget_level": "high",
            "style": "现代简约",
        },
        template_version="shopping_mall_atrium",
    )
    assert result["filename"] == "fake.png"
    assert "圣诞节" in result["prompt"] or "Christmas" in result["prompt"]
    assert "central" in result["prompt"].lower() or "中庭" in result["prompt"]
    assert result["template_version"] == "shopping_mall_atrium:1.0"
