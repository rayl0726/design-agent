from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jinja2 import Template

from app.services.prompt_template_loader import PromptTemplate


@dataclass
class RenderedPrompt:
    positive: str
    negative: str
    version: str
    aspect_ratio: str


class PromptTemplateRenderer:
    @staticmethod
    def _strip_multiline(text: str) -> str:
        return " ".join(line.strip() for line in text.splitlines() if line.strip())

    async def render(
        self,
        template: PromptTemplate,
        context: dict[str, Any],
    ) -> RenderedPrompt:
        rendered_sections: dict[str, str] = {}
        for key, raw in template.sections.items():
            if key == "negative":
                continue
            rendered_sections[key] = self._strip_multiline(Template(raw).render(context))

        positive = " ".join(
            rendered_sections.get(k, "")
            for k in ["subject", "environment", "camera_angle", "lighting", "style"]
        )

        negative_context = {
            **context,
            "default_negative": template.sections.get("negative", ""),
        }
        user_negative = context.get("negative_prompts", [])
        if user_negative:
            negative = ", ".join(user_negative)
        else:
            negative = self._strip_multiline(
                Template(template.sections.get("negative", "")).render(negative_context)
            )

        return RenderedPrompt(
            positive=positive,
            negative=negative,
            version=f"{template.name}:{template.version}",
            aspect_ratio=template.aspect_ratio,
        )
