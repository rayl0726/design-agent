# Robust Intent Recognition with Debug Trace

## 1. Problem Statement

Current behavior: when `parse-text` returns `needs_clarification=true`, the response contains only `missing_fields` and `clarification_question`. The already-extracted fields (e.g. `theme=情人节`) are omitted. `DialogueService` saves this metadata-only payload, so on the next turn the previously parsed fields are lost. This causes the assistant to keep asking for the same information.

This is not a theme-specific problem. Any standalone open-field value (theme, space type, budget) that triggers clarification can be lost across turns.

## 2. Goals

1. **Preserve partial fields**: every `parse-text` call returns the best-effort values it has extracted, even when some required fields are still missing.
2. **Generalize recognition**: theme, space type, and budget extraction should not depend on hard-coded examples. Standalone words like `情人节`, `海洋风`, `快闪店`, `30万` must be recognized.
3. **Add debug trace**: record every intent recognition decision so failures can be diagnosed without reading code.
4. **Keep LLM-first architecture**: LLM structured output remains the primary extractor; rule-based components act as fast fallback and safety net.

## 3. Non-Goals

- Replace LLM extraction with a fully rule-based parser.
- Change the existing dialogue state machine or clarification strategy.
- Add a user-facing admin UI in this change.
- Optimize for sub-100ms latency (current ~1-2s LLM calls dominate).

## 4. Architecture

```
User input
    │
    ▼
┌─────────────────────────────────┐
│  IntentRecognitionService       │
│  (orchestrator)                 │
│                                 │
│  1. LLM extraction              │
│     └─> IntentLLMExtractor      │
│         └─> few-shot examples   │
│                                 │
│  2. Rule fallback               │
│     └─> IntentRuleExtractor     │
│         (theme/space/budget)    │
│                                 │
│  3. Merge & validate            │
│     └─> IntentValidator         │
│                                 │
│  4. Record trace                │
│     └─> IntentTraceRecorder     │
└─────────────────────────────────┘
    │
    ▼
parse-text response (fields + meta + trace_id)
    │
    ▼
DialogueService merges fields into requirement_json
```

### 4.1 LLM Extraction (primary)

- Keep `IntentLLMExtractor` with `IntentOutput` schema.
- System prompt already marks `theme`, `budget`, etc. as open fields; no schema change needed.
- Ensure JSON output is returned even when fields are missing (missing fields → `null`).

### 4.2 Rule Fallback (`IntentRuleExtractor`)

A lightweight, deterministic extractor that runs when LLM extraction returns an empty or incomplete result.

Responsibilities:

| Field | Rule | Example |
|-------|------|---------|
| `theme` | Match standalone festival/season/style nouns and `X主题`/`X概念`/`X风` patterns. | `情人节`, `海洋风`, `国潮主题` |
| `space_type` | Substring match against taxonomy space types; prefer longest match. | `购物中心中庭` > `中庭` |
| `budget` | Extract number + unit (`万`, `k`, `千`, `元`) and normalize to integer RMB. | `30万` → `300000` |
| `points` | Substring match against taxonomy points. | `门头`, `DP点`, `中庭` |

The rule extractor only fills fields that the LLM left empty. It never overwrites LLM output.

### 4.3 Merge Strategy

```
result = llm_output or empty
for each field in rule_output:
    if result[field] is None/empty:
        result[field] = rule_output[field]
```

This keeps LLM intelligence for nuanced input while guaranteeing bare words are captured.

### 4.4 Validation

`IntentValidator` normalizes values (budget to int, space_type alias mapping) and computes confidence. It preserves open-field values as-is unless an alias mapping exists.

### 4.5 Intent Trace Recorder

Every recognition attempt records:

```json
{
  "trace_id": "uuid",
  "project_id": "...",
  "input_text": "情人节",
  "timestamp": "2026-07-10T00:00:00Z",
  "llm_output": { "theme": "情人节", ... },
  "rule_output": { "theme": "情人节" },
  "merged_output": { "theme": "情人节", ... },
  "missing_fields": ["space_type", "budget"],
  "needs_clarification": true,
  "low_confidence_fields": [],
  "errors": []
}
```

Storage: append-only JSONL file under `agent-core/data/intent_traces/YYYY-MM-DD.jsonl`. This avoids DB schema changes and keeps traces local for quick iteration.

## 5. Data Flow Changes

### 5.1 `parse-text` Response

Always include:

- All extracted fields (`theme`, `space_type`, `budget`, etc.) with best-effort values.
- `needs_clarification` boolean.
- `missing_fields` list.
- `clarification_question` string.
- `_recognition_meta` with source per field (`llm`, `rule`, `validator`).
- `trace_id` for debugging.

### 5.2 `DialogueService` Merge

`mergeRequirements(existing, textParse)` already preserves non-null fields. It will now receive actual field values instead of metadata-only payloads, so multi-turn accumulation works correctly.

No change needed in `DialogueService` after the parse-text fix.

## 6. Debug API

Add internal endpoints to `agent-core`:

- `GET /api/v1/debug/intent-traces/{project_id}` — list recent traces for a project.
- `GET /api/v1/debug/intent-traces/{project_id}/{trace_id}` — single trace detail.
- `POST /api/v1/debug/intent-traces/query` — query by input text, missing field, etc.

These endpoints are unauthenticated and intended for local development only.

## 7. Error Handling

- If LLM call fails entirely: log error, use rule fallback alone.
- If LLM returns unparseable JSON: log raw output, retry once, then fallback.
- If rule fallback also fails: return `needs_clarification=true` with empty fields and a generic question.
- All failures are captured in `intent_traces` with `errors` populated.

## 8. Testing

1. **Golden tests** for bare-word themes: `情人节`, `春节`, `海洋风`, `国潮`.
2. **Golden tests** for mixed multi-turn inputs: theme first, space second, budget third.
3. **Unit tests** for `IntentRuleExtractor`.
4. **Unit tests** for merge strategy.
5. **Integration tests** for intent trace recording and debug API.

## 9. Rollout

1. Implement rule fallback and merge logic.
2. Update `parse-text` to always return best-effort fields.
3. Add intent trace recorder and debug API.
4. Add golden/unit tests.
5. Restart `agent-core` and verify with `情人节快闪店30万`.
6. Commit and push.
