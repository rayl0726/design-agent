from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Example:
    input_text: str
    space_type: str
    theme: str | None = None
    budget: int | None = None
    points: list[str] | None = None
    style: str | None = None
    material_restrictions: list[str] | None = None
    allowed_materials: list[str] | None = None


class FewShotLibrary:
    def __init__(self, data_dir: str | Path = "agent-core/data/few_shot_examples"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, space_type: str) -> Path:
        safe = space_type.replace(" ", "_").replace("/", "_")
        return self.data_dir / f"{safe}.jsonl"

    async def append(self, example: Example) -> None:
        path = self._file_path(example.space_type)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(example), ensure_ascii=False) + "\n")

    async def retrieve(
        self,
        space_type: str,
        theme: str | None = None,
        top_k: int = 3,
    ) -> list[Example]:
        path = self._file_path(space_type)
        if not path.exists():
            return []

        examples: list[Example] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                examples.append(Example(**data))

        if theme:
            examples = [e for e in examples if e.theme == theme]
        return examples[:top_k]
