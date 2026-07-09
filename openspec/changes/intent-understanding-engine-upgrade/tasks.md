## 1. Data Model & Schema Definition

- [ ] 1.1 Define Pydantic `IntentOutput` schema in `agent-core/app/services/intent_schemas.py` covering both closed fields (space_type, style, material, point) and open fields (theme, budget, budget_level, timeline, color, brand, material_restrictions, special_requirements, target_audience, design_system_preference).
- [ ] 1.2 Define `FieldSource` and confidence model (`llm`, `validated`, `default`, `clarification`) in `agent-core/app/services/intent_recognition_result.py`.
- [ ] 1.3 Define clarification result model with `needs_clarification`, `clarification_question`, and `low_confidence_fields`.
- [ ] 1.4 Update taxonomy loader to expose alias maps and canonical sets for validator use.

## 2. LLM Structured-Output Extractor

- [ ] 2.1 Implement `IntentLLMExtractor` in `agent-core/app/services/intent_recognition.py` with a system prompt asking the LLM to return JSON matching `IntentOutput`.
- [ ] 2.2 Build prompt template that includes taxonomy reference but explicitly allows open-set values for theme/budget/color/brand/timeline.
- [ ] 2.3 Add JSON retry logic: on malformed JSON or pydantic validation failure, retry up to 2 times; on persistent failure fall back to rule-based extraction and mark confidence low.
- [ ] 2.4 Wire extractor to existing `llm_client` (`GLM-4.7-Flash`) with stage logging around the LLM call.

## 3. Post-Validation Layer

- [ ] 3.1 Implement `IntentValidator` class that normalizes LLM output per field.
- [ ] 3.2 Implement budget normalization: convert "30万", "300k", "三十万左右" into integer RMB; set `budget_level` based on amount thresholds.
- [ ] 3.3 Implement alias mapping for closed fields (space_type, style, material, point) using taxonomy alias maps; preserve unknown values as-is and lower confidence.
- [ ] 3.4 Implement required-field check (project theme, space type, budget range) and compute per-field confidence/source metadata.
- [ ] 3.5 Implement clarification strategy: when a required field is missing or below configured threshold, mark `needs_clarification=true` and generate a follow-up question via static templates (per missing field).
- [ ] 3.6 Add domain defaults/context inheritance: merge current turn with previous conversation context before validation.

## 4. API & Database Extension for Feedback

- [ ] 4.1 Add Flyway migration `V2026070901__feedback_intent_corrections.sql` to extend `feedbacks` table with `category`, `intent_field`, `original_value`, `corrected_value`, `processed`, `notes` columns.
- [ ] 4.2 Update `agent-api Feedback.java` entity with new correction fields and `createIntentCorrection` factory method.
- [ ] 4.3 Update `FeedbackRepository.java` to query unprocessed intent corrections by category.
- [ ] 4.4 Update `FeedbackService.java` to accept and store intent correction payloads.
- [ ] 4.5 Update `FeedbackController.java` endpoint to accept intent correction feedback and validate required fields.

## 5. Input Parser Integration

- [ ] 5.1 Update `agent-core/app/agents/input_parser.py` `TextParser.parse()` to call the new LLM-first extractor and consume `IntentOutput`.
- [ ] 5.2 Map `IntentOutput` + validator result back to the existing parse-text response shape so downstream agents remain compatible.
- [ ] 5.3 Handle clarification response: when `needs_clarification=true`, return a response that the dialogue layer can turn into a follow-up question without starting design generation.
- [ ] 5.4 Remove or deprecate the legacy `intent_parser_legacy` fallback path once golden tests pass.

## 6. Golden Tests & Regression

- [ ] 6.1 Create `agent-core/tests/test_intent_recognition_golden.py` with at least 15 test cases covering: exact space type, alias point, fuzzy department-store entrance, LLM fallback for uncommon description, theme extraction ("圣诞节"), budget variants ("30万", "二十万到三十万"), material restrictions, context inheritance, low-confidence clarification, unknown space type.
- [ ] 6.2 Add unit tests for `IntentValidator` budget normalization and alias mapping edge cases.
- [ ] 6.3 Add unit tests for feedback correction persistence in `agent-api`.
- [ ] 6.4 Run `pytest agent-core/tests/test_intent_recognition_golden.py` and ensure all tests pass.
- [ ] 6.5 Run `agent-api` test suite (`mvn test`) and ensure no regressions.

## 7. Rollout & Verification

- [ ] 7.1 Start local services and test the parse-text endpoint with "圣诞节" and "30万" inputs; verify theme and budget are correctly extracted.
- [ ] 7.2 Verify clarification flow: input "做个美陈" triggers a space-type clarification question.
- [ ] 7.3 Verify feedback correction endpoint accepts intent correction payloads and stores them in `feedbacks`.
- [ ] 7.4 Commit changes, merge to `master`, and push to origin.
