from pathlib import Path


def test_load_generic_template():
    from app.services.prompt_template_loader import PromptTemplateLoader

    loader = PromptTemplateLoader(template_dir=Path("data/prompt_templates"))
    template = loader.load("generic_commercial_display")
    assert template.name == "generic_commercial_display"
    assert template.version == "1.0"
    assert "subject" in template.sections
    assert "negative" in template.sections
