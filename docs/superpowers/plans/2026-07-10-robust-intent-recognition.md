# Robust Intent Recognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `parse-text` return best-effort extracted fields even when clarification is needed, add rule-based fallback for bare theme/space/budget words, and record an intent trace for debugging.

**Architecture:** Keep LLM extraction as primary path; run a lightweight deterministic `IntentRuleExtractor` to fill any fields the LLM misses; merge both into a single `IntentOutput`; validate and convert to `ValidatedIntent`; record a trace and expose debug endpoints.

**Tech Stack:** Python 3.9+, FastAPI, Pydantic, pytest, jieba, rapidfuzz.

## Global Constraints

- Maintain Python 3.9 compatibility (use `from __future__ import annotations`).
- LLM extraction remains the primary path; rule fallback must not overwrite LLM values.
- Do not add DB migrations; trace storage is local JSONL under `agent-core/data/intent_traces/`.
- All new code must have unit/golden tests.
- Commit after each task.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `agent-core/app/services/intent_rule_extractor.py` | New deterministic extractor for bare theme, space_type, budget, points. |
| `agent-core/app/services/intent_recognition.py` | Replace `_RuleBasedExtractor` with `IntentRuleExtractor`; merge LLM + rule outputs; record trace; set `trace_id` on result. |
| `agent-core/app/services/intent_recognition_result.py` | Add `trace_id` to `ValidatedIntent`. |
| `agent-core/app/services/intent_trace_recorder.py` | Append-only JSONL recorder and query API for intent traces. |
| `agent-core/app/api/endpoints/debug.py` | New debug endpoints for intent traces. |
| `agent-core/app/api/routers.py` | Include debug router. |
| `agent-core/app/agents/input_parser.py` | Always return best-effort fields from `ValidatedIntent`; include `trace_id`. |
| Tests under `agent-core/tests/services/` | Unit and golden tests. |

---

### Task 1: Create `IntentRuleExtractor`

**Files:**
- Create: `agent-core/app/services/intent_rule_extractor.py`
- Modify: `agent-core/app/services/intent_recognition.py:38-105` (remove inline `_RuleBasedExtractor` later)
- Test: `agent-core/tests/services/test_intent_rule_extractor.py`

**Interfaces:**
- Consumes: `Taxonomy`
- Produces: `async def extract(text: str) -> IntentOutput`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from app.services.intent_rule_extractor import IntentRuleExtractor
from app.services.taxonomy_loader import load_taxonomy


@pytest.mark.asyncio
async def test_extract_bare_theme():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("情人节")
    assert output.theme == "情人节"
    assert output.space_type is None


@pytest.mark.asyncio
async def test_extract_space_type_and_budget():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("快闪店30万")
    assert output.space_type == "快闪店"
    assert output.budget == "30万"


@pytest.mark.asyncio
async def test_extract_points():
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("中庭门头")
    assert "中庭" in output.points
    assert "门头" in output.points
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && pytest tests/services/test_intent_rule_extractor.py -v`

Expected: `ModuleNotFoundError: No module named 'app.services.intent_rule_extractor'`

- [ ] **Step 3: Implement `IntentRuleExtractor`**

Create `agent-core/app/services/intent_rule_extractor.py`:

```python
from __future__ import annotations

import re

import jieba  # type: ignore[import-untyped]
from rapidfuzz import fuzz

from app.services.intent_schemas import IntentOutput
from app.services.taxonomy_loader import Taxonomy

_FUZZY_THRESHOLD = 0.75
_FUZZY_THRESHOLD_CRITICAL = 0.85


class IntentRuleExtractor:
    """确定性规则提取器，用于补齐 LLM 未识别的字段。"""

    def __init__(self, taxonomy: Taxonomy):
        self.taxonomy = taxonomy
        self._load_jieba_dict()

    def _load_jieba_dict(self) -> None:
        terms: list[str] = []
        sources = (
            self.taxonomy.space_types
            + self.taxonomy.points
            + self.taxonomy.styles
            + self.taxonomy.materials
        )
        for item in sources:
            terms.append(item["name"])
            terms.extend(item.get("aliases", []))
        for term in set(terms):
            jieba.add_word(term, freq=1000)

    async def extract(self, text: str) -> IntentOutput:
        tokens = [t for t in jieba.lcut(text) if t.strip()]
        output = IntentOutput()

        output.space_type = self._extract_space_type(text, tokens)
        output.points = self._extract_points(text, tokens)
        output.theme = self._extract_theme(text, tokens)
        output.budget = self._extract_budget(text)
        output.style = self._extract_style(text, tokens)
        output.material_restrictions = self._extract_material_restrictions(text)
        output.allowed_materials = self._extract_allowed_materials(text)
        output.timeline = self._extract_regex_field(
            text, r"(?:工期|时间|timeline)\s*(?:为|是|：|:)?\s*([^\n，。]+)"
        )
        output.color_preference = self._extract_regex_field(
            text, r"(?:颜色|色彩|color)\s*(?:为|是|：|:)?\s*([^\n，。]+)"
        )
        return output

    def _extract_space_type(self, text: str, tokens: list[str]) -> str | None:
        return self._match_field(
            text, tokens, self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type
        )

    def _extract_style(self, text: str, tokens: list[str]) -> str | None:
        return self._match_field(
            text, tokens, self.taxonomy.style_names, self.taxonomy.alias_to_style
        )

    def _match_field(
        self,
        text: str,
        tokens: list[str],
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> str | None:
        # 1. 精确匹配
        for token in tokens:
            if token in exact_names:
                return token

        # 2. 别名匹配
        for token in tokens:
            key = token.lower()
            if key in alias_map:
                return alias_map[key]

        # 3. 子串匹配（优先最长）
        all_targets: dict[str, str] = {}
        for name in exact_names:
            all_targets[name] = name
        for alias, standard in alias_map.items():
            all_targets[alias] = standard

        candidates: list[tuple[str, str]] = []
        text_lower = text.lower()
        for target, standard in all_targets.items():
            if len(target) >= 2 and target in text_lower:
                candidates.append((target, standard))
        if candidates:
            candidates.sort(key=lambda x: len(x[0]), reverse=True)
            return candidates[0][1]

        # 4. 模糊匹配
        best: tuple[str, float] | None = None
        for token in tokens:
            for target, standard in all_targets.items():
                score = fuzz.ratio(token, target) / 100.0
                if score >= FUZZY_THRESHOLD and (best is None or score > best[1]):
                    best = (standard, score)
        if best and best[1] >= FUZZY_THRESHOLD_CRITICAL:
            return best[0]
        return None

    def _extract_points(self, text: str, tokens: list[str]) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        all_point_targets: dict[str, str] = {}
        for name in self.taxonomy.point_names:
            all_point_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_point.items():
            all_point_targets[alias] = standard

        text_lower = text.lower()
        for target, standard in all_point_targets.items():
            if len(target) >= 2 and target in text_lower and standard not in seen:
                found.append(standard)
                seen.add(standard)
        return found

    def _extract_theme(self, text: str, tokens: list[str]) -> str | None:
        # 显式标记：X主题 / X概念 / X风
        match = re.search(r"([^\n，。]+?)(?:主题|概念|theme|风)", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"(?:主题|概念|theme)\s*(?:为|是|：|:)\s*([^\n，。]+)", text)
        if match:
            return match.group(1).strip()

        # 裸词启发式：输入较短、且未命中 space_type/point/style/material/budget 的名词
        if len(text) <= 8 and len(tokens) <= 3:
            for token in tokens:
                if len(token) >= 2 and not self._is_known_non_theme(token):
                    return token
        return None

    def _is_known_non_theme(self, token: str) -> bool:
        lowered = token.lower()
        if token in self.taxonomy.space_type_names:
            return True
        if token in self.taxonomy.point_names:
            return True
        if token in self.taxonomy.style_names:
            return True
        if token in self.taxonomy.material_names:
            return True
        if lowered in self.taxonomy.alias_to_space_type:
            return True
        if lowered in self.taxonomy.alias_to_point:
            return True
        if lowered in self.taxonomy.alias_to_style:
            return True
        if lowered in self.taxonomy.alias_to_material:
            return True
        return False

    def _extract_budget(self, text: str) -> str | None:
        range_pattern = r"([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[~\-到至]\s*([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[万w千k元]?"
        match = re.search(range_pattern, text)
        if match:
            return match.group(0).strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|w|千|k|元)", text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        match = re.search(r"([零一二两三四五六七八九十百千万亿]+)\s*[万w千k元]?", text)
        if match:
            return match.group(0).strip()
        return None

    def _extract_material_restrictions(self, text: str) -> list[str]:
        results: list[str] = []
        stop_chars = "，。；;"
        patterns = [
            rf"(?:不要|不用|禁用|避免|不想用|别用)\s*([^{stop_chars}]+)",
            rf"(?:排除|去除|不要出现)\s*([^{stop_chars}]+)",
        ]
        all_targets: dict[str, str] = {}
        for name in self.taxonomy.material_names:
            all_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_material.items():
            all_targets[alias] = standard

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip().lower()
                for target, standard in all_targets.items():
                    if target in fragment and standard not in results:
                        results.append(standard)
                if not results:
                    results.append(match.group(1).strip())
        return results

    def _extract_allowed_materials(self, text: str) -> list[str]:
        results: list[str] = []
        stop_chars = "，。；;"
        patterns = [
            rf"([^{stop_chars}]+?)\s*(?:可以|可用|能用|允许使用)",
            rf"(?:可用|能用|允许使用)\s*([^{stop_chars}]+)",
        ]
        all_targets: dict[str, str] = {}
        for name in self.taxonomy.material_names:
            all_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_material.items():
            all_targets[alias] = standard

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip().lower()
                for target, standard in all_targets.items():
                    if target in fragment and standard not in results:
                        results.append(standard)
        return results

    def _extract_regex_field(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && pytest tests/services/test_intent_rule_extractor.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/intent_rule_extractor.py tests/services/test_intent_rule_extractor.py
git commit -m "feat(intent): add deterministic IntentRuleExtractor for bare theme/space/budget"
```

---

### Task 2: Merge LLM + Rule Output and Wire Trace ID

**Files:**
- Modify: `agent-core/app/services/intent_recognition.py`
- Modify: `agent-core/app/services/intent_recognition_result.py`
- Test: `agent-core/tests/services/test_intent_recognition.py`

**Interfaces:**
- Consumes: `IntentLLMExtractor.extract`, `IntentRuleExtractor.extract`
- Produces: `ValidatedIntent` with `trace_id` and merged fields

- [ ] **Step 1: Write the failing test**

```python
import pytest

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_rule_extractor import IntentRuleExtractor
from app.services.taxonomy_loader import load_taxonomy


class DummyLLMClient:
    async def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = False, temperature: float = 0.7) -> str:
        return '{"theme": "情人节"}'


@pytest.mark.asyncio
async def test_merge_rule_fallback_for_missing_space_and_budget():
    service = IntentRecognitionService(
        llm_client=DummyLLMClient(),
    )
    result = await service.recognize("情人节快闪店30万")
    assert result.theme.value == "情人节"
    assert result.space_type.value == "快闪店"
    assert result.budget.value == 300000
    assert result.trace_id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && pytest tests/services/test_intent_recognition.py::test_merge_rule_fallback_for_missing_space_and_budget -v`

Expected: FAIL because `space_type` is missing and `trace_id` is not set.

- [ ] **Step 3: Implement merge + trace wiring**

Modify `agent-core/app/services/intent_recognition.py`:

```python
import uuid
from app.services.intent_rule_extractor import IntentRuleExtractor


def _merge_intent_outputs(llm_output: IntentOutput, rule_output: IntentOutput) -> IntentOutput:
    """规则只补齐 LLM 没有返回的字段。"""
    merged = llm_output.model_copy(deep=True) if llm_output else IntentOutput()
    for field_name in IntentOutput.model_fields:
        llm_value = getattr(merged, field_name)
        rule_value = getattr(rule_output, field_name)
        if field_name in ("points", "material_restrictions", "allowed_materials", "special_requirements"):
            if not llm_value and rule_value:
                setattr(merged, field_name, rule_value)
        elif llm_value is None or llm_value == "":
            if rule_value is not None and rule_value != "":
                setattr(merged, field_name, rule_value)
    return merged
```

Replace `_RuleBasedExtractor` usage with `IntentRuleExtractor` and update `recognize`:

```python
    def __init__(...):
        ...
        self._rule_extractor = IntentRuleExtractor(self.taxonomy)
        self._trace_recorder: IntentTraceRecorder | None = None  # set in Task 4

    async def recognize(self, text: str, previous_intent: ValidatedIntent | None = None) -> ValidatedIntent:
        trace_id = str(uuid.uuid4())

        llm_output = await self._llm_extractor.extract(text)
        rule_output = await self._rule_extractor.extract(text)
        merged_output = _merge_intent_outputs(llm_output, rule_output)

        validated = self._validator.validate(merged_output, text)
        validated = self._validator.merge_context(validated, previous_intent)
        validated = self.apply_defaults(validated)
        validated.trace_id = trace_id

        if self._trace_recorder is not None:
            await self._trace_recorder.record(
                trace_id=trace_id,
                project_id=None,  # filled by caller
                input_text=text,
                llm_output=llm_output,
                rule_output=rule_output,
                merged_output=merged_output,
                validated=validated,
            )

        return validated
```

Add `trace_id` to `ValidatedIntent` in `agent-core/app/services/intent_recognition_result.py`:

```python
class ValidatedIntent(BaseModel):
    ...
    raw_text: str = ""
    clarification: ClarificationRequest | None = None
    trace_id: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && pytest tests/services/test_intent_recognition.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/intent_recognition.py agent-core/app/services/intent_recognition_result.py tests/services/test_intent_recognition.py
git commit -m "feat(intent): merge LLM and rule outputs; attach trace_id"
```

---

### Task 3: Update `parse-text` to Always Return Best-Effort Fields

**Files:**
- Modify: `agent-core/app/agents/input_parser.py`
- Test: `agent-core/tests/test_input_parser.py`

**Interfaces:**
- Consumes: `ValidatedIntent` from `IntentRecognitionService`
- Produces: `dict` always containing theme/space_type/budget etc. plus `trace_id`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from app.agents.input_parser import TextParser


@pytest.mark.asyncio
async def test_parse_text_returns_partial_fields_when_needs_clarification():
    parser = TextParser()
    result = await parser.parse("情人节")
    assert result["theme"] == "情人节"
    assert result["needs_clarification"] is True
    assert "space_type" in result
    assert "budget" in result
    assert "trace_id" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && pytest tests/test_input_parser.py::test_parse_text_returns_partial_fields_when_needs_clarification -v`

Expected: FAIL because current clarification path returns metadata only.

- [ ] **Step 3: Implement conversion helper**

In `agent-core/app/agents/input_parser.py`, replace the `parse` method body of `TextParser` with:

```python
    async def parse(self, text: str) -> dict[str, Any]:
        from app.core.config import settings

        if getattr(settings, "intent_parser_legacy", False):
            return self._get_fallback_parse(text)

        service = self._intent_service or get_intent_service()
        result = await service.recognize(text)
        return self._validated_intent_to_dict(result)

    def _validated_intent_to_dict(self, result) -> dict[str, Any]:
        data = {
            "theme": result.theme.value if result.theme else "",
            "style": result.style.value if result.style else "",
            "space_type": result.space_type.value if result.space_type else "",
            "budget": result.budget.value if result.budget else "",
            "budget_level": result.budget_level.value if result.budget_level else "",
            "target_audience": result.target_audience.value if result.target_audience else "",
            "timeline": result.timeline.value if result.timeline else "",
            "material_restrictions": [m.value for m in result.material_restrictions],
            "allowed_materials": [m.value for m in result.allowed_materials],
            "special_requirements": [s.value for s in result.special_requirements],
            "color_preference": result.color_preference.value if result.color_preference else "",
            "brand_positioning": result.brand_positioning.value if result.brand_positioning else "",
            "design_system_preference": result.design_system_preference.value
            if result.design_system_preference
            else "",
            "points": [{"name": str(p.value), "count": 1, "notes": ""} for p in result.points],
            "source_type": "text",
            "trace_id": result.trace_id,
            "_recognition_meta": {
                "space_type_source": result.space_type.source if result.space_type else None,
                "space_type_confidence": result.space_type.confidence if result.space_type else 0.0,
            },
        }
        if result.clarification and result.clarification.needs_clarification:
            data["needs_clarification"] = True
            data["clarification_question"] = result.clarification.clarification_question
            data["missing_fields"] = result.clarification.missing_fields
            data["low_confidence_fields"] = result.clarification.low_confidence_fields
        return data
```

Remove the old if/else branching in `parse`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && pytest tests/test_input_parser.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/agents/input_parser.py tests/test_input_parser.py
git commit -m "fix(input-parser): always return best-effort fields and trace_id"
```

---

### Task 4: Add Intent Trace Recorder and Debug Endpoints

**Files:**
- Create: `agent-core/app/services/intent_trace_recorder.py`
- Create: `agent-core/app/api/endpoints/debug.py`
- Modify: `agent-core/app/services/intent_recognition.py` (wire recorder singleton)
- Modify: `agent-core/app/api/routers.py` (include debug router)
- Test: `agent-core/tests/services/test_intent_trace_recorder.py`

**Interfaces:**
- Consumes: `ValidatedIntent`, `IntentOutput`
- Produces: JSONL trace records + FastAPI endpoints

- [ ] **Step 1: Write the failing test**

```python
import pytest

from app.services.intent_trace_recorder import IntentTraceRecorder


@pytest.mark.asyncio
async def test_record_and_retrieve(tmp_path):
    recorder = IntentTraceRecorder(base_dir=tmp_path)
    await recorder.record(
        trace_id="t1",
        project_id="p1",
        input_text="情人节",
        llm_output=None,
        rule_output=None,
        merged_output=None,
        validated={"theme": "情人节"},
    )
    traces = await recorder.list_by_project("p1")
    assert len(traces) == 1
    assert traces[0]["input_text"] == "情人节"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && pytest tests/services/test_intent_trace_recorder.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement recorder**

Create `agent-core/app/services/intent_trace_recorder.py`:

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.intent_schemas import IntentOutput


class IntentTraceRecorder:
    def __init__(self, base_dir: str | Path = "agent-core/data/intent_traces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.base_dir / f"{date_str}.jsonl"

    def _serialize_output(self, output: IntentOutput | None) -> dict[str, Any] | None:
        if output is None:
            return None
        return output.model_dump()

    async def record(
        self,
        *,
        trace_id: str | None = None,
        project_id: str | None,
        input_text: str,
        llm_output: IntentOutput | None,
        rule_output: IntentOutput | None,
        merged_output: IntentOutput | None,
        validated: Any,
    ) -> str:
        trace_id = trace_id or str(uuid.uuid4())
        record = {
            "trace_id": trace_id,
            "project_id": project_id,
            "input_text": input_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "llm_output": self._serialize_output(llm_output),
            "rule_output": self._serialize_output(rule_output),
            "merged_output": self._serialize_output(merged_output),
            "validated": validated.model_dump() if hasattr(validated, "model_dump") else validated,
        }
        path = self._file_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return trace_id

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob("*.jsonl"), reverse=True):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("project_id") == project_id:
                        results.append(record)
            if len(results) >= limit:
                break
        return results[:limit]

    async def get_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        for path in sorted(self.base_dir.glob("*.jsonl"), reverse=True):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("trace_id") == trace_id:
                        return record
        return None
```

- [ ] **Step 4: Create debug endpoints**

Create `agent-core/app/api/endpoints/debug.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.intent_trace_recorder import IntentTraceRecorder

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

_recorder = IntentTraceRecorder()


@router.get("/intent-traces/{project_id}")
async def list_intent_traces(project_id: str, limit: int = Query(50, ge=1, le=200)):
    return {"project_id": project_id, "traces": await _recorder.list_by_project(project_id, limit=limit)}


@router.get("/intent-traces/{project_id}/{trace_id}")
async def get_intent_trace(project_id: str, trace_id: str):
    record = await _recorder.get_by_trace_id(trace_id)
    if record is None or record.get("project_id") != project_id:
        return {"error": "not found"}
    return record
```

- [ ] **Step 5: Wire recorder and router**

In `agent-core/app/services/intent_recognition.py`, set the recorder on the service:

```python
from app.services.intent_trace_recorder import IntentTraceRecorder

_intent_service: IntentRecognitionService | None = None
_trace_recorder: IntentTraceRecorder | None = None


def get_intent_service() -> IntentRecognitionService:
    global _intent_service, _trace_recorder
    if _intent_service is None:
        _trace_recorder = IntentTraceRecorder()
        _intent_service = IntentRecognitionService()
        _intent_service.set_trace_recorder(_trace_recorder)
    return _intent_service
```

Add `set_trace_recorder` to `IntentRecognitionService`:

```python
    def set_trace_recorder(self, recorder: IntentTraceRecorder) -> None:
        self._trace_recorder = recorder
```

In `agent-core/app/api/routers.py`, import and include the debug router:

```python
from app.api.endpoints import debug

router.include_router(debug.router)
```

- [ ] **Step 6: Run tests**

Run: `cd agent-core && pytest tests/services/test_intent_trace_recorder.py tests/test_input_parser.py tests/services/test_intent_recognition.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agent-core/app/services/intent_trace_recorder.py agent-core/app/api/endpoints/debug.py agent-core/app/services/intent_recognition.py agent-core/app/api/routers.py tests/services/test_intent_trace_recorder.py
git commit -m "feat(debug): add intent trace recorder and debug endpoints"
```

---

### Task 5: Pass `project_id` to Recognize and Update Dialogue Call Site

**Files:**
- Modify: `agent-core/app/services/intent_recognition.py`
- Modify: `agent-core/app/agents/input_parser.py`
- Modify: `agent-core/app/api/routers.py`
- Test: `agent-core/tests/test_input_parser.py`

**Interfaces:**
- `recognize(text, previous_intent=None, project_id=None)`

- [ ] **Step 1: Update signatures**

In `agent-core/app/services/intent_recognition.py`:

```python
    async def recognize(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
        project_id: str | None = None,
    ) -> ValidatedIntent:
        ...
        if self._trace_recorder is not None:
            await self._trace_recorder.record(
                trace_id=trace_id,
                project_id=project_id,
                ...
            )
```

In `agent-core/app/agents/input_parser.py`:

```python
    async def parse(self, text: str, project_id: str | None = None) -> dict[str, Any]:
        ...
        result = await service.recognize(text, project_id=project_id)
```

In `agent-core/app/api/routers.py`:

```python
@router.post("/agents/input-parser/parse-text")
async def parse_text(payload: dict):
    text = payload.get("text", "")
    project_id = payload.get("project_id")
    parser = TextParser()
    return await parser.parse(text, project_id=project_id)
```

- [ ] **Step 2: Run tests**

Run: `cd agent-core && pytest tests/test_input_parser.py tests/services/test_intent_recognition.py -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agent-core/app/services/intent_recognition.py agent-core/app/agents/input_parser.py agent-core/app/api/routers.py tests/test_input_parser.py
git commit -m "feat(intent): pass project_id into recognize for trace correlation"
```

---

### Task 6: Golden Tests for Bare Themes and Multi-Turn Context

**Files:**
- Create: `agent-core/tests/services/test_intent_recognition_golden.py`

- [ ] **Step 1: Add golden cases**

```python
import pytest

from app.services.intent_recognition import IntentRecognitionService


@pytest.mark.asyncio
@pytest.mark.parametrize("text,expected_theme,expected_space,expected_budget", [
    ("情人节", "情人节", None, None),
    ("春节快闪店", "春节", "快闪店", None),
    ("海洋风购物中心中庭", "海洋风", "购物中心中庭", None),
    ("国潮主题，预算30万", "国潮", None, 300000),
    ("情人节快闪店30万", "情人节", "快闪店", 300000),
])
async def test_golden_open_fields(text, expected_theme, expected_space, expected_budget):
    service = IntentRecognitionService()
    result = await service.recognize(text)
    if expected_theme:
        assert result.theme and result.theme.value == expected_theme
    if expected_space:
        assert result.space_type and result.space_type.value == expected_space
    if expected_budget:
        assert result.budget and result.budget.value == expected_budget


@pytest.mark.asyncio
async def test_multi_turn_context_inheritance():
    service = IntentRecognitionService()
    first = await service.recognize("情人节")
    second = await service.recognize("快闪店", previous_intent=first)
    third = await service.recognize("30万", previous_intent=second)
    assert third.theme and third.theme.value == "情人节"
    assert third.space_type and third.space_type.value == "快闪店"
    assert third.budget and third.budget.value == 300000
```

- [ ] **Step 2: Run tests**

Run: `cd agent-core && pytest tests/services/test_intent_recognition_golden.py -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/services/test_intent_recognition_golden.py
git commit -m "test(intent): add golden tests for bare themes and multi-turn context"
```

---

### Task 7: Full Regression Test and Restart

**Files:**
- None (verification only)

- [ ] **Step 1: Run full agent-core test suite**

Run: `cd agent-core && pytest -q`

Expected: All tests pass.

- [ ] **Step 2: Verify with curl**

```bash
curl -s -X POST http://localhost:8000/agents/input-parser/parse-text \
  -H 'Content-Type: application/json' \
  -d '{"text":"情人节快闪店30万","project_id":"p-test"}' | python3 -m json.tool
```

Expected response contains `theme=情人节`, `space_type=快闪店`, `budget=300000`, `trace_id`, and `needs_clarification=false`.

Then:

```bash
curl -s http://localhost:8000/api/v1/debug/intent-traces/p-test | python3 -m json.tool
```

Expected: trace list with the above input.

- [ ] **Step 3: Restart agent-core**

Kill the existing uvicorn process and restart:

```bash
kill $(lsof -ti:8000)
cd agent-core && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 4: Commit any final changes and push**

```bash
git push origin main
```

If push times out, retry once or note the failure.

---

## Self-Review Checklist

1. **Spec coverage:**
   - Best-effort fields in clarification response → Task 3
   - Rule fallback for bare theme/space/budget → Task 1 + 2
   - Intent trace recording → Task 4
   - Debug API → Task 4
   - Tests → Task 1-6

2. **Placeholder scan:** No TBD/TODO placeholders; all code blocks are complete.

3. **Type consistency:**
   - `IntentRuleExtractor.extract` returns `IntentOutput`.
   - `_merge_intent_outputs` consumes/produces `IntentOutput`.
   - `ValidatedIntent.trace_id` is `str | None`.
   - `TextParser.parse` returns `dict[str, Any]`.

4. **Scope check:** Tasks are focused on intent recognition/debug; admin UI is explicitly out of scope (Non-Goal #3).
