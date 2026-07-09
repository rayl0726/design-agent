from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class NegativePromptBuilder:
    def __init__(self, config_dir: str | Path | None = None):
        if config_dir is None:
            self.config_dir = Path(__file__).resolve().parents[2] / "data" / "negative_prompts"
        else:
            self.config_dir = Path(config_dir)
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        path = self.config_dir / "default.yaml"
        if not path.exists():
            return {"categories": {}, "space_type_mapping": {"_default": ["generic"]}}
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def build(self, space_type: str | None = None, user_negative: list[str] | None = None) -> str:
        if user_negative:
            return ", ".join(user_negative)

        categories = self._config.get("space_type_mapping", {})
        keys = categories.get(space_type, categories.get("_default", ["generic"]))

        fragments: list[str] = []
        for key in keys:
            for phrase in self._config.get("categories", {}).get(key, []):
                if phrase not in fragments:
                    fragments.append(phrase)
        return ", ".join(fragments)
