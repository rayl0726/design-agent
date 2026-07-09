from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.services.learning.alias_expansion import AliasProposal


class TaxonomyWriter:
    def __init__(self, taxonomy_path: str | Path = "agent-core/data/intent_taxonomy.yaml"):
        self.taxonomy_path = Path(taxonomy_path)

    def apply_alias(self, proposal: AliasProposal) -> bool:
        data = yaml.safe_load(self.taxonomy_path.read_text(encoding="utf-8"))
        target_list = self._target_list(data, proposal.field)
        if target_list is None:
            return False

        for entry in target_list:
            if entry.get("name") == proposal.canonical:
                aliases = entry.setdefault("aliases", [])
                if proposal.alias not in aliases:
                    aliases.append(proposal.alias)
                self.taxonomy_path.write_text(
                    yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )
                return True
        return False

    def _target_list(self, data: dict[str, Any], field: str) -> list[dict[str, Any]] | None:
        mapping = {
            "space_type": "space_types",
            "point": "points",
            "style": "styles",
            "material": "materials",
        }
        key = mapping.get(field)
        return data.get(key) if key else None
