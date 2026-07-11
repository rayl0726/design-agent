## 1. Prompt Template Data & Configuration

- [x] 1.1 Create `agent-core/data/prompt_templates/` directory and add `generic_commercial_display.yaml` with structured sections (subject, environment, camera, lighting, style, negative).
- [x] 1.2 Add `agent-core/data/prompt_templates/shopping_mall_atrium.yaml` optimized for central-atrium subject prominence and background minimization.
- [x] 1.3 Create `agent-core/data/negative_prompts/default.yaml` with selectable negative prompt categories.

## 2. Prompt Template Renderer

- [x] 2.1 Implement `PromptTemplate` dataclass and `PromptTemplateLoader` in `agent-core/app/services/prompt_template_loader.py`.
- [x] 2.2 Implement `PromptTemplateRenderer` in `agent-core/app/services/prompt_template_renderer.py` using Jinja2 to render templates with theme, space_type, budget, style variables.
- [x] 2.3 Add renderer unit tests in `agent-core/tests/services/test_prompt_template_renderer.py` verifying atrium template emphasizes central area.

## 3. Image Generation Integration

- [x] 3.1 Modify `agent-core/app/services/image_generation.py` to call `PromptTemplateRenderer` when `prompt_template_version` is present.
- [x] 3.2 Preserve legacy prompt concatenation path when no template version is configured.
- [x] 3.3 Add integration test in `agent-core/tests/services/test_image_generation.py` asserting rendered prompt contains expected subject and negative sections.

## 4. Learning Flywheel - Feedback Capture

- [x] 4.1 Extend `agent-api FeedbackService` to accept image feedback with category, tag, point_name, image_index, and prompt_template_version.
- [x] 4.2 Add Flyway migration `V2026071001__image_feedback_prompt_version.sql` to add `prompt_template_version` and `generation_params` columns to feedbacks/images.
- [x] 4.3 Add unit tests for feedback capture in `agent-api`.

## 5. Learning Flywheel - Alias Expansion

- [x] 5.1 Implement `AliasExpansionService` in `agent-core/app/services/learning/alias_expansion.py` that scans unprocessed intent corrections and proposes aliases after threshold occurrences.
- [x] 5.2 Add endpoint or admin utility to review and apply proposed aliases to `intent_taxonomy.yaml`.
- [x] 5.3 Add unit tests for alias proposal logic.

## 6. Learning Flywheel - Few-Shot Library

- [x] 6.1 Create `agent-core/data/few_shot_examples/` directory and JSONL format for intent examples keyed by space_type/theme.
- [x] 6.2 Implement `FewShotLibrary` in `agent-core/app/services/learning/few_shot_library.py` for append and retrieval.
- [x] 6.3 Inject top-k matching examples into `IntentLLMExtractor` prompt context.
- [x] 6.4 Add unit tests for few-shot retrieval.

## 7. Prompt Version Tracking

- [x] 7.1 Update image generation records to store `prompt_template_version` and `rendered_prompt`.
- [x] 7.2 Implement aggregation query/service to compare feedback counts across prompt versions.
- [x] 7.3 Add unit tests for version comparison aggregation.

## 8. Rollout & Verification

- [x] 8.1 Run full `agent-core` and `agent-api` test suites with no regressions.
- [x] 8.2 Start local services and generate sample images for "购物中心中庭 圣诞节" to visually verify subject prominence.
- [x] 8.3 Commit changes, merge to main, and push to origin.
