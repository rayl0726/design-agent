## Why

The current intent recognition engine is rule-first: it tokenizes input and tries exact/alias/fuzzy matches against a fixed taxonomy. This misses open-ended fields like "圣诞节" (theme) and "30万" (budget) because they are not in any closed vocabulary. As a result, user intent is only partially understood, forcing users to repeat themselves or accept defaults. This change upgrades the engine so an LLM extracts structured intent first, and a lightweight rule layer only normalizes and validates the output.

## What Changes

- Replace the rule-first pipeline in `agent-core/app/services/intent_recognition.py` with an LLM structured-output-first pipeline.
- Introduce a pydantic `IntentOutput` schema covering both closed fields (space_type, style, material, point) and open fields (theme, budget, timeline, color, brand, material_restrictions).
- Add a `Validator` post-processing layer that normalizes budget to integer RMB, maps aliases to canonical taxonomy values, and flags missing required fields.
- Keep taxonomy as an open set: LLM can emit values outside the taxonomy; validation records them as-is when no canonical mapping exists.
- Add confidence scoring per field and a clarification strategy for low-confidence or missing required fields.
- Extend the `feedbacks` table in agent-api to capture intent corrections (field, original value, corrected value, category) so future changes can build a learning loop.
- Add golden regression tests for intent recognition covering exact, fuzzy, LLM-only, and correction scenarios.

## Capabilities

### New Capabilities
- `intent-feedback-capture`: Capture and store user corrections on intent fields so the system can learn from mismatches.

### Modified Capabilities
- `intent-recognition`: Shift from rule-first recognition to LLM structured-output-first recognition with rule-based post-validation; add support for open-ended fields, per-field confidence, and clarification prompts.

## Impact

- `agent-core/app/services/intent_recognition.py` — replaced/rewritten.
- `agent-core/app/agents/input_parser.py` — updated to consume new intent output schema and emit clarification responses.
- `agent-core/data/intent_taxonomy.yaml` — retained as a canonical/reference taxonomy, no longer the primary matching source.
- `agent-api` Feedback entity, repository, service, controller, and Flyway migration — extended with correction fields.
- C端 parse-text API response shape may gain new fields (`needs_clarification`, `clarification_question`, `confidence` per field).
