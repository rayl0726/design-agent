# Intent Recognition Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded keyword parsing in `agent-core` with a domain-taxonomy-driven, multi-layer intent recognition service that supports exact/alias/fuzzy/semantic matching, constrained LLM fallback, cross-modal consistency, and automated accuracy evaluation.

**Architecture:** A new `IntentRecognitionService` reads `intent_taxonomy.yaml` and runs inputs through five local layers (exact → alias → fuzzy → semantic → LLM-constrained). The service returns `IntentRecognitionResult` objects with source/confidence/candidates metadata. Text and multi-modal parsers consume this service; a golden test set and evaluator protect against regressions.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, jieba, rapidfuzz, numpy, existing `EmbeddingClient` (Ollama/Zhipu), pytest.

## Global Constraints

- Python target version: 3.11 (`tool.ruff.target-version = "py311"`).
- Line length: 120 (`tool.ruff.line-length = 120`).
- mypy strict mode enabled.
- Add new dependencies to `agent-core/pyproject.toml`.
- Keep parsers in `agent-core/app/agents/input_parser.py`; do not split them into separate files unless necessary.
- Do not modify frontend UI; clarification messages flow through existing text-message mechanism.
- `IntentRecognitionService` must be async-friendly for FastAPI endpoints.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `agent-core/data/intent_taxonomy.yaml` | Domain vocabulary: space types, points, budget levels, styles, materials, aliases. |
| `agent-core/app/services/intent_recognition_result.py` | Pydantic models for recognition result, field source, and confidence. |
| `agent-core/app/services/taxonomy_loader.py` | Load and validate `intent_taxonomy.yaml`; build alias indexes. |
| `agent-core/app/services/semantic_matcher.py` | Pre-compute taxonomy embeddings and match user tokens by cosine similarity. |
| `agent-core/app/services/intent_recognition.py` | Main `IntentRecognitionService`: runs the five-layer pipeline. |
| `agent-core/app/agents/input_parser.py` | Modify `TextParser`, `PhotoParser`, `VideoParser`, `ReferenceParser`, `InputMerger` to use the new service. |
| `agent-core/tests/intent/golden_cases.jsonl` | Ground-truth test cases covering all match sources and context scenarios. |
| `agent-core/tests/intent/test_intent_recognition.py` | Unit tests for the service and each layer. |
| `agent-core/tests/intent/test_evaluator.py` | Accuracy evaluator and golden-case runner. |
| `agent-core/pyproject.toml` | Add `jieba`, `rapidfuzz`, optional `sentence-transformers` fallback. |

---

### Task 1: Add Dependencies

**Files:**
- Modify: `agent-core/pyproject.toml:6-28`

**Interfaces:**
- Consumes: none.
- Produces: updated dependency list.

- [ ] **Step 1: Add packages to `dependencies`**

Append these lines to the `dependencies` array in `agent-core/pyproject.toml`:

```toml
    "jieba>=0.42.1",
    "rapidfuzz>=3.9.0",
```

- [ ] **Step 2: Add optional local embedding fallback**

Append to `project.optional-dependencies.dev`:

```toml
    "sentence-transformers>=3.0.0",
```

This is only used if the project later wants a fully offline embedding model; the implementation will reuse the existing `EmbeddingClient`.

- [ ] **Step 3: Install locally**

Run:

```bash
cd agent-core
pip install -e ".[dev]"
```

Expected: installs `jieba` and `rapidfuzz` without errors.

- [ ] **Step 4: Commit**

```bash
git add agent-core/pyproject.toml
git commit -m "deps: add jieba and rapidfuzz for intent recognition"
```

---

### Task 2: Create Domain Taxonomy File

**Files:**
- Create: `agent-core/data/intent_taxonomy.yaml`

**Interfaces:**
- Consumes: none.
- Produces: taxonomy file read by `TaxonomyLoader`.

- [ ] **Step 1: Write taxonomy YAML**

Create `agent-core/data/intent_taxonomy.yaml`:

```yaml
version: "1.0"
space_types:
  - name: "购物中心中庭"
    aliases: ["商场中庭", "shopping mall atrium", "中庭"]
  - name: "快闪店"
    aliases: ["popup store", "pop-up store", "快闪", "快闪空间"]
  - name: "百货入口"
    aliases: ["商场入口", "百货大门", "department store entrance"]
  - name: "步行街"
    aliases: ["商业街", "pedestrian street"]
  - name: "展厅"
    aliases: ["展览厅", "exhibition hall"]
  - name: "门店"
    aliases: ["专卖店", "retail store"]
  - name: "橱窗"
    aliases: ["display window", "shop window"]

points:
  - name: "中庭"
    aliases: ["中庭吊饰", "中庭装置"]
  - name: "门头"
    aliases: ["店招", "入口门头"]
  - name: "DP点"
    aliases: ["dp点", "display point"]
  - name: "合影墙"
    aliases: ["打卡墙", "photo wall"]
  - name: "灯光画"
    aliases: ["灯饰画", "lighting art"]
  - name: "扶梯"
    aliases: ["自动扶梯", "escalator"]
  - name: "连廊"
    aliases: ["走廊", "corridor"]
  - name: "服务台"
    aliases: ["咨询台", "reception"]
  - name: "立柱"
    aliases: ["柱子", "pillar"]
  - name: "地贴"
    aliases: ["地面贴画", "floor sticker"]
  - name: "吊旗"
    aliases: ["hanging flag"]
  - name: "指示牌"
    aliases: ["导视牌", "signage"]
  - name: "花车"
    aliases: ["促销车", "display cart"]
  - name: "摊位"
    aliases: ["booth", "摊位布置"]

budget_levels:
  - name: "low"
    aliases: ["低预算", "低成本", "省钱"]
    max_amount_cny: 100000
  - name: "medium"
    aliases: ["中等预算", "适中"]
    max_amount_cny: 300000
  - name: "high"
    aliases: ["高预算", "高端", "豪华"]
    max_amount_cny: 1000000

styles:
  - name: "现代简约"
    aliases: ["简约", "modern minimal"]
  - name: "国潮"
    aliases: ["中国风", "新中式", "chinese trend"]
  - name: "轻奢"
    aliases: ["轻奢华", " affordable luxury"]
  - name: "海洋风"
    aliases: ["海洋主题", "summer ocean"]
  - name: "新春"
    aliases: ["春节", "新年", "spring festival"]

materials:
  - name: "亚克力"
    aliases: ["acrylic"]
  - name: "LED灯带"
    aliases: ["灯带", "led strip"]
  - name: "金属框架"
    aliases: ["金属", "metal frame"]
  - name: "玻璃"
    aliases: ["glass"]
  - name: "木材"
    aliases: ["木质", "wood"]
  - name: "泡沫雕塑"
    aliases: ["泡沫", "foam sculpture"]

field_defaults:
  space_type:
    required: true
    can_inherit: false
  budget:
    required: true
    can_inherit: false
  points:
    required: false
    can_inherit: false
    default_by_space_type:
      快闪店: ["门头", "DP点", "合影墙"]
      购物中心中庭: ["中庭", "DP点"]
      百货入口: ["门头", "指示牌"]
      步行街: ["DP点", "指示牌", "花车"]
  style:
    required: false
    can_inherit: true
  color_preference:
    required: false
    can_inherit: true
  material_restrictions:
    required: false
    can_inherit: true
  timeline:
    required: false
    can_inherit: false
    default_value: "2-3周"
```

- [ ] **Step 2: Verify YAML loads**

Run:

```bash
cd agent-core
python -c "import yaml; print(yaml.safe_load(open('data/intent_taxonomy.yaml')))"
```

Expected: prints a dictionary without errors. If `pyyaml` is not installed, use `pip install pyyaml` (it is already a transitive dependency via `pyproject.toml`).

- [ ] **Step 3: Commit**

```bash
git add agent-core/data/intent_taxonomy.yaml
git commit -m "data: add commercial display intent taxonomy"
```

---

### Task 3: Create Result Models

**Files:**
- Create: `agent-core/app/services/intent_recognition_result.py`

**Interfaces:**
- Consumes: none.
- Produces: `FieldSource`, `RecognizedField`, `IntentRecognitionResult`, `ClarificationRequest`.

- [ ] **Step 1: Write result models**

Create `agent-core/app/services/intent_recognition_result.py`:

```python
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldSource(str, Enum):
    EXACT = "exact"
    ALIAS = "alias"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    LLM = "llm"
    DEFAULT = "default"
    UNKNOWN = "unknown"


class RecognizedField(BaseModel):
    name: str
    value: Any
    source: FieldSource = FieldSource.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    candidates: list[tuple[str, float]] = Field(default_factory=list)
    raw_text: str = ""

    def is_confident(self, threshold: float = 0.75) -> bool:
        return self.confidence >= threshold


class IntentRecognitionResult(BaseModel):
    space_type: RecognizedField | None = None
    budget: RecognizedField | None = None
    budget_level: RecognizedField | None = None
    theme: RecognizedField | None = None
    style: RecognizedField | None = None
    target_audience: RecognizedField | None = None
    timeline: RecognizedField | None = None
    material_restrictions: list[RecognizedField] = Field(default_factory=list)
    special_requirements: list[RecognizedField] = Field(default_factory=list)
    color_preference: RecognizedField | None = None
    brand_positioning: RecognizedField | None = None
    design_system_preference: RecognizedField | None = None
    points: list[RecognizedField] = Field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ClarificationRequest(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    low_confidence_fields: list[str] = Field(default_factory=list)
    message: str = ""
```

- [ ] **Step 2: Write a minimal import test**

Create `agent-core/tests/intent/__init__.py` (empty file) and `agent-core/tests/intent/test_models.py`:

```python
from app.services.intent_recognition_result import (
    FieldSource,
    RecognizedField,
    IntentRecognitionResult,
)


def test_recognized_field_defaults():
    field = RecognizedField(name="space_type", value="快闪店")
    assert field.source == FieldSource.UNKNOWN
    assert field.confidence == 0.0
    assert not field.is_confident()


def test_result_can_dump():
    result = IntentRecognitionResult(
        space_type=RecognizedField(name="space_type", value="快闪店", source=FieldSource.EXACT, confidence=1.0)
    )
    data = result.to_dict()
    assert data["space_type"]["value"] == "快闪店"
```

- [ ] **Step 3: Run the test**

```bash
cd agent-core
pytest tests/intent/test_models.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add agent-core/app/services/intent_recognition_result.py agent-core/tests/intent/__init__.py agent-core/tests/intent/test_models.py
git commit -m "feat(intent): add recognition result models"
```

---

### Task 4: Create Taxonomy Loader

**Files:**
- Create: `agent-core/app/services/taxonomy_loader.py`

**Interfaces:**
- Consumes: `agent-core/data/intent_taxonomy.yaml`.
- Produces: `Taxonomy` dataclass with `name_to_standard`, `alias_to_standard`, `all_terms`, `field_defaults`.

- [ ] **Step 1: Implement loader**

Create `agent-core/app/services/taxonomy_loader.py`:

```python
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
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Taxonomy(
        space_types=data.get("space_types", []),
        points=data.get("points", []),
        budget_levels=data.get("budget_levels", []),
        styles=data.get("styles", []),
        materials=data.get("materials", []),
        field_defaults=data.get("field_defaults", {}),
    )
```

- [ ] **Step 2: Write loader test**

Create `agent-core/tests/intent/test_taxonomy_loader.py`:

```python
from app.services.taxonomy_loader import load_taxonomy


def test_load_taxonomy():
    taxonomy = load_taxonomy()
    assert "快闪店" in taxonomy.space_type_names
    assert taxonomy.alias_to_space_type["popup store"] == "快闪店"
    assert taxonomy.alias_to_space_type["中庭"] == "购物中心中庭"
    assert "DP点" in taxonomy.point_names
```

- [ ] **Step 3: Run the test**

```bash
cd agent-core
pytest tests/intent/test_taxonomy_loader.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add agent-core/app/services/taxonomy_loader.py agent-core/tests/intent/test_taxonomy_loader.py
git commit -m "feat(intent): add taxonomy loader with alias indexes"
```

---

### Task 5: Create Semantic Matcher

**Files:**
- Create: `agent-core/app/services/semantic_matcher.py`

**Interfaces:**
- Consumes: `Taxonomy`, `EmbeddingClient`.
- Produces: `SemanticMatcher.match(text, field_type)` returning `(standard_name, confidence)` or `(None, 0.0)`.

- [ ] **Step 1: Implement semantic matcher**

Create `agent-core/app/services/semantic_matcher.py`:

```python
from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np

from app.services.embedding_client import embedding_client
from app.services.taxonomy_loader import Taxonomy


class SemanticMatcher:
    def __init__(self, taxonomy: Taxonomy, threshold: float = 0.82):
        self.taxonomy = taxonomy
        self.threshold = threshold
        self._embedding_cache: dict[str, list[float]] = {}

    async def _embed(self, text: str) -> list[float]:
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        emb = await embedding_client.embed(text, use_cache=True)
        self._embedding_cache[text] = emb
        return emb

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        va = np.array(a)
        vb = np.array(b)
        norm = np.linalg.norm(va) * np.linalg.norm(vb)
        if norm == 0:
            return 0.0
        return float(np.dot(va, vb) / norm)

    async def match(
        self,
        text: str,
        field_type: str,
    ) -> tuple[str | None, float]:
        candidates = self._candidates_for_field(field_type)
        if not candidates:
            return None, 0.0

        query_emb = await self._embed(text)
        best_name: str | None = None
        best_score = 0.0
        for name, aliases in candidates:
            texts = [name, *aliases]
            scores: list[float] = []
            for t in texts:
                key = t.lower()
                emb = await self._embed(key)
                scores.append(self._cosine_similarity(query_emb, emb))
            score = max(scores)
            if score > best_score:
                best_score = score
                best_name = name

        if best_score >= self.threshold:
            return best_name, best_score
        return None, best_score

    def _candidates_for_field(self, field_type: str) -> list[tuple[str, list[str]]]:
        mapping: dict[str, list[dict[str, Any]]] = {
            "space_type": self.taxonomy.space_types,
            "point": self.taxonomy.points,
            "budget_level": self.taxonomy.budget_levels,
            "style": self.taxonomy.styles,
            "material": self.taxonomy.materials,
        }
        items = mapping.get(field_type, [])
        return [(item["name"], item.get("aliases", [])) for item in items]
```

- [ ] **Step 2: Write semantic matcher test**

Create `agent-core/tests/intent/test_semantic_matcher.py`:

```python
import pytest

from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import load_taxonomy


@pytest.mark.asyncio
async def test_semantic_match_space_type():
    taxonomy = load_taxonomy()
    matcher = SemanticMatcher(taxonomy, threshold=0.75)
    name, score = await matcher.match("pop-up store", "space_type")
    assert name == "快闪店"
    assert score >= 0.75
```

- [ ] **Step 3: Run the test**

```bash
cd agent-core
pytest tests/intent/test_semantic_matcher.py -v
```

Expected: 1 passed (requires embedding provider to be reachable or cached).

- [ ] **Step 4: Commit**

```bash
git add agent-core/app/services/semantic_matcher.py agent-core/tests/intent/test_semantic_matcher.py
git commit -m "feat(intent): add semantic matcher over taxonomy embeddings"
```

---

### Task 6: Create Intent Recognition Service

**Files:**
- Create: `agent-core/app/services/intent_recognition.py`
- Modify: `agent-core/app/services/__init__.py`

**Interfaces:**
- Consumes: `Taxonomy`, `SemanticMatcher`, `llm_client`, `RecognizedField`, `IntentRecognitionResult`, `FieldSource`.
- Produces: `IntentRecognitionService.recognize(text: str) -> IntentRecognitionResult` and `.fill_missing(result, last_intent) -> IntentRecognitionResult`.

- [ ] **Step 1: Implement service**

Create `agent-core/app/services/intent_recognition.py`:

```python
from __future__ import annotations

import json
import re
from typing import Any

import jieba
from rapidfuzz import fuzz

from app.services.intent_recognition_result import (
    FieldSource,
    IntentRecognitionResult,
    RecognizedField,
)
from app.services.llm_client import llm_client
from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import Taxonomy, load_taxonomy


FUZZY_THRESHOLD = 0.75
FUZZY_THRESHOLD_CRITICAL = 0.85
SEMANTIC_THRESHOLD = 0.82


class IntentRecognitionService:
    def __init__(self, taxonomy: Taxonomy | None = None):
        self.taxonomy = taxonomy or load_taxonomy()
        self.semantic = SemanticMatcher(self.taxonomy, threshold=SEMANTIC_THRESHOLD)
        self._load_jieba_dict()

    def _load_jieba_dict(self) -> None:
        # Add taxonomy terms to jieba user dict so they are not split.
        terms: list[str] = []
        for item in self.taxonomy.space_types + self.taxonomy.points + self.taxonomy.styles + self.taxonomy.materials:
            terms.append(item["name"])
            terms.extend(item.get("aliases", []))
        for term in set(terms):
            jieba.add_word(term, freq=1000)

    async def recognize(self, text: str) -> IntentRecognitionResult:
        tokens = [t for t in jieba.lcut(text) if t.strip()]
        result = IntentRecognitionResult(raw_text=text)

        # Space type
        result.space_type = await self._match_field(tokens, "space_type", self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type)

        # Points
        result.points = self._match_points(tokens, text)

        # Budget
        result.budget = self._extract_budget(text)
        result.budget_level = self._extract_budget_level(text, result.budget)

        # Style
        result.style = await self._match_field(tokens, "style", self.taxonomy.style_names, self.taxonomy.alias_to_style)

        # Materials
        result.material_restrictions = await self._match_multi(tokens, "material", self.taxonomy.material_names, self.taxonomy.alias_to_material)

        # Theme, timeline, color via simple regex + LLM fallback
        result.theme = self._extract_regex_field(text, r"(?:主题|概念|theme)\s*[：:]\s*([^\n，。]+)")
        result.timeline = self._extract_regex_field(text, r"(?:工期|时间|timeline)\s*[：:]\s*([^\n，。]+)")
        result.color_preference = self._extract_regex_field(text, r"(?:颜色|色彩|color)\s*[：:]\s*([^\n，。]+)")

        # LLM fallback for missing critical/optional fields
        result = await self._llm_fallback(result, text)
        return result

    async def _match_field(
        self,
        tokens: list[str],
        field_type: str,
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> RecognizedField | None:
        # Layer 1: exact token match
        for token in tokens:
            if token in exact_names:
                return RecognizedField(name=field_type, value=token, source=FieldSource.EXACT, confidence=1.0, raw_text=token)

        # Layer 2: alias match
        for token in tokens:
            key = token.lower()
            if key in alias_map:
                standard = alias_map[key]
                return RecognizedField(name=field_type, value=standard, source=FieldSource.ALIAS, confidence=0.95, raw_text=token)

        # Layer 3: fuzzy match (token vs standard names and aliases)
        best: tuple[str, float] | None = None
        all_targets: dict[str, str] = {}
        for name in exact_names:
            all_targets[name] = name
        for alias, standard in alias_map.items():
            all_targets[alias] = standard

        for token in tokens:
            for target, standard in all_targets.items():
                score = fuzz.ratio(token, target) / 100.0
                if score >= FUZZY_THRESHOLD and (best is None or score > best[1]):
                    best = (standard, score)

        if best and best[1] >= FUZZY_THRESHOLD_CRITICAL:
            return RecognizedField(name=field_type, value=best[0], source=FieldSource.FUZZY, confidence=round(best[1], 2), raw_text=" ".join(tokens))

        # Layer 4: semantic match over full text
        standard, score = await self.semantic.match(" ".join(tokens), field_type)
        if standard:
            return RecognizedField(name=field_type, value=standard, source=FieldSource.SEMANTIC, confidence=round(score, 2), raw_text=" ".join(tokens))

        return None

    def _match_points(self, tokens: list[str], text: str) -> list[RecognizedField]:
        found: list[RecognizedField] = []
        seen: set[str] = set()
        all_targets: dict[str, str] = {}
        for item in self.taxonomy.points:
            name = item["name"]
            all_targets[name] = name
            for alias in item.get("aliases", []):
                all_targets[alias] = name

        for token in tokens:
            if token in self.taxonomy.point_names and token not in seen:
                found.append(RecognizedField(name="point", value=token, source=FieldSource.EXACT, confidence=1.0, raw_text=token))
                seen.add(token)
                continue
            key = token.lower()
            if key in self.taxonomy.alias_to_point:
                standard = self.taxonomy.alias_to_point[key]
                if standard not in seen:
                    found.append(RecognizedField(name="point", value=standard, source=FieldSource.ALIAS, confidence=0.95, raw_text=token))
                    seen.add(standard)

        # Count extraction: "门头×2"
        for field in found:
            name = str(field.value)
            pattern = re.search(rf"{re.escape(name)}\s*[×xX*]\s*(\d+)", text)
            if pattern:
                field.value = {"name": name, "count": int(pattern.group(1))}
            else:
                field.value = {"name": name, "count": 1}
        return found

    def _extract_budget(self, text: str) -> RecognizedField | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|元|千)", text)
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            if unit == "万":
                amount *= 10000
            elif unit == "千":
                amount *= 1000
            return RecognizedField(name="budget", value=int(amount), source=FieldSource.EXACT, confidence=1.0, raw_text=match.group(0))
        return None

    def _extract_budget_level(self, text: str, budget: RecognizedField | None) -> RecognizedField | None:
        # Check alias map first
        for alias, standard in self.taxonomy.alias_to_budget_level.items():
            if alias in text.lower() and len(alias) > 1:
                return RecognizedField(name="budget_level", value=standard, source=FieldSource.ALIAS, confidence=0.9, raw_text=alias)
        if budget and isinstance(budget.value, int):
            amount = budget.value
            if amount < 100000:
                level = "low"
            elif amount > 300000:
                level = "high"
            else:
                level = "medium"
            return RecognizedField(name="budget_level", value=level, source=FieldSource.DEFAULT, confidence=0.8, raw_text=str(amount))
        return None

    def _extract_regex_field(self, text: str, pattern: str) -> RecognizedField | None:
        match = re.search(pattern, text)
        if match:
            return RecognizedField(name="theme", value=match.group(1).strip(), source=FieldSource.EXACT, confidence=1.0, raw_text=match.group(0))
        return None

    async def _match_multi(
        self,
        tokens: list[str],
        field_type: str,
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> list[RecognizedField]:
        results: list[RecognizedField] = []
        seen: set[str] = set()
        for token in tokens:
            if token in exact_names and token not in seen:
                results.append(RecognizedField(name=field_type, value=token, source=FieldSource.EXACT, confidence=1.0, raw_text=token))
                seen.add(token)
            key = token.lower()
            if key in alias_map:
                standard = alias_map[key]
                if standard not in seen:
                    results.append(RecognizedField(name=field_type, value=standard, source=FieldSource.ALIAS, confidence=0.95, raw_text=token))
                    seen.add(standard)
        return results

    async def _llm_fallback(self, result: IntentRecognitionResult, text: str) -> IntentRecognitionResult:
        missing_fields: dict[str, list[str]] = {}
        if result.space_type is None:
            missing_fields["space_type"] = ["空间类型"] + [s["name"] for s in self.taxonomy.space_types[:10]]
        if result.budget is None:
            missing_fields["budget"] = ["预算金额，如 150000"]

        if not missing_fields:
            return result

        system = "你是一位美陈设计需求解析助手。请仅从候选值中选择，不要编造。"
        prompt = (
            f"用户输入：{text}\n"
            "请从以下候选值中补充缺失字段，输出 JSON 不要多余文字。\n"
            "如果无法确定，保持 null。\n"
            f"{json.dumps(missing_fields, ensure_ascii=False, indent=2)}\n"
            '输出格式：{"space_type": "购物中心中庭", "budget": 150000}'
        )
        raw = await llm_client.complete(system, prompt, json_mode=True)
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return result

        if result.space_type is None and data.get("space_type"):
            value = data["space_type"]
            if value in self.taxonomy.space_type_names:
                result.space_type = RecognizedField(name="space_type", value=value, source=FieldSource.LLM, confidence=0.7, raw_text=text)

        if result.budget is None and data.get("budget"):
            value = data["budget"]
            try:
                result.budget = RecognizedField(name="budget", value=int(value), source=FieldSource.LLM, confidence=0.7, raw_text=text)
            except (ValueError, TypeError):
                pass

        return result

    def fill_missing_from_context(
        self,
        result: IntentRecognitionResult,
        last_intent: IntentRecognitionResult | None,
    ) -> IntentRecognitionResult:
        if last_intent is None:
            return result
        fields = ["style", "color_preference", "material_restrictions", "special_requirements"]
        for field_name in fields:
            current = getattr(result, field_name)
            previous = getattr(last_intent, field_name)
            if current is None or (isinstance(current, list) and not current):
                setattr(result, field_name, previous)
        return result


_intent_service: IntentRecognitionService | None = None


def get_intent_service() -> IntentRecognitionService:
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentRecognitionService()
    return _intent_service
```

- [ ] **Step 2: Write service tests**

Create `agent-core/tests/intent/test_intent_recognition.py`:

```python
import pytest

from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_recognition_result import FieldSource


@pytest.fixture
def service():
    return IntentRecognitionService()


@pytest.mark.asyncio
async def test_exact_space_type(service):
    result = await service.recognize("购物中心中庭海洋主题")
    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"
    assert result.space_type.source == FieldSource.EXACT


@pytest.mark.asyncio
async def test_alias_space_type(service):
    result = await service.recognize("popup store 快闪")
    assert result.space_type is not None
    assert result.space_type.value == "快闪店"
    assert result.space_type.source == FieldSource.ALIAS


@pytest.mark.asyncio
async def test_fuzzy_space_type(service):
    result = await service.recognize("百货入口国潮美陈")
    assert result.space_type is not None
    assert result.space_type.value == "百货入口"


@pytest.mark.asyncio
async def test_extract_budget(service):
    result = await service.recognize("购物中心中庭，预算15万")
    assert result.budget is not None
    assert result.budget.value == 150000


@pytest.mark.asyncio
async def test_match_points(service):
    result = await service.recognize("新春快闪店，门头×2，DP点×3")
    names = [str(p.value.get("name", "")) for p in result.points]
    assert "门头" in names
    assert "DP点" in names
```

- [ ] **Step 3: Run the tests**

```bash
cd agent-core
pytest tests/intent/test_intent_recognition.py -v
```

Expected: at least exact, alias, fuzzy, budget, and point tests pass. Semantic test may fail if embedding provider unavailable; mark as optional or ensure cache.

- [ ] **Step 4: Commit**

```bash
git add agent-core/app/services/intent_recognition.py agent-core/app/services/__init__.py agent-core/tests/intent/test_intent_recognition.py
git commit -m "feat(intent): add layered intent recognition service"
```

---

### Task 7: Integrate with TextParser

**Files:**
- Modify: `agent-core/app/agents/input_parser.py:109-238`

**Interfaces:**
- Consumes: `IntentRecognitionService.recognize`, `IntentRecognitionResult.to_dict`.
- Produces: `TextParser.parse` returns dict with recognized fields and metadata.

- [ ] **Step 1: Replace fallback parsing with service**

At the top of `agent-core/app/agents/input_parser.py`, add:

```python
from app.services.intent_recognition import get_intent_service
from app.services.intent_recognition_result import IntentRecognitionResult
```

Replace the body of `TextParser.parse` (lines 112-133) with:

```python
    async def parse(self, text: str) -> dict[str, Any]:
        service = get_intent_service()
        result = await service.recognize(text)
        data = {
            "theme": result.theme.value if result.theme else "",
            "style": result.style.value if result.style else "",
            "space_type": result.space_type.value if result.space_type else "",
            "budget": result.budget.value if result.budget else "",
            "budget_level": result.budget_level.value if result.budget_level else "",
            "target_audience": result.target_audience.value if result.target_audience else "",
            "timeline": result.timeline.value if result.timeline else "",
            "material_restrictions": [m.value for m in result.material_restrictions],
            "special_requirements": [],
            "color_preference": result.color_preference.value if result.color_preference else "",
            "brand_positioning": result.brand_positioning.value if result.brand_positioning else "",
            "design_system_preference": result.design_system_preference.value if result.design_system_preference else "",
            "points": [p.value for p in result.points],
            "source_type": "text",
            "_recognition_meta": {
                "space_type_source": result.space_type.source if result.space_type else None,
                "space_type_confidence": result.space_type.confidence if result.space_type else 0.0,
            },
        }
        return data
```

Keep `_get_fallback_parse` as a private method but no longer call it by default; it remains available under a feature flag if needed.

- [ ] **Step 2: Add feature flag fallback**

In `agent-core/app/core/config.py` (read first), add:

```python
intent_parser_legacy: bool = False
```

Then in `TextParser.parse`, wrap the service call:

```python
        if getattr(settings, "intent_parser_legacy", False):
            return self._get_fallback_parse(text)
```

- [ ] **Step 3: Write integration test**

Create `agent-core/tests/intent/test_text_parser.py`:

```python
import pytest

from app.agents.input_parser import TextParser


@pytest.mark.asyncio
async def test_text_parser_recognizes_pop_up():
    parser = TextParser()
    data = await parser.parse("新春国潮快闪店，预算15万")
    assert data["space_type"] == "快闪店"
    assert data["budget"] == 150000
    assert data["_recognition_meta"]["space_type_source"] == "exact"
```

- [ ] **Step 4: Run test**

```bash
cd agent-core
pytest tests/intent/test_text_parser.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/agents/input_parser.py agent-core/app/core/config.py agent-core/tests/intent/test_text_parser.py
git commit -m "feat(intent): wire TextParser to IntentRecognitionService"
```

---

### Task 8: Integrate Multi-Modal Parsers

**Files:**
- Modify: `agent-core/app/agents/input_parser.py:31-106`

**Interfaces:**
- Consumes: `Taxonomy` standard lists via `taxonomy_loader`.
- Produces: VLM prompts constrained to taxonomy; output dicts contain standardized values.

- [ ] **Step 1: Add taxonomy serialization helper**

At the top of `agent-core/app/agents/input_parser.py`, add:

```python
from app.services.taxonomy_loader import load_taxonomy

_TAXONOMY = load_taxonomy()


def _taxonomy_prompt_fragment() -> str:
    space_types = [s["name"] for s in _TAXONOMY.space_types]
    points = [p["name"] for p in _TAXONOMY.points]
    styles = [s["name"] for s in _TAXONOMY.styles]
    materials = [m["name"] for m in _TAXONOMY.materials]
    return (
        "空间类型必须从以下候选中选择：" + ", ".join(space_types) + "\n"
        "点位必须从以下候选中选择：" + ", ".join(points) + "\n"
        "风格必须从以下候选中选择：" + ", ".join(styles) + "\n"
        "材质必须从以下候选中选择：" + ", ".join(materials) + "\n"
        "无法确定时请返回 null。"
    )
```

- [ ] **Step 2: Update PhotoParser prompt**

Replace the `PhotoParser.parse` prompt (lines 36-43) with:

```python
        prompt = (
            "你是一位商业空间视觉分析师。请分析这张现场照片，输出以下 JSON 字段（只输出 JSON，不要多余文字）：\n"
            '{"space_type": "空间类型", "estimated_area": "估算面积", "ceiling_height": "天花板高度", '
            '"existing_elements": ["现有装饰物"], "lighting_condition": "光照条件", '
            '"crowd_flow": "人流特征", "notes": "其他观察"}\n'
            + _taxonomy_prompt_fragment()
        )
```

- [ ] **Step 3: Update ReferenceParser prompt**

Replace the `ReferenceParser.parse` prompt (lines 93-97) with:

```python
        prompt = (
            "请分析这张参考图，输出以下 JSON 字段（只输出 JSON）：\n"
            '{"style": "风格", "theme": "主题", "color_palette": ["主要颜色"], '
            '"materials": ["材质"], "space_type": "适用空间类型", '
            '"design_elements": ["设计元素"], "mood": "氛围关键词"}\n'
            + _taxonomy_prompt_fragment()
        )
```

- [ ] **Step 4: Normalize VLM outputs**

Add a helper to coerce values to taxonomy standards:

```python
    def _normalize_vlm_value(self, value: Any, field: str) -> Any:
        if not value or not isinstance(value, str):
            return value
        lowered = value.lower()
        mapping: dict[str, dict[str, str]] = {
            "space_type": _TAXONOMY.alias_to_space_type,
            "style": _TAXONOMY.alias_to_style,
            "material": _TAXONOMY.alias_to_material,
            "point": _TAXONOMY.alias_to_point,
        }
        alias_map = mapping.get(field, {})
        return alias_map.get(lowered, value)
```

Apply it in `PhotoParser.parse` after `json.loads`:

```python
        data["space_type"] = self._normalize_vlm_value(data.get("space_type"), "space_type")
```

And similarly in `ReferenceParser.parse` for `style`, `materials`, and `space_type`.

- [ ] **Step 5: Write test**

Create `agent-core/tests/intent/test_multimodal_parser.py`:

```python
from app.agents.input_parser import PhotoParser, ReferenceParser


def test_photo_parser_normalizes_space_type():
    parser = PhotoParser()
    assert parser._normalize_vlm_value("popup store", "space_type") == "快闪店"
    assert parser._normalize_vlm_value("快闪店", "space_type") == "快闪店"
```

- [ ] **Step 6: Run test and commit**

```bash
cd agent-core
pytest tests/intent/test_multimodal_parser.py -v
```

Expected: 1 passed.

```bash
git add agent-core/app/agents/input_parser.py agent-core/tests/intent/test_multimodal_parser.py
git commit -m "feat(intent): constrain multi-modal parsers to taxonomy"
```

---

### Task 9: Create Golden Test Set and Evaluator

**Files:**
- Create: `agent-core/tests/intent/golden_cases.jsonl`
- Create: `agent-core/tests/intent/evaluator.py`

**Interfaces:**
- Consumes: `IntentRecognitionService`, golden cases.
- Produces: accuracy report dict.

- [ ] **Step 1: Write golden cases**

Create `agent-core/tests/intent/golden_cases.jsonl` (one JSON object per line):

```json
{"input": "购物中心中庭海洋主题，预算15万", "expected": {"space_type": "购物中心中庭", "budget": 150000, "budget_level": "medium"}, "tags": ["exact", "budget"]}
{"input": "popup store 新春国潮", "expected": {"space_type": "快闪店"}, "tags": ["alias"]}
{"input": "百货入口轻奢灯光装置", "expected": {"space_type": "百货入口"}, "tags": ["fuzzy"]}
{"input": "商场入口国潮美陈", "expected": {"space_type": "百货入口"}, "tags": ["semantic"]}
{"input": "夏季度假风步行街", "expected": {"space_type": "步行街"}, "tags": ["exact"]}
{"input": "快闪店需要门头×2、DP点×3、合影墙", "expected": {"space_type": "快闪店", "points": [{"name": "门头", "count": 2}, {"name": "DP点", "count": 3}, {"name": "合影墙", "count": 1}]}, "tags": ["points"]}
{"input": "预算低，中式风格", "expected": {"budget_level": "low", "style": "国潮"}, "tags": ["budget_level", "style"]}
```

- [ ] **Step 2: Implement evaluator**

Create `agent-core/tests/intent/evaluator.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_recognition_result import IntentRecognitionResult


GOLDEN_CASES_PATH = Path(__file__).parent / "golden_cases.jsonl"


def load_cases(path: Path = GOLDEN_CASES_PATH) -> list[dict[str, Any]]:
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


async def evaluate(service: IntentRecognitionService | None = None) -> dict[str, Any]:
    service = service or IntentRecognitionService()
    cases = load_cases()
    total = len(cases)
    passed = 0
    failures: list[dict[str, Any]] = []

    for case in cases:
        result = await service.recognize(case["input"])
        ok, details = _check_case(case, result)
        if ok:
            passed += 1
        else:
            failures.append({"input": case["input"], "expected": case["expected"], "got": details})

    return {
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "failures": failures,
    }


def _check_case(case: dict[str, Any], result: IntentRecognitionResult) -> tuple[bool, dict[str, Any]]:
    expected = case["expected"]
    details: dict[str, Any] = {}
    all_ok = True

    if "space_type" in expected:
        got = result.space_type.value if result.space_type else None
        details["space_type"] = got
        if got != expected["space_type"]:
            all_ok = False

    if "budget" in expected:
        got = result.budget.value if result.budget else None
        details["budget"] = got
        if got != expected["budget"]:
            all_ok = False

    if "budget_level" in expected:
        got = result.budget_level.value if result.budget_level else None
        details["budget_level"] = got
        if got != expected["budget_level"]:
            all_ok = False

    if "style" in expected:
        got = result.style.value if result.style else None
        details["style"] = got
        if got != expected["style"]:
            all_ok = False

    if "points" in expected:
        got = sorted([p.value for p in result.points], key=lambda x: x.get("name", ""))
        details["points"] = got
        expected_sorted = sorted(expected["points"], key=lambda x: x.get("name", ""))
        if got != expected_sorted:
            all_ok = False

    return all_ok, details


if __name__ == "__main__":
    import asyncio

    report = asyncio.run(evaluate())
    print(json.dumps(report, ensure_ascii=False, indent=2))
```

- [ ] **Step 3: Add CI test**

Create `agent-core/tests/intent/test_evaluator.py`:

```python
import pytest

from tests.intent.evaluator import evaluate


@pytest.mark.asyncio
async def test_golden_case_accuracy():
    report = await evaluate()
    assert report["accuracy"] >= 0.8, f"Accuracy {report['accuracy']} below 0.8: {report['failures']}"
```

- [ ] **Step 4: Run evaluator**

```bash
cd agent-core
python tests/intent/evaluator.py
```

Expected: prints accuracy report.

- [ ] **Step 5: Run CI test**

```bash
cd agent-core
pytest tests/intent/test_evaluator.py -v
```

Expected: 1 passed if accuracy >= 0.8.

- [ ] **Step 6: Commit**

```bash
git add agent-core/tests/intent/golden_cases.jsonl agent-core/tests/intent/evaluator.py agent-core/tests/intent/test_evaluator.py
git commit -m "test(intent): add golden test set and accuracy evaluator"
```

---

### Task 10: Add Context Completion

**Files:**
- Modify: `agent-core/app/services/intent_recognition.py`
- Modify: `agent-core/app/agents/input_parser.py` (InputMerger if needed)

**Interfaces:**
- Consumes: `last_intent` result.
- Produces: filled `IntentRecognitionResult`.

- [ ] **Step 1: Improve fill_missing_from_context**

The method already exists in Task 6. Enhance it to use `field_defaults`:

```python
    def fill_missing_from_context(
        self,
        result: IntentRecognitionResult,
        last_intent: IntentRecognitionResult | None,
    ) -> IntentRecognitionResult:
        if last_intent is None:
            return result

        inherit_fields = ["style", "color_preference", "brand_positioning", "design_system_preference"]
        for field_name in inherit_fields:
            current = getattr(result, field_name)
            previous = getattr(last_intent, field_name)
            if current is None and previous is not None:
                setattr(result, field_name, previous)

        # Inherit lists
        for field_name in ["material_restrictions", "special_requirements"]:
            current = getattr(result, field_name)
            previous = getattr(last_intent, field_name)
            if not current and previous:
                setattr(result, field_name, previous)

        return result

    def apply_defaults(self, result: IntentRecognitionResult) -> IntentRecognitionResult:
        defaults = self.taxonomy.field_defaults
        space_type_value = result.space_type.value if result.space_type else None

        # Default points by space type
        points_default = defaults.get("points", {}).get("default_by_space_type", {}).get(space_type_value)
        if points_default and not result.points:
            result.points = [
                RecognizedField(name="point", value={"name": p, "count": 1}, source=FieldSource.DEFAULT, confidence=0.6)
                for p in points_default
            ]

        # Default timeline
        if result.timeline is None and defaults.get("timeline", {}).get("default_value"):
            result.timeline = RecognizedField(
                name="timeline",
                value=defaults["timeline"]["default_value"],
                source=FieldSource.DEFAULT,
                confidence=0.5,
            )

        return result
```

- [ ] **Step 2: Add unit test**

Append to `agent-core/tests/intent/test_intent_recognition.py`:

```python
@pytest.mark.asyncio
async def test_apply_defaults(service):
    result = await service.recognize("快闪店")
    result = service.apply_defaults(result)
    names = [str(p.value.get("name")) for p in result.points]
    assert "门头" in names
    assert "DP点" in names
    assert "合影墙" in names
```

- [ ] **Step 3: Run and commit**

```bash
cd agent-core
pytest tests/intent/test_intent_recognition.py -v
```

Expected: new test passes.

```bash
git add agent-core/app/services/intent_recognition.py agent-core/tests/intent/test_intent_recognition.py
git commit -m "feat(intent): add context inheritance and domain defaults"
```

---

### Task 11: End-to-End Integration and Validation

**Files:**
- Modify: `agent-core/app/agents/input_parser.py` (InputMerger if needed)
- Run: full workflow test.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: working parser pipeline.

- [ ] **Step 1: Run all intent tests**

```bash
cd agent-core
pytest tests/intent/ -v
```

Expected: all tests pass (semantic tests may be skipped if embedding unavailable).

- [ ] **Step 2: Run existing workflow test**

```bash
cd agent-core
pytest tests/test_workflow.py -v
```

Expected: existing tests still pass.

- [ ] **Step 3: Manual smoke test**

Start agent-core:

```bash
cd agent-core
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"text": "新春国潮快闪店，预算15万"}'
```

Expected: response contains `space_type="快闪店"` and `budget=150000`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(intent): integrate recognition service end-to-end"
```

---

## Self-Review

- **Spec coverage:**
  - Domain taxonomy → Task 2.
  - Layered recognition → Task 6.
  - Semantic matching → Task 5.
  - Constrained LLM fallback → Task 6 `_llm_fallback`.
  - Cross-modal taxonomy injection → Task 8.
  - Golden test set + CI → Task 9.
  - Context completion/defaults → Task 10.
  - No gaps identified.

- **Placeholder scan:** No TBD/TODO placeholders found.

- **Type consistency:** `IntentRecognitionResult` and `RecognizedField` are used consistently across tasks.
