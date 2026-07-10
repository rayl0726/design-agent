# Intent Recognition Convergence Fix

> Supersedes the root-cause conclusion in [2026-07-10-robust-intent-recognition-design.md](./2026-07-10-robust-intent-recognition-design.md). That doc assumed field loss happened because `parse-text` omitted partial fields, and that "no change needed in `DialogueService`". Live session evidence (project `27a08547`, 2026-07-10 18:14) shows `parse-text` already returns partial fields — the real failure is architectural. This doc corrects that and defines the fix.

## 1. Problem Statement

A real user session (project `27a08547-d2a4-4cdd-acda-32e4d76c49d9`) never converged. The user provided the three required fields across multiple turns, but the assistant kept re-asking for already-provided fields and the project stayed stuck at `status=INIT`.

Observed conversation (condensed):

| Turn | User input | Assistant response |
|------|-----------|-------------------|
| 1 | 圣诞节 | **Error** "处理你的需求时出错了" (88s later) |
| 2 | 圣诞节 | ask space type + budget (theme captured) |
| 3 | 快闪店 | ask budget + **theme** (theme lost from the question) |
| 4 | 30万，主题圣诞节 | ask **space type** (space type lost from the question) |
| 5 | 快闪店 | ask budget + **theme** again |

The project never advances. This is not theme-specific — any multi-turn requirement gathering hits the same loop.

## 2. Root Cause (from `intent_traces` evidence)

The `agent-core/data/intent_traces/2026-07-10.jsonl` traces for this session show four distinct bugs. One is primary.

### Bug 1 (primary — convergence failure): clarification is decided on the current message only

`TextParser.parse()` → `IntentRecognitionService.recognize(text)` computes `clarification.needs_clarification` and `missing_fields` from **only the fields parsed out of the current message**. It never sees `project.requirementJson`, so it has no knowledge of fields captured in prior turns.

Trace evidence — turn 3, input "快闪店":
```json
"clarification": {
  "needs_clarification": true,
  "missing_fields": ["budget", "theme"],
  "clarification_question": "项目预算大概是多少？\n您希望设计的主题或概念是什么？"
}
```
`theme` was captured in turn 2, but because turn 3's message contained no theme, `parse-text` lists `theme` as missing and asks for it again.

`DialogueService` then short-circuits on this `needs_clarification` flag ([DialogueService.java:83, Path A](file:///Users/liulei/private-work/design-agent/agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java#L83)) **before** merging, so the clarification question is generated from the current message alone — every turn. The conversation cannot converge.

### Bug 2: LLM returns null for short inputs; rule extractor mis-parses

All four traces have `llm_output: null` — GLM-4.7-Flash returns null/empty for short inputs like "圣诞节", "快闪店" (a known issue). The rule extractor takes over but mis-parses the multi-field input "30万，主题圣诞节" into `theme="，"` (a lone comma) instead of `theme="圣诞节"`.

### Bug 3: merge overwrites good values with garbage

[`mergeRequirements` (DialogueService.java:190)](file:///Users/liulei/private-work/design-agent/agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java#L190) overwrites an existing field with any non-empty current value. Since `"，"` is non-empty, it overwrites the previously-captured `"圣诞节"`. There is no validity check.

### Bug 4: first-turn error swallowed

Turn 1's "圣诞节" produced "处理你的需求时出错了" after 88s, with no trace recorded. The catch block returns a generic message and does not log the underlying exception, so the root cause is invisible. Likely an unhandled null (LLM null → downstream None dereference) or a timeout.

## 3. Goals

1. **Convergence**: once the user has provided theme + space_type + budget across any number of turns, the system stops asking for them and advances to requirement analysis.
2. **No garbage overwrites**: invalid extracted values (punctuation, too-short strings, non-numeric budget) never overwrite valid accumulated values.
3. **Robust short-input extraction**: bare words like "圣诞节", "快闪店" extract correctly even when the LLM returns null.
4. **Visible failures**: the first-turn error class produces a logged stack trace, not a silent generic message.

## 4. Non-Goals

- Replacing LLM extraction with a fully rule-based parser (LLM stays primary; rules stay fallback).
- Changing the public `parse-text` contract for callers other than `DialogueService`.
- Adding admin UI (separate change).
- Sub-100ms latency optimization.

## 5. Architecture: Approach A — parse-text extracts only, completeness decided post-merge

```
User message
    │
    ▼
parse-text  (pure extraction, NO needs_clarification)
    │  returns: extracted fields + per-field confidence/source
    ▼
DialogueService.mergeRequirements(existing, current)  +  validity check (Bug 3)
    │  writes merged requirement back to project.requirementJson
    ▼
checkCompleteness(merged)   ── fast, rule-based, no LLM
    │  core fields = theme, space_type, budget
    │
    ├─ missing → buildFollowUpQuestion(only truly-missing fields) → next turn
    │
    └─ complete → requirement-analyst (deep analysis + recommendations)
                  → user confirms → workflow proceeds
```

### 5.1 parse-text changes (`agent-core/app/agents/input_parser.py`)

- Remove the `clarification` object (`needs_clarification`, `missing_fields`, `clarification_question`, `message`) from the parse-text response.
- `parse-text` returns only: extracted fields, per-field `_recognition_meta` (source/confidence), and `trace_id`.
- Completeness is no longer a parse-text concern. This keeps parse-text stateless and single-responsibility (extraction).

### 5.2 DialogueService changes (`agent-api/.../service/DialogueService.java`)

- **Delete the Path A short-circuit** (current L83-101): the branch that returns early on `needs_clarification` is removed.
- **Always merge first**: `merged = mergeRequirements(existing, textParse)` runs before any completeness decision.
- **Add `checkCompleteness(merged)`**: a rule-based check that the three core fields (theme, space_type, budget) are present AND valid. This does not call the LLM.
  - Missing → `buildFollowUpQuestion(missingFields)` asking only for the genuinely-missing fields, then return (next turn).
  - Complete → proceed to `requirement-analyst` with the merged requirement.
- `requirement-analyst` is now called only when core fields are complete (deep analysis + recommendations + confirmation), saving an LLM call on every incomplete turn.

### 5.3 Completeness rule

Per project constraint, only three fields are user-required; the rest are auto-filled by recommendations. Therefore:

```
complete = isPresentAndValid(theme)
       AND isPresentAndValid(space_type)
       AND isPresentAndValid(budget)
```

`isPresentAndValid` reuses the same validity predicate used in merge (§6.1).

## 6. Bug-Specific Fixes

### 6.1 Bug 3 — merge validity guard

Add `isValidValue(field, value)` used by both `mergeRequirements` and `checkCompleteness`:

- String fields (theme, space_type, style, ...): after trimming leading/trailing punctuation and whitespace, length ≥ 2; not pure-punctuation; not pure-digit (for theme/space_type).
- `budget`: must parse to a number (int RMB after normalization).
- Lists (points, materials): keep existing merge behavior.

Invalid current values are discarded (do not overwrite existing). Valid current values overwrite. This prevents `theme="，"` from replacing `theme="圣诞节"`.

### 6.2 Bug 2 — rule extractor + domain lexicon

- **Fix theme regex** in the rule extractor so `主题X` / `X主题` patterns capture `X`, not the delimiter. "30万，主题圣诞节" must split into `budget=300000` + `theme=圣诞节`.
- **Domain lexicon fallback**: a lightweight list of common themes (圣诞节, 情人节, 新春, 国潮, 海洋风, ...) and space types (购物中心中庭, 快闪店, 百货入口, ...). When LLM returns null and the rule regex is ambiguous, match against the lexicon. This hardens short-input extraction against the known GLM-4.7-Flash null behavior.
- The existing `intent_traces` recorder (from the earlier design) already captures `llm_output`/`rule_output`/`merged_output`, so these fixes are observable.

### 6.3 Bug 4 — first-turn error visibility

- `IntentRecognitionService`: handle LLM null/empty defensively — return an empty field set rather than throwing. No downstream code should NPE on a null LLM result.
- `DialogueService` catch block: log the full exception (message + stack trace) to `stage-issue.log` with project_id and stage, instead of swallowing it into a generic "处理出错了".
- If static analysis cannot confirm the exact trigger, use the `systematic-debugging` / `TRAE-debugger` skill to reproduce and capture runtime evidence before finalizing.

## 7. Data Flow & State

- **Accumulated state**: `project.requirementJson`. Read at the start of each turn, merged, written back at the end.
- **Per-turn**: `parse-text` output is transient (extracted fields only). It does not carry forward; only the merged `requirementJson` persists.
- **Completeness** is computed on the merged state, never on the parse-text output alone.

## 8. Error Handling

- LLM call fails entirely → rule fallback runs; if rule also empty → ask a generic clarifying question (no crash).
- LLM returns unparseable JSON → log raw output, retry once, then rule fallback.
- Invalid extracted value → discarded by validity guard; existing value retained.
- Any unhandled exception in DialogueService → full stack trace to `stage-issue.log`; user sees a specific retry message, not a silent generic one.

## 9. Testing

1. **Convergence test (agent-api)**: simulate the 5-turn session — "圣诞节" → "快闪店" → "30万，主题圣诞节" → assert no re-asking of captured fields and project advances to analysis after the third turn.
2. **Validity guard unit tests (agent-api)**: `theme="，"` does not overwrite `theme="圣诞节"`; `budget="abc"` discarded; valid values overwrite.
3. **Rule extractor tests (agent-core)**: "30万，主题圣诞节" → `{budget:300000, theme:"圣诞节"}`; bare "圣诞节" → `{theme:"圣诞节"}`; bare "快闪店" → `{space_type:"快闪店"}`.
4. **Completeness check tests**: merged requirement with all three core fields → complete; missing one → that field in missing list only.
5. **LLM-null defensive test**: mock LLM returning null → no exception, rule fallback fills fields.
6. **Error logging test**: forced exception → stack trace present in stage-issue.log.

## 10. Rollout

1. Add `isValidValue` + update `mergeRequirements` (Bug 3) — agent-api.
2. Add `checkCompleteness` + remove Path A short-circuit (Bug 1) — agent-api.
3. Fix theme regex + add domain lexicon (Bug 2) — agent-core.
4. Defensive null handling + error logging (Bug 4) — agent-core + agent-api.
5. Remove `clarification` from parse-text output (Bug 1) — agent-core.
6. Add tests (§9).
7. Restart services; replay the "圣诞节 → 快闪店 → 30万" flow end-to-end; confirm convergence.
8. Commit.
