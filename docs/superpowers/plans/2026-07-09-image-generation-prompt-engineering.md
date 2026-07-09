# Image Generation Prompt Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce structured, space-type-aware prompt templates and user-configurable negative prompts into the image generation pipeline so generated commercial-display images emphasize the main subject and de-emphasize the background.

**Architecture:** Keep templates as YAML files under `agent-core/data/prompt_templates/` and negative prompts under `agent-core/data/negative_prompts/`. Add a Jinja2-based `PromptTemplateRenderer` that consumes a `ValidatedIntent`-like dictionary and produces positive and negative prompt strings. The existing `ImageGenerationService` gains a thin wrapper that uses the renderer when a `prompt_template_version` is configured and falls back to the legacy concatenation path otherwise.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, Jinja2, PyYAML, pytest, pytest-asyncio, Java 17 / Spring Boot 3.2.5, Flyway.

## Global Constraints

- Image generation must use asyncio.gather with semaphore for parallel execution; max_parallel_images defaults to 8.
- Configurable parameters include idea_count (default 3), images_per_point (default 1), max_parallel_images (default 8).
- Each design point must generate 1 image (center perspective) instead of 3.
- Image background must be simple to focus on commercial display installations.
- Image prompts for the same point must only vary camera angle, not content.
- Negative prompts for image generation are user-selectable with default values.
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

- `agent-core/data/prompt_templates/generic_commercial_display.yaml` — default structured template for unknown space types.
- `agent-core/data/prompt_templates/shopping_mall_atrium.yaml` — atrium-specific template emphasizing central area.
- `agent-core/data/negative_prompts/default.yaml` — categorized negative prompt defaults.
- `agent-core/app/services/prompt_template_loader.py` — loads and validates YAML templates into dataclasses.
- `agent-core/app/services/prompt_template_renderer.py` — renders positive and negative prompts from a template + variables.
- `agent-core/app/services/negative_prompt_builder.py` — selects negative prompt fragments by category and user override.
- `agent-core/app/services/image_generation.py` (modify) — integrates renderer and records template version.
- `agent-core/tests/services/test_prompt_template_loader.py` — loader unit tests.
- `agent-core/tests/services/test_prompt_template_renderer.py` — renderer unit tests.
- `agent-core/tests/services/test_negative_prompt_builder.py` — negative prompt unit tests.
- `agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql` — adds `prompt_template_version` and `rendered_prompt` columns to generated image records (if a table exists; otherwise adds to `feedbacks` as JSON).

## Task 1: Define Structured Prompt Template Data Model

**Files:**
- Create: `agent-core/app/services/prompt_template_loader.py`
- Test: `agent-core/tests/services/test_prompt_template_loader.py`

**Interfaces:**
- Consumes: YAML files on disk under `agent-core/data/prompt_templates/`.
- Produces: `PromptTemplate` dataclass with fields `name`, `version`, `space_types`, `subject`, `environment`, `camera_angle`, `lighting`, `style`, `negative_defaults`, `aspect_ratio`, `legacy_fallback`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from app.services.prompt_template_loader import PromptTemplateLoader


def test_load_generic_template():
    loader = PromptTemplateLoader(template_dir=Path("agent-core/data/prompt_templates"))
    template = loader.load("generic_commercial_display")
    assert template.name == "generic_commercial_display"
    assert template.version == "1.0"
    assert "subject" in template.sections
    assert "negative" in template.sections
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_loader.py::test_load_generic_template -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.prompt_template_loader'`

- [ ] **Step 3: Implement the loader and dataclass**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    def __init__(self, template_dir: str | Path = "agent-core/data/prompt_templates"):
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
```

- [ ] **Step 4: Create the generic template YAML**

Create `agent-core/data/prompt_templates/generic_commercial_display.yaml`:

```yaml
name: generic_commercial_display
version: "1.0"
space_types: []
aspect_ratio: "16:9"
sections:
  subject: |
    A high-quality commercial display installation for a {{ space_type }} with {{ theme }} theme,
    budget level {{ budget_level }}, designed to attract shoppers and highlight the brand.
  environment: |
    Clean modern shopping environment, minimal distractions, subtle architectural context.
  camera_angle: |
    Centered eye-level shot, straight-on perspective, symmetrical composition.
  lighting: |
    Soft even professional lighting, no harsh shadows, warm inviting atmosphere.
  style: |
    Photorealistic 3D render, commercial photography style, high detail.
  negative: |
    blurry, low quality, distorted, cluttered background, people, cars, text, watermark, frame, border
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_loader.py::test_load_generic_template -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/services/prompt_template_loader.py \
        agent-core/tests/services/test_prompt_template_loader.py \
        agent-core/data/prompt_templates/generic_commercial_display.yaml
git commit -m "feat(prompt): add structured prompt template loader and generic template"
```

## Task 2: Implement Jinja2 Prompt Template Renderer

**Files:**
- Create: `agent-core/app/services/prompt_template_renderer.py`
- Test: `agent-core/tests/services/test_prompt_template_renderer.py`

**Interfaces:**
- Consumes: `PromptTemplate` from Task 1 and a `RenderContext` dict.
- Produces: `RenderedPrompt` dataclass with `positive`, `negative`, `version`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer


@pytest.mark.asyncio
async def test_render_atrium_emphasizes_center():
    loader = PromptTemplateLoader(template_dir=Path("agent-core/data/prompt_templates"))
    template = loader.load("shopping_mall_atrium")
    renderer = PromptTemplateRenderer()
    result = await renderer.render(template, {
        "theme": "圣诞节",
        "space_type": "购物中心中庭",
        "budget_level": "high",
        "style": "现代简约",
        "negative_prompts": ["cluttered background", "people"],
    })
    assert "central atrium" in result.positive.lower() or "中庭" in result.positive
    assert "background" in result.negative.lower() or "人物" in result.negative or "people" in result.negative
    assert result.version == "shopping_mall_atrium:1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_renderer.py::test_render_atrium_emphasizes_center -v
```
Expected: FAIL with template not found or module not found.

- [ ] **Step 3: Create the atrium template YAML**

Create `agent-core/data/prompt_templates/shopping_mall_atrium.yaml`:

```yaml
name: shopping_mall_atrium
version: "1.0"
space_types:
  - "购物中心中庭"
  - "商场中庭"
aspect_ratio: "16:9"
sections:
  subject: |
    A striking commercial display installation dominating the very center of a shopping mall atrium,
    {{ theme }} theme, {{ budget_level }} budget, designed for maximum visual impact.
    The installation occupies the central foreground and is the single largest and brightest element in the frame.
  environment: |
    Elegant multi-floor shopping mall atrium with glass railings and soft architectural lines visible only at the edges;
    keep the surrounding mall structure blurred and low-detail so the display remains the hero.
  camera_angle: |
    Centered straight-on perspective from the ground floor looking toward the middle of the atrium,
    symmetrical composition, the display perfectly centered in the frame.
  lighting: |
    Bright, even commercial lighting focused on the central display, warm welcoming atmosphere,
    subtle ambient light on the atrium ceiling.
  style: |
    Photorealistic 3D architectural visualization, premium commercial photography, crisp detail on the display,
    clean and modern.
  negative: |
    blurry, low quality, distorted, cluttered background, crowds of people, cars, street view, text, watermark,
    frame, border, busy shoppers, distracting signs, uneven lighting
```

- [ ] **Step 4: Implement the renderer**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_renderer.py::test_render_atrium_emphasizes_center -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/services/prompt_template_renderer.py \
        agent-core/tests/services/test_prompt_template_renderer.py \
        agent-core/data/prompt_templates/shopping_mall_atrium.yaml
git commit -m "feat(prompt): add Jinja2 prompt template renderer and atrium template"
```

## Task 3: Implement Negative Prompt Builder

**Files:**
- Create: `agent-core/app/services/negative_prompt_builder.py`
- Create: `agent-core/data/negative_prompts/default.yaml`
- Test: `agent-core/tests/services/test_negative_prompt_builder.py`

**Interfaces:**
- Consumes: YAML negative prompt categories and user override list.
- Produces: A single comma-separated negative prompt string.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from app.services.negative_prompt_builder import NegativePromptBuilder


def test_default_negative_prompts_applied():
    builder = NegativePromptBuilder(config_dir=Path("agent-core/data/negative_prompts"))
    result = builder.build(space_type="购物中心中庭")
    assert "cluttered background" in result
    assert "people" in result


def test_user_override_replaces_defaults():
    builder = NegativePromptBuilder(config_dir=Path("agent-core/data/negative_prompts"))
    result = builder.build(space_type="购物中心中庭", user_negative=["text", "watermark"])
    assert result == "text, watermark"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/test_negative_prompt_builder.py -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Create default negative prompt config**

Create `agent-core/data/negative_prompts/default.yaml`:

```yaml
categories:
  generic:
    - blurry
    - low quality
    - distorted
    - text
    - watermark
    - frame
    - border
  atrium:
    - cluttered background
    - people
    - cars
    - street view
    - busy shoppers
    - distracting signs
    - uneven lighting
  pop_up_store:
    - cluttered background
    - people
    - cars
    - street view
    - distracting signs

space_type_mapping:
  "购物中心中庭": ["generic", "atrium"]
  "商场中庭": ["generic", "atrium"]
  "快闪店": ["generic", "pop_up_store"]
  "_default": ["generic"]
```

- [ ] **Step 4: Implement the builder**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class NegativePromptBuilder:
    def __init__(self, config_dir: str | Path = "agent-core/data/negative_prompts"):
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd agent-core
pytest tests/services/test_negative_prompt_builder.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/services/negative_prompt_builder.py \
        agent-core/tests/services/test_negative_prompt_builder.py \
        agent-core/data/negative_prompts/default.yaml
git commit -m "feat(prompt): add configurable negative prompt builder"
```

## Task 4: Integrate Renderer into Image Generation Pipeline

**Files:**
- Modify: `agent-core/app/services/image_generation.py`
- Test: `agent-core/tests/services/test_image_generation.py` (create if absent)

**Interfaces:**
- Consumes: `PromptTemplateRenderer`, `NegativePromptBuilder`, `ValidatedIntent`/dict.
- Produces: `ImageGenerationService.generate_from_intent(intent, template_version=None)` returning a filename.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from app.services.image_generation import ImageGenerationService


@pytest.mark.asyncio
async def test_generate_from_intent_uses_template(monkeypatch):
    service = ImageGenerationService()
    called = {}

    async def fake_generate(prompt, aspect_ratio="16:9", style="realistic"):
        called["prompt"] = prompt
        called["aspect_ratio"] = aspect_ratio
        return "fake.png"

    monkeypatch.setattr(service, "generate", fake_generate)

    result = await service.generate_from_intent(
        {
            "theme": "圣诞节",
            "space_type": "购物中心中庭",
            "budget_level": "high",
            "style": "现代简约",
        },
        template_version="shopping_mall_atrium",
    )
    assert result == "fake.png"
    assert "Christmas" in called["prompt"] or "圣诞节" in called["prompt"]
    assert "central" in called["prompt"].lower() or "中庭" in called["prompt"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/services/test_image_generation.py::test_generate_from_intent_uses_template -v
```
Expected: FAIL with `AttributeError: 'ImageGenerationService' object has no attribute 'generate_from_intent'`

- [ ] **Step 3: Modify image_generation.py**

Add imports at the top:

```python
from app.services.negative_prompt_builder import NegativePromptBuilder
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer
```

Add helper method to `ImageGenerationService`:

```python
    def __init__(self):
        self.providers = [
            SiliconFlowProvider(),
            ZhipuProvider(),
            PollinationsProvider(),
            ComfyUIProvider(),
            PlaceholderProvider(),
        ]
        self._template_loader = PromptTemplateLoader()
        self._template_renderer = PromptTemplateRenderer()
        self._negative_builder = NegativePromptBuilder()

    async def generate_from_intent(
        self,
        intent: dict,
        template_version: str | None = None,
        aspect_ratio: str = "16:9",
        style: str = "realistic",
    ) -> dict:
        """Render prompt from intent and generate image. Returns metadata dict."""
        if template_version:
            template = self._template_loader.load(template_version)
            space_type = intent.get("space_type")
            negative = self._negative_builder.build(
                space_type=space_type,
                user_negative=intent.get("negative_prompts"),
            )
            rendered = await self._template_renderer.render(
                template,
                {**intent, "negative_prompts": negative.split(", ") if negative else []},
            )
            prompt = rendered.positive
            final_negative = rendered.negative
        else:
            prompt = self._legacy_prompt(intent)
            final_negative = self._negative_builder.build(
                space_type=intent.get("space_type"),
                user_negative=intent.get("negative_prompts"),
            )
            rendered = None

        filename = await self.generate(prompt, aspect_ratio, style)
        return {
            "filename": filename,
            "prompt": prompt,
            "negative_prompt": final_negative,
            "template_version": rendered.version if rendered else None,
            "aspect_ratio": aspect_ratio,
        }

    def _legacy_prompt(self, intent: dict) -> str:
        parts = [
            f"Commercial display design for {intent.get('space_type', 'commercial space')}",
        ]
        if intent.get("theme"):
            parts.append(f"theme: {intent['theme']}")
        if intent.get("style"):
            parts.append(f"style: {intent['style']}")
        if intent.get("budget_level"):
            parts.append(f"budget level: {intent['budget_level']}")
        return ", ".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/services/test_image_generation.py::test_generate_from_intent_uses_template -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/image_generation.py \
        agent-core/tests/services/test_image_generation.py
git commit -m "feat(prompt): integrate template renderer into image generation service"
```

## Task 5: Add Template Selection by Space Type

**Files:**
- Modify: `agent-core/app/services/prompt_template_loader.py`
- Test: `agent-core/tests/services/test_prompt_template_loader.py`

**Interfaces:**
- Consumes: Space type string.
- Produces: Best matching `PromptTemplate` name.

- [ ] **Step 1: Write the failing test**

```python
def test_select_template_by_space_type():
    loader = PromptTemplateLoader(template_dir=Path("agent-core/data/prompt_templates"))
    name = loader.select_for_space_type("购物中心中庭")
    assert name == "shopping_mall_atrium"


def test_select_fallback_for_unknown_space_type():
    loader = PromptTemplateLoader(template_dir=Path("agent-core/data/prompt_templates"))
    name = loader.select_for_space_type("未知空间")
    assert name == "generic_commercial_display"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_loader.py::test_select_template_by_space_type tests/services/test_prompt_template_loader.py::test_select_fallback_for_unknown_space_type -v
```
Expected: FAIL with `AttributeError: 'PromptTemplateLoader' object has no attribute 'select_for_space_type'`

- [ ] **Step 3: Implement selection method**

Add to `PromptTemplateLoader`:

```python
    def select_for_space_type(self, space_type: str | None) -> str:
        if not space_type:
            return "generic_commercial_display"
        candidates: list[tuple[str, int]] = []
        for stem in self.list_templates():
            try:
                template = self.load(stem)
            except Exception:
                continue
            for candidate_space in template.space_types:
                if candidate_space == space_type:
                    return stem
                if candidate_space in space_type or space_type in candidate_space:
                    candidates.append((stem, len(candidate_space)))
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]
        return "generic_commercial_display"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd agent-core
pytest tests/services/test_prompt_template_loader.py::test_select_template_by_space_type tests/services/test_prompt_template_loader.py::test_select_fallback_for_unknown_space_type -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/prompt_template_loader.py \
        agent-core/tests/services/test_prompt_template_loader.py
git commit -m "feat(prompt): select prompt template by space type with fallback"
```

## Task 6: Add Flyway Migration for Prompt Version Tracking

**Files:**
- Create: `agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql`

**Interfaces:**
- Consumes: Existing `feedbacks` table.
- Produces: Extended `feedbacks` and/or new `generated_images` table columns.

- [ ] **Step 1: Inspect existing schema**

Run:
```bash
cd agent-api
mvn flyway:info -q
```
Expected: shows existing migrations including `V2026070901__feedback_intent_corrections.sql`.

- [ ] **Step 2: Write the migration**

If there is no dedicated `generated_images` table, extend `feedbacks` to store image generation metadata:

```sql
ALTER TABLE feedbacks
    ADD COLUMN prompt_template_version VARCHAR(100) NULL AFTER image_url,
    ADD COLUMN rendered_prompt TEXT NULL AFTER prompt_template_version,
    ADD COLUMN generation_params JSON NULL AFTER rendered_prompt;

CREATE INDEX idx_feedbacks_prompt_version ON feedbacks (prompt_template_version);
```

If a `generated_images` table exists instead, add the columns there.

- [ ] **Step 3: Run migration locally**

Run:
```bash
cd agent-api
mvn flyway:migrate
```
Expected: `BUILD SUCCESS` and new migration applied.

- [ ] **Step 4: Commit**

```bash
git add agent-api/src/main/resources/db/migration/V2026071001__image_prompt_template_version.sql
git commit -m "feat(db): add prompt template version and rendered prompt columns"
```

## Task 7: Expose Template Render Preview Endpoint

**Files:**
- Create: `agent-core/app/api/endpoints/prompt_preview.py`
- Modify: `agent-core/app/api/router.py` (or create if absent)
- Test: `agent-core/tests/api/test_prompt_preview.py`

**Interfaces:**
- Consumes: HTTP POST with `theme`, `space_type`, `budget_level`, `style`, optional `negative_prompts`.
- Produces: JSON with `positive`, `negative`, `template_version`, `aspect_ratio`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_preview_prompt(client: AsyncClient):
    response = await client.post("/api/v1/prompt-preview", json={
        "theme": "圣诞节",
        "space_type": "购物中心中庭",
        "budget_level": "high",
        "style": "现代简约",
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "positive" in data
    assert "negative" in data
    assert "shopping_mall_atrium" in data["template_version"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd agent-core
pytest tests/api/test_prompt_preview.py::test_preview_prompt -v
```
Expected: FAIL with 404 or module error.

- [ ] **Step 3: Implement the endpoint**

Create `agent-core/app/api/endpoints/prompt_preview.py`:

```python
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.negative_prompt_builder import NegativePromptBuilder
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer

router = APIRouter()

loader = PromptTemplateLoader()
renderer = PromptTemplateRenderer()
negative_builder = NegativePromptBuilder()


class PromptPreviewRequest(BaseModel):
    theme: str
    space_type: str
    budget_level: str | None = None
    style: str | None = None
    negative_prompts: list[str] | None = None


class PromptPreviewResponse(BaseModel):
    positive: str
    negative: str
    template_version: str
    aspect_ratio: str


@router.post("/api/v1/prompt-preview", response_model=PromptPreviewResponse)
async def preview_prompt(req: PromptPreviewRequest) -> PromptPreviewResponse:
    template_name = loader.select_for_space_type(req.space_type)
    template = loader.load(template_name)
    negative = negative_builder.build(
        space_type=req.space_type,
        user_negative=req.negative_prompts,
    )
    rendered = await renderer.render(
        template,
        {
            "theme": req.theme,
            "space_type": req.space_type,
            "budget_level": req.budget_level or "medium",
            "style": req.style,
            "negative_prompts": negative.split(", ") if negative else [],
        },
    )
    return PromptPreviewResponse(
        positive=rendered.positive,
        negative=rendered.negative,
        template_version=rendered.version,
        aspect_ratio=rendered.aspect_ratio,
    )
```

- [ ] **Step 4: Wire the router**

Find `agent-core/app/api/router.py` or equivalent and add:

```python
from app.api.endpoints import prompt_preview

api_router.include_router(prompt_preview.router)
```

If no router file exists, locate the FastAPI app factory in `agent-core/app/main.py` and add the router there.

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd agent-core
pytest tests/api/test_prompt_preview.py::test_preview_prompt -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/api/endpoints/prompt_preview.py \
        agent-core/app/api/router.py \
        agent-core/tests/api/test_prompt_preview.py
git commit -m "feat(api): add prompt preview endpoint"
```

## Task 8: Local Visual Verification

**Files:**
- None (manual verification).

- [ ] **Step 1: Start agent-core service**

Run:
```bash
cd agent-core
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Call preview endpoint**

In another terminal:
```bash
curl -s -X POST http://localhost:8000/api/v1/prompt-preview \
  -H "Content-Type: application/json" \
  -d '{"theme":"圣诞节","space_type":"购物中心中庭","budget_level":"high"}' | jq .
```
Expected: JSON with positive prompt containing atrium/center emphasis and negative prompt containing background/people suppression.

- [ ] **Step 3: Verify image generation still works with legacy path**

Run a local workflow that does NOT pass `template_version` and confirm `ImageGenerationService.generate_from_intent` falls back to `_legacy_prompt`.

- [ ] **Step 4: Commit verification notes**

If any prompt tuning is needed, edit the YAML files and commit:

```bash
git add agent-core/data/prompt_templates/shopping_mall_atrium.yaml
git commit -m "chore(prompt): tune atrium template after visual verification"
```

## Task 9: Full Test Suite and Rollout

- [ ] **Step 1: Run agent-core tests**

```bash
cd agent-core
pytest tests/services/test_prompt_template_loader.py \
       tests/services/test_prompt_template_renderer.py \
       tests/services/test_negative_prompt_builder.py \
       tests/services/test_image_generation.py \
       tests/api/test_prompt_preview.py -v
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
- Structured prompt templates → Tasks 1-2.
- Template selection by space type → Task 5.
- User-configurable negative prompts → Tasks 3, 7.
- Backward-compatible legacy mode → Task 4 `_legacy_prompt` path.
- Atrium Christmas scenario emphasis → Task 2 template and Task 8 verification.
- No gaps identified.

**2. Placeholder scan:**
- No TBD/TODO/fill-in-details patterns found.
- Every code step contains concrete code.
- Every test step contains concrete assertions.

**3. Type consistency:**
- `PromptTemplateLoader.load` returns `PromptTemplate` consistently.
- `PromptTemplateRenderer.render` returns `RenderedPrompt` consistently.
- `generate_from_intent` returns `dict` with keys `filename`, `prompt`, `negative_prompt`, `template_version`, `aspect_ratio`.

**4. Known assumptions to verify during implementation:**
- Confirm whether a dedicated `generated_images` table exists; if so, apply migration there instead of `feedbacks`.
- Confirm FastAPI router wiring location (`app/api/router.py` or `app/main.py`).
