from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PromptTemplate:
    name: str
    version: str
    space_types: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    aspect_ratio: str = "16:9"
    legacy_fallback: bool = False


class PromptTemplateLoader:
    def __init__(self, template_dir: str | Path | None = None):
        if template_dir is None:
            self.template_dir = Path(__file__).resolve().parents[2] / "data" / "prompt_templates"
        else:
            self.template_dir = Path(template_dir)

    def load(self, name: str) -> PromptTemplate:
        path = self.template_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PromptTemplate(
            name=name,
            version=str(raw.get("version", "1.0")),
            space_types=raw.get("space_types", []),
            sections=raw.get("sections", {}),
            aspect_ratio=raw.get("aspect_ratio", "16:9"),
            legacy_fallback=raw.get("legacy_fallback", False),
        )

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.template_dir.glob("*.yaml"))
