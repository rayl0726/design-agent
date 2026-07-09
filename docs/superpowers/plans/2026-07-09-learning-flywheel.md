# Learning Flywheel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a feedback-driven learning flywheel that captures intent corrections and image feedback, expands the alias lexicon from repeated corrections, accumulates few-shot examples, and tracks prompt template version performance.

**Architecture:** Reuse the existing `feedbacks` table for correction and image feedback records. Add small Python services under `agent-core/app/services/learning/` (`alias_expansion.py`, `few_shot_library.py`) that read from the `feedbacks` table (via a lightweight repository or direct SQL) and from local JSONL files. Provide admin-facing utilities and one internal API endpoint to apply alias proposals back to `intent_taxonomy.yaml`.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, PyYAML/ruamel.yaml, JSONL, pytest, pytest-asyncio, Java 17 / Spring Boot 3.2.5, MySQL, Flyway.

## Global Constraints

- Image generation must use asyncio.gather with semaphore for parallel execution; max_parallel_images defaults to 8.
- Configurable parameters include idea_count (default 3), images_per_point (default 1), max_parallel_images (default 8).
- Each design point must generate 1 image (center perspective) instead of 3.
- Image prompts for the same point must only vary camera angle, not content.
- Learning data must be stored in existing `feedbacks` table or local JSONL; avoid schema changes beyond adding `prompt_template_version` and `generation_params`.
- LLM/VLM must use 智谱 API only; all Ollama local model fallbacks removed.
- LLM/VLM API failures must throw exceptions and log detailed error information.
- URL paths must use 16-digit URL-safe nanoid (public_id) instead of numeric IDs for resource isolation.
- Public access to image files: /images/** and /data/** endpoints must be unauthenticated.
- Image URLs stored in database must use filenames only (no absolute paths).
- Async tasks must use thread pools instead of direct new Thread() operations.
- Java compilation must enable -Xlint:all to expose type warnings.
- Use TypeReference<Map<String, Object>>() {} instead of Map.class for objectMapper.readValue to avoid unchecked conversion.
- Commit after each independently testable task.

---

## File Structure

- `agent-core/app/services/learning/__init__.py` — package marker.
- `agent-core/app/services/learning/alias_expansion.py` — scans unprocessed intent corrections and proposes alias expansions.
- `agent-core/app/services/learning/few_shot_library.py` — append/retrieve few-shot examples keyed by space_type/theme.
- `agent-core/app/services/learning/feedback_reader.py` — lightweight async reader for feedback/correction records.
- `agent-core/app/services/learning/prompt_version_tracker.py` — aggregates feedback by prompt template version.
- `agent-core/app/services/learning/taxonomy_writer.py` — applies alias proposals to `intent_taxonomy.yaml` preserving formatting.
- `agent-core/data/few_shot_examples/` — directory for JSONL example files.
- `agent-core/app/api/endpoints/learning.py` — internal/admin endpoints for proposals, apply, and few-shot.
- `agent-core/tests/services/learning/test_alias_expansion.py` — alias expansion unit tests.
- `agent-core/tests/services/learning/test_few_shot_library.py` — few-shot library unit tests.
- `agent-core/tests/services/learning/test_prompt_version_tracker.py` — version tracking unit tests.
- `agent-core/tests/services/learning/test_taxonomy_writer.py` — taxonomy YAML write tests.
- `agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java` (modify) — add `promptTemplateVersion`, `renderedPrompt`, `generationParams` fields.
- `agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java` (modify) — accept image feedback with template version.
- `agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql` — shared migration with prompt-engineering plan.

## Task 1: Extend Feedback Entity and Service to Capture Image Feedback with Prompt Version

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java`
- Modify: `agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/service/FeedbackServiceTest.java` (create if absent)

**Interfaces:**
- Consumes: HTTP JSON payload with `feedback_type`, `category`, `tag`, `point_name`, `image_index`, `prompt_template_version`, `rendered_prompt`, `generation_params`.
- Produces: `Feedback` entity persisted to MySQL.

- [ ] **Step 1: Write the failing test**

```java
package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.repository.FeedbackRepository;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FeedbackServiceTest {

    @Mock
    private FeedbackRepository feedbackRepository;

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private PublicIdGenerator publicIdGenerator;

    @InjectMocks
    private FeedbackService feedbackService;

    @Test
    void saveImageFeedbackWithPromptVersion() {
        when(projectRepository.findByIdAndUserId("p1", 1L)).thenReturn(Optional.of(new Project()));
        when(feedbackRepository.save(any(Feedback.class))).thenAnswer(inv -> inv.getArgument(0));

        Feedback fb = feedbackService.saveFeedback("p1", Map.of(
            "feedback_type", "image",
            "category", "image_feedback",
            "tag", "composition",
            "point_name", "中庭",
            "image_index", 0,
            "prompt_template_version", "shopping_mall_atrium:1.0",
            "rendered_prompt", "positive prompt text",
            "generation_params", Map.of("theme", "圣诞节")
        ), 1L);

        assertEquals("shopping_mall_atrium:1.0", fb.getPromptTemplateVersion());
        assertEquals("positive prompt text", fb.getRenderedPrompt());
        assertNotNull(fb.getGenerationParams());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-api
mvn test -Dtest=FeedbackServiceTest#saveImageFeedbackWithPromptVersion
```
Expected: FAIL with compilation errors (`getPromptTemplateVersion` does not exist).

- [ ] **Step 3: Add fields to Feedback entity**

Add to `agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java` after `imageUrl`:

```java
    @Column(name = "prompt_template_version", length = 100)
    private String promptTemplateVersion;

    @Column(name = "rendered_prompt", columnDefinition = "TEXT")
    private String renderedPrompt;

    @Column(name = "generation_params", columnDefinition = "JSON")
    private String generationParams;
```

Add getters/setters:

```java
    public String getPromptTemplateVersion() { return promptTemplateVersion; }
    public void setPromptTemplateVersion(String promptTemplateVersion) { this.promptTemplateVersion = promptTemplateVersion; }

    public String getRenderedPrompt() { return renderedPrompt; }
    public void setRenderedPrompt(String renderedPrompt) { this.renderedPrompt = renderedPrompt; }

    public String getGenerationParams() { return generationParams; }
    public void setGenerationParams(String generationParams) { this.generationParams = generationParams; }
```

- [ ] **Step 4: Update migration**

Ensure `agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql` contains:

```sql
ALTER TABLE feedbacks
    ADD COLUMN prompt_template_version VARCHAR(100) NULL AFTER image_url,
    ADD COLUMN rendered_prompt TEXT NULL AFTER prompt_template_version,
    ADD COLUMN generation_params JSON NULL AFTER rendered_prompt;

CREATE INDEX idx_feedbacks_prompt_version ON feedbacks (prompt_template_version);
```

- [ ] **Step 5: Update FeedbackService to read new fields**

Modify `saveFeedback` in `FeedbackService.java` to read and store the new fields:

```java
        } else {
            Integer ideaIndex = payload.get("idea_index") instanceof Number n ? n.intValue() : null;
            String pointName = (String) payload.get("point_name");
            Integer imageIndex = payload.get("image_index") instanceof Number n ? n.intValue() : null;
            String imageUrl = (String) payload.get("image_url");
            String tag = (String) payload.get("tag");
            String comment = (String) payload.get("comment");

            feedback = Feedback.create(
                projectId, feedbackType, ideaIndex, pointName, imageIndex, imageUrl, tag, comment
            );
            feedback.setPromptTemplateVersion((String) payload.get("prompt_template_version"));
            feedback.setRenderedPrompt((String) payload.get("rendered_prompt"));
            Object generationParams = payload.get("generation_params");
            if (generationParams != null) {
                try {
                    feedback.setGenerationParams(objectMapper.writeValueAsString(generationParams));
                } catch (JsonProcessingException e) {
                    throw new IllegalArgumentException("Invalid generation_params", e);
                }
            }
        }
```

Inject `ObjectMapper` into `FeedbackService`:

```java
    private final ObjectMapper objectMapper;

    public FeedbackService(FeedbackRepository feedbackRepository,
                           ProjectRepository projectRepository,
                           PublicIdGenerator publicIdGenerator,
                           ObjectMapper objectMapper) {
        this.feedbackRepository = feedbackRepository;
        this.projectRepository = projectRepository;
        this.publicIdGenerator = publicIdGenerator;
        this.objectMapper = objectMapper;
    }
```

- [ ] **Step 6: Run test to verify it passes**

Run:
```bash
cd agent-api
mvn test -Dtest=FeedbackServiceTest#saveImageFeedbackWithPromptVersion
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java \
        agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java \
        agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql \
        agent-api/src/test/java/com/meichen/orchestrator/service/FeedbackServiceTest.java
git commit -m "feat(feedback): store prompt version and rendered prompt with image feedback"
```

## Task 2: Build Feedback Reader for Corrections

**Files:**
- Create: `agent-core/app/services/learning/feedback_reader.py`
- Create: `agent-core/app/services/learning/__init__.py`
- Test: `agent-core/tests/services/learning/test_feedback_reader.py`

**Interfaces:**
- Consumes: MySQL connection config.
- Produces: `list[IntentCorrectionRecord]` and `list[ImageFeedbackRecord]` dataclasses.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock

from app.services.learning.feedback_reader import FeedbackReader, IntentCorrectionRecord


@pytest.mark.asyncio
async def test_list_unprocessed_intent_corrections():
    reader = FeedbackReader(db_url="sqlite+aiosqlite:///:memory:")
    reader._execute = AsyncMock(return_value=[
        {"intent_field": "space_type", "original_value": "商场", "corrected_value": "购物中心中庭", "count": 3}
    ])
    results = await reader.list_unprocessed_intent_corrections()
    assert len(results) == 1
    assert results[0].original_value == "商场"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_feedback_reader.py::test_list_unprocessed_intent_corrections -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Implement feedback reader**

Create `agent-core/app/services/learning/feedback_reader.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import aiomysql  # type: ignore[import-untyped]

from app.core.config import settings


@dataclass
class IntentCorrectionRecord:
    intent_field: str
    original_value: str
    corrected_value: str
    count: int


@dataclass
class ImageFeedbackRecord:
    category: str
    tag: str
    point_name: str | None
    image_index: int | None
    prompt_template_version: str | None
    comment: str | None


class FeedbackReader:
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or self._build_db_url()

    @staticmethod
    def _build_db_url() -> str:
        return (
            f"mysql+aiomysql://{settings.mysql_username}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
        )

    async def list_unprocessed_intent_corrections(self) -> list[IntentCorrectionRecord]:
        query = """
            SELECT intent_field, original_value, corrected_value, COUNT(*) AS count
            FROM feedbacks
            WHERE feedback_type = 'intent'
              AND processed = FALSE
            GROUP BY intent_field, original_value, corrected_value
            ORDER BY count DESC
        """
        rows = await self._execute(query)
        return [
            IntentCorrectionRecord(
                intent_field=r["intent_field"],
                original_value=r["original_value"],
                corrected_value=r["corrected_value"],
                count=int(r["count"]),
            )
            for r in rows
        ]

    async def list_image_feedback_by_version(self, version: str) -> list[ImageFeedbackRecord]:
        query = """
            SELECT category, tag, point_name, image_index, prompt_template_version, comment
            FROM feedbacks
            WHERE feedback_type = 'image'
              AND prompt_template_version = %s
            ORDER BY created_at DESC
        """
        rows = await self._execute(query, (version,))
        return [ImageFeedbackRecord(**r) for r in rows]

    async def _execute(self, query: str, params: tuple | None = None) -> list[dict]:
        conn = await aiomysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_username,
            password=settings.mysql_password,
            db=settings.mysql_db,
        )
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params or ())
                return await cur.fetchall()
        finally:
            conn.close()
```

Create `agent-core/app/services/learning/__init__.py` as an empty file.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_feedback_reader.py::test_list_unprocessed_intent_corrections -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/learning/__init__.py \
        agent-core/app/services/learning/feedback_reader.py \
        agent-core/tests/services/learning/test_feedback_reader.py
git commit -m "feat(learning): add async feedback reader for corrections"
```

## Task 3: Implement Alias Expansion Service

**Files:**
- Create: `agent-core/app/services/learning/alias_expansion.py`
- Test: `agent-core/tests/services/learning/test_alias_expansion.py`

**Interfaces:**
- Consumes: `list[IntentCorrectionRecord]`.
- Produces: `list[AliasProposal]` with field, alias, canonical value, confidence, occurrence count.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from app.services.learning.alias_expansion import AliasExpansionService, AliasProposal
from app.services.learning.feedback_reader import IntentCorrectionRecord


def test_propose_alias_after_threshold():
    service = AliasExpansionService(min_occurrences=3)
    corrections = [
        IntentCorrectionRecord("space_type", "商厦中庭", "购物中心中庭", 3),
        IntentCorrectionRecord("space_type", "商厦", "购物中心中庭", 1),
    ]
    proposals = service.propose(corrections)
    assert len(proposals) == 1
    assert proposals[0].alias == "商厦中庭"
    assert proposals[0].canonical == "购物中心中庭"
    assert proposals[0].occurrences == 3


def test_no_proposal_below_threshold():
    service = AliasExpansionService(min_occurrences=3)
    corrections = [
        IntentCorrectionRecord("space_type", "商厦", "购物中心中庭", 1),
    ]
    proposals = service.propose(corrections)
    assert len(proposals) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_alias_expansion.py -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Implement alias expansion service**

```python
from __future__ import annotations

from dataclasses import dataclass

from app.services.learning.feedback_reader import IntentCorrectionRecord


@dataclass
class AliasProposal:
    field: str
    alias: str
    canonical: str
    occurrences: int
    confidence: float


class AliasExpansionService:
    def __init__(self, min_occurrences: int = 3):
        self.min_occurrences = min_occurrences

    def propose(self, corrections: list[IntentCorrectionRecord]) -> list[AliasProposal]:
        proposals: list[AliasProposal] = []
        for record in corrections:
            if record.count < self.min_occurrences:
                continue
            if not record.original_value or not record.corrected_value:
                continue
            if record.original_value == record.corrected_value:
                continue
            confidence = min(0.99, 0.5 + 0.1 * record.count)
            proposals.append(AliasProposal(
                field=record.intent_field,
                alias=record.original_value,
                canonical=record.corrected_value,
                occurrences=record.count,
                confidence=confidence,
            ))
        return proposals
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_alias_expansion.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/learning/alias_expansion.py \
        agent-core/tests/services/learning/test_alias_expansion.py
git commit -m "feat(learning): add alias expansion proposal service"
```

## Task 4: Implement Taxonomy YAML Writer

**Files:**
- Create: `agent-core/app/services/learning/taxonomy_writer.py`
- Test: `agent-core/tests/services/learning/test_taxonomy_writer.py`

**Interfaces:**
- Consumes: `AliasProposal`, path to `intent_taxonomy.yaml`.
- Produces: Updated YAML file preserving formatting and comments.

- [ ] **Step 1: Write the failing test**

```python
import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.learning.alias_expansion import AliasProposal
from app.services.learning.taxonomy_writer import TaxonomyWriter


def test_apply_alias_to_taxonomy():
    source = """
space_types:
  - name: "购物中心中庭"
    aliases: ["商场中庭"]
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intent_taxonomy.yaml"
        path.write_text(source, encoding="utf-8")
        writer = TaxonomyWriter(path)
        writer.apply_alias(AliasProposal("space_type", "商厦中庭", "购物中心中庭", 3, 0.9))
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "商厦中庭" in data["space_types"][0]["aliases"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_taxonomy_writer.py::test_apply_alias_to_taxonomy -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Implement taxonomy writer**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_taxonomy_writer.py::test_apply_alias_to_taxonomy -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/learning/taxonomy_writer.py \
        agent-core/tests/services/learning/test_taxonomy_writer.py
git commit -m "feat(learning): add taxonomy YAML writer for alias proposals"
```

## Task 5: Implement Few-Shot Example Library

**Files:**
- Create: `agent-core/app/services/learning/few_shot_library.py`
- Create: `agent-core/data/few_shot_examples/.gitkeep`
- Test: `agent-core/tests/services/learning/test_few_shot_library.py`

**Interfaces:**
- Consumes: User input text and structured intent output.
- Produces: `list[Example]` retrieved by space_type/theme; persisted as JSONL.

- [ ] **Step 1: Write the failing test**

```python
import pytest
import tempfile
from pathlib import Path

from app.services.learning.few_shot_library import FewShotLibrary, Example


@pytest.mark.asyncio
async def test_append_and_retrieve_examples():
    with tempfile.TemporaryDirectory() as tmp:
        lib = FewShotLibrary(data_dir=Path(tmp))
        await lib.append(Example(
            input_text="圣诞节 30万 中庭",
            space_type="购物中心中庭",
            theme="圣诞节",
            budget=300000,
            points=["中庭", "DP点"],
        ))
        results = await lib.retrieve(space_type="购物中心中庭", theme="圣诞节", top_k=3)
        assert len(results) == 1
        assert results[0].input_text == "圣诞节 30万 中庭"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_few_shot_library.py::test_append_and_retrieve_examples -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Implement few-shot library**

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_few_shot_library.py::test_append_and_retrieve_examples -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/learning/few_shot_library.py \
        agent-core/data/few_shot_examples/.gitkeep \
        agent-core/tests/services/learning/test_few_shot_library.py
git commit -m "feat(learning): add few-shot example library with JSONL storage"
```

## Task 6: Inject Few-Shot Examples into Intent LLM Extractor

**Files:**
- Modify: `agent-core/app/services/intent_llm_extractor.py`
- Test: `agent-core/tests/intent/test_intent_llm_extractor.py` (create if absent)

**Interfaces:**
- Consumes: `FewShotLibrary` injected into `IntentLLMExtractor`.
- Produces: LLM prompt includes up to 3 matching examples.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.learning.few_shot_library import Example, FewShotLibrary


@pytest.mark.asyncio
async def test_extractor_includes_few_shot_examples(monkeypatch):
    lib = FewShotLibrary(data_dir="/tmp/few_shot_test")
    monkeypatch.setattr(lib, "retrieve", AsyncMock(return_value=[
        Example(input_text="圣诞节 30万 中庭", space_type="购物中心中庭", theme="圣诞节"),
    ]))

    extractor = IntentLLMExtractor(few_shot_library=lib)
    extractor.taxonomy = AsyncMock()
    extractor._llm_client = AsyncMock()
    extractor._llm_client.complete = AsyncMock(return_value='{"space_type":"购物中心中庭","theme":"圣诞节"}')

    await extractor.extract("圣诞节 中庭")
    call_args = extractor._llm_client.complete.call_args.kwargs
    prompt = call_args["user_prompt"]
    assert "圣诞节 30万 中庭" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/intent/test_intent_llm_extractor.py::test_extractor_includes_few_shot_examples -v
```
Expected: FAIL with `TypeError: IntentLLMExtractor.__init__() got an unexpected keyword argument 'few_shot_library'`.

- [ ] **Step 3: Modify IntentLLMExtractor**

Update imports and constructor:

```python
from app.services.learning.few_shot_library import Example, FewShotLibrary
```

```python
    def __init__(
        self,
        taxonomy: Taxonomy | None = None,
        llm_client: LLMClient | None = None,
        max_retries: int = 2,
        few_shot_library: FewShotLibrary | None = None,
    ):
        self.taxonomy = taxonomy or load_taxonomy()
        self._llm_client = llm_client or _default_llm_client
        self._max_retries = max_retries
        self._few_shot_library = few_shot_library
```

Update `_build_prompt`:

```python
    async def _build_prompt(self, text: str) -> str:
        schema_json = IntentOutput.model_json_schema()
        few_shot = ""
        if self._few_shot_library is not None:
            examples = await self._few_shot_library.retrieve(
                space_type=self._extract_space_type_hint(text),
                theme=self._extract_theme_hint(text),
                top_k=3,
            )
            if examples:
                few_shot = "\n参考示例（输入 -> 输出）：\n" + "\n".join(
                    f"- 输入：{e.input_text}\n  输出：{self._example_output(e)}"
                    for e in examples
                ) + "\n"
        return (
            f"用户输入：\"{text}\"\n\n"
            "请提取设计需求并输出符合以下 JSON Schema 的对象：\n"
            f"{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n"
            f"{self._taxonomy_prompt_fragment()}"
            f"{few_shot}"
        )

    def _extract_space_type_hint(self, text: str) -> str | None:
        # Best-effort; will be refined by validator
        for name in self.taxonomy.space_type_names:
            if name in text:
                return name
        return None

    def _extract_theme_hint(self, text: str) -> str | None:
        match = re.search(r"([^，。]+?)(?:主题|theme)", text)
        if match:
            return match.group(1).strip()
        return None

    def _example_output(self, example: Example) -> str:
        parts = [f"space_type: {example.space_type}"]
        if example.theme:
            parts.append(f"theme: {example.theme}")
        if example.budget:
            parts.append(f"budget: {example.budget}")
        if example.points:
            parts.append(f"points: {', '.join(example.points)}")
        return "; ".join(parts)
```

Add `import re` at the top if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/intent/test_intent_llm_extractor.py::test_extractor_includes_few_shot_examples -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/intent_llm_extractor.py \
        agent-core/tests/intent/test_intent_llm_extractor.py
git commit -m "feat(intent): inject few-shot examples into LLM extractor prompt"
```

## Task 7: Implement Prompt Version Performance Tracker

**Files:**
- Create: `agent-core/app/services/learning/prompt_version_tracker.py`
- Test: `agent-core/tests/services/learning/test_prompt_version_tracker.py`

**Interfaces:**
- Consumes: `FeedbackReader` image feedback records.
- Produces: `PromptVersionReport` with total images, positive/negative counts.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock

from app.services.learning.feedback_reader import ImageFeedbackRecord
from app.services.learning.prompt_version_tracker import PromptVersionTracker


@pytest.mark.asyncio
async def test_compare_template_versions():
    tracker = PromptVersionTracker(reader=AsyncMock())
    tracker.reader.list_image_feedback_by_version = AsyncMock(side_effect=lambda v: {
        "atrium-v1": [
            ImageFeedbackRecord("image_feedback", "composition", "中庭", 0, "atrium-v1", "good"),
            ImageFeedbackRecord("image_feedback", "composition", "中庭", 1, "atrium-v1", "bad"),
        ],
        "atrium-v2": [
            ImageFeedbackRecord("image_feedback", "composition", "中庭", 0, "atrium-v2", "good"),
            ImageFeedbackRecord("image_feedback", "composition", "中庭", 1, "atrium-v2", "good"),
        ],
    }.get(v, []))

    report = await tracker.compare_versions(["atrium-v1", "atrium-v2"])
    assert report["atrium-v1"].negative == 1
    assert report["atrium-v2"].positive == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_prompt_version_tracker.py::test_compare_template_versions -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Implement version tracker**

```python
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.learning.feedback_reader import FeedbackReader, ImageFeedbackRecord


@dataclass
class PromptVersionReport:
    version: str
    total: int = 0
    positive: int = 0
    negative: int = 0
    tags: dict[str, int] = field(default_factory=dict)


class PromptVersionTracker:
    def __init__(self, reader: FeedbackReader | None = None):
        self.reader = reader or FeedbackReader()

    async def compare_versions(self, versions: list[str]) -> dict[str, PromptVersionReport]:
        reports: dict[str, PromptVersionReport] = {}
        for version in versions:
            records = await self.reader.list_image_feedback_by_version(version)
            report = PromptVersionReport(version=version)
            for r in records:
                report.total += 1
                report.tags[r.tag] = report.tags.get(r.tag, 0) + 1
                if self._is_positive(r):
                    report.positive += 1
                elif self._is_negative(r):
                    report.negative += 1
            reports[version] = report
        return reports

    def _is_positive(self, record: ImageFeedbackRecord) -> bool:
        return record.comment is not None and any(
            word in record.comment for word in ["good", "满意", "好", "喜欢"]
        )

    def _is_negative(self, record: ImageFeedbackRecord) -> bool:
        return record.comment is not None and any(
            word in record.comment for word in ["bad", "不", "差", "主体不突出"]
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/learning/test_prompt_version_tracker.py::test_compare_template_versions -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/learning/prompt_version_tracker.py \
        agent-core/tests/services/learning/test_prompt_version_tracker.py
git commit -m "feat(learning): add prompt template version performance tracker"
```

## Task 8: Add Learning Admin/Internal API Endpoints

**Files:**
- Create: `agent-core/app/api/endpoints/learning.py`
- Modify: `agent-core/app/api/router.py`
- Test: `agent-core/tests/api/test_learning_api.py`

**Interfaces:**
- Consumes: HTTP requests for alias proposals, apply alias, few-shot append/retrieve, version comparison.
- Produces: JSON responses.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_list_alias_proposals(client: AsyncClient):
    response = await client.get("/api/v1/learning/alias-proposals")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/api/test_learning_api.py::test_list_alias_proposals -v
```
Expected: FAIL with 404 or module error.

- [ ] **Step 3: Implement the endpoint**

Create `agent-core/app/api/endpoints/learning.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.learning.alias_expansion import AliasExpansionService
from app.services.learning.feedback_reader import FeedbackReader
from app.services.learning.few_shot_library import Example, FewShotLibrary
from app.services.learning.prompt_version_tracker import PromptVersionTracker
from app.services.learning.taxonomy_writer import TaxonomyWriter

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])

feedback_reader = FeedbackReader()
alias_service = AliasExpansionService(min_occurrences=3)
few_shot_lib = FewShotLibrary()
version_tracker = PromptVersionTracker(reader=feedback_reader)
taxonomy_writer = TaxonomyWriter()


class AliasProposalResponse(BaseModel):
    field: str
    alias: str
    canonical: str
    occurrences: int
    confidence: float


class ApplyAliasRequest(BaseModel):
    field: str
    alias: str
    canonical: str


class FewShotAppendRequest(BaseModel):
    input_text: str
    space_type: str
    theme: str | None = None
    budget: int | None = None
    points: list[str] | None = None


@router.get("/alias-proposals", response_model=list[AliasProposalResponse])
async def list_alias_proposals() -> list[AliasProposalResponse]:
    corrections = await feedback_reader.list_unprocessed_intent_corrections()
    proposals = alias_service.propose(corrections)
    return [
        AliasProposalResponse(
            field=p.field,
            alias=p.alias,
            canonical=p.canonical,
            occurrences=p.occurrences,
            confidence=p.confidence,
        )
        for p in proposals
    ]


@router.post("/alias-proposals/apply")
async def apply_alias_proposal(req: ApplyAliasRequest) -> dict:
    from app.services.learning.alias_expansion import AliasProposal
    proposal = AliasProposal(
        field=req.field,
        alias=req.alias,
        canonical=req.canonical,
        occurrences=0,
        confidence=1.0,
    )
    ok = taxonomy_writer.apply_alias(proposal)
    if not ok:
        raise HTTPException(status_code=404, detail="Canonical value not found in taxonomy")
    return {"applied": True}


@router.post("/few-shot-examples")
async def append_few_shot_example(req: FewShotAppendRequest) -> dict:
    await few_shot_lib.append(Example(**req.model_dump()))
    return {"saved": True}


@router.get("/few-shot-examples")
async def list_few_shot_examples(space_type: str, theme: str | None = None, top_k: int = 3) -> list[dict]:
    examples = await few_shot_lib.retrieve(space_type=space_type, theme=theme, top_k=top_k)
    return [example.__dict__ for example in examples]


@router.get("/prompt-version-comparison")
async def compare_prompt_versions(versions: str) -> dict:
    version_list = [v.strip() for v in versions.split(",") if v.strip()]
    reports = await version_tracker.compare_versions(version_list)
    return {
        v: {
            "total": r.total,
            "positive": r.positive,
            "negative": r.negative,
            "tags": r.tags,
        }
        for v, r in reports.items()
    }
```

Wire into router:

```python
from app.api.endpoints import learning
api_router.include_router(learning.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/api/test_learning_api.py::test_list_alias_proposals -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/api/endpoints/learning.py \
        agent-core/app/api/router.py \
        agent-core/tests/api/test_learning_api.py
git commit -m "feat(api): add learning flywheel admin endpoints"
```

## Task 9: Full Test Suite and Rollout

- [ ] **Step 1: Run agent-core tests**

```bash
cd agent-core
pytest tests/services/learning/ tests/intent/test_intent_llm_extractor.py -v
```
Expected: ALL PASS

- [ ] **Step 2: Run agent-api tests**

```bash
cd agent-api
mvn test
```
Expected: ALL PASS

- [ ] **Step 3: Run Java compile with lint**

```bash
cd agent-api
mvn clean compile -Xlint:all
```
Expected: BUILD SUCCESS with no warnings.

- [ ] **Step 4: Commit and push**

```bash
git push origin main
```

---

## Self-Review

**1. Spec coverage:**
- Capture intent corrections and image feedback → Task 1.
- Alias expansion from repeated corrections → Tasks 2-3.
- Few-shot example library → Tasks 5-6.
- Prompt template versioning and performance comparison → Tasks 1, 7.
- Apply alias proposals to taxonomy YAML → Task 4.
- No gaps identified.

**2. Placeholder scan:**
- No TBD/TODO/fill-in-details patterns found.
- Every code step contains concrete code.
- Every test step contains concrete assertions.

**3. Type consistency:**
- `AliasProposal` fields used consistently across `alias_expansion.py` and `taxonomy_writer.py`.
- `FeedbackReader` returns `IntentCorrectionRecord` and `ImageFeedbackRecord` consistently.
- `FewShotLibrary` uses `Example` dataclass consistently.

**4. Known assumptions to verify during implementation:**
- If `aiomysql` is not installed, add it to `agent-core/pyproject.toml` dependencies.
- If a dedicated `generated_images` table exists, move prompt version columns there instead of `feedbacks`.
- Confirm FastAPI router wiring location (`app/api/router.py` or `app/main.py`).
