from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Taxonomy:
    space_types: list[dict[str, Any]]
    points: list[dict[str, Any]]
    budget_levels: list[dict[str, Any]]
    styles: list[dict[str, Any]]
    materials: list[dict[str, Any]]
    field_defaults: dict[str, Any]

    # Built indexes
    space_type_names: set[str] = field(default_factory=set)
    point_names: set[str] = field(default_factory=set)
    budget_level_names: set[str] = field(default_factory=set)
    style_names: set[str] = field(default_factory=set)
    material_names: set[str] = field(default_factory=set)

    alias_to_space_type: dict[str, str] = field(default_factory=dict)
    alias_to_point: dict[str, str] = field(default_factory=dict)
    alias_to_budget_level: dict[str, str] = field(default_factory=dict)
    alias_to_style: dict[str, str] = field(default_factory=dict)
    alias_to_material: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.space_type_names, self.alias_to_space_type = _build_index(self.space_types)
        self.point_names, self.alias_to_point = _build_index(self.points)
        self.budget_level_names, self.alias_to_budget_level = _build_index(self.budget_levels)
        self.style_names, self.alias_to_style = _build_index(self.styles)
        self.material_names, self.alias_to_material = _build_index(self.materials)


def _build_index(items: list[dict[str, Any]]) -> tuple[set[str], dict[str, str]]:
    names: set[str] = set()
    alias_map: dict[str, str] = {}
    for item in items:
        name = item["name"]
        names.add(name)
        for alias in item.get("aliases", []):
            alias_map[alias.lower()] = name
        alias_map[name.lower()] = name
    return names, alias_map


DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "intent_taxonomy.yaml"


def load_taxonomy(path: Path | str = DEFAULT_TAXONOMY_PATH) -> Taxonomy:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Taxonomy(
        space_types=data.get("space_types", []),
        points=data.get("points", []),
        budget_levels=data.get("budget_levels", []),
        styles=data.get("styles", []),
        materials=data.get("materials", []),
        field_defaults=data.get("field_defaults", {}),
    )
