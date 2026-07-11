# Intent Recognition Convergence Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the non-converging dialogue where the assistant keeps re-asking for already-provided fields, so a multi-turn requirement gathering (theme → space_type → budget) converges and the project advances.

**Architecture:** Approach A — `parse-text` becomes a pure field extractor (no completeness decision); `DialogueService` merges each turn's extracted fields into accumulated `requirementJson`, then runs a rule-based completeness check on the merged state. Clarification asks only for genuinely-missing fields. Validity guards prevent garbage values (e.g. `"，"`) from overwriting good ones.

**Tech Stack:** Java 17 / Spring Boot 3.2 (agent-api), Python 3.9 / FastAPI (agent-core), pytest, JUnit 5 + Mockito + AssertJ.

## Global Constraints

- LLM/VLM must use 智谱 API only; Embedding uses local Ollama bge-m3.
- Only theme, space_type, budget are user-required; other fields auto-filled by recommendations.
- Async tasks use thread pools (dialogueExecutor already wired).
- Synchronous DB queries in async context use thread pool.
- Public image/data endpoints unauthenticated.
- Java compilation enables -Xlint:all.
- Use TypeReference<Map<String, Object>>() {} for objectMapper.readValue.

---

## File Structure

**agent-core (Python):**
- Modify `app/services/intent_rule_extractor.py` — fix `_extract_theme` so punctuation/too-short tokens aren't returned as theme (Bug 2).
- Modify `app/services/intent_llm_extractor.py` — make few-shot retrieval failure non-fatal so embedding errors don't crash extraction (Bug 4).
- Modify `app/agents/input_parser.py` — remove `clarification` block from `TextParser._validated_intent_to_dict` (Bug 1).
- Test `tests/services/test_intent_rule_extractor.py` — add theme-mis-parse regression test.
- Test `tests/services/test_intent_llm_extractor.py` — add few-shot-failure test (create if absent).

**agent-api (Java):**
- Modify `DialogueService.java` — add `isValidValue`/`findMissingCoreFields`/`buildCoreFieldFollowUp`; update `mergeRequirements`; remove Path A short-circuit; restructure `processUserMessage`; improve error logging.
- Test `DialogueServiceTest.java` (create) — unit tests for merge validity + completeness.

---

### Task 1: Fix rule extractor theme mis-parse (Bug 2)

The rule extractor's `_extract_theme` step 2 uses the token *before* a marker (主题/概念) as the theme candidate. For "30万，主题圣诞节", jieba tokenizes to `["30万","，","主题","圣诞节"]`, so the candidate before "主题" is "，" — a lone comma that passes `_is_known_non_theme` and becomes `theme="，"`.

**Files:**
- Modify: `agent-core/app/services/intent_rule_extractor.py:129-184` (`_extract_theme`) and `:186-225` (`_is_known_non_theme`)
- Test: `agent-core/tests/services/test_intent_rule_extractor.py`

**Interfaces:**
- Produces: `IntentRuleExtractor._extract_theme` correctly returns `None` for punctuation candidates and `"圣诞节"` for "30万，主题圣诞节".

- [ ] **Step 1: Write failing test**

Add to `agent-core/tests/services/test_intent_rule_extractor.py`:

```python
@pytest.mark.asyncio
async def test_extract_theme_multi_field_with_comma():
    """Regression: '30万，主题圣诞节' must yield theme='圣诞节', not '，'."""
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("30万，主题圣诞节")
    assert output.theme == "圣诞节"
    assert output.budget == "30万"


@pytest.mark.asyncio
async def test_extract_theme_marker_after_punctuation():
    """A punctuation token before 主题 must not become the theme."""
    extractor = IntentRuleExtractor(load_taxonomy())
    output = await extractor.extract("预算30万，主题新年")
    assert output.theme == "新年"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && .venv/bin/pytest tests/services/test_intent_rule_extractor.py::test_extract_theme_multi_field_with_comma tests/services/test_intent_rule_extractor.py::test_extract_theme_marker_after_punctuation -v`
Expected: FAIL — `assert '，' == '圣诞节'`

- [ ] **Step 3: Fix `_is_known_non_theme` to reject punctuation**

In `agent-core/app/services/intent_rule_extractor.py`, add a punctuation/length check at the top of `_is_known_non_theme` (after the `def` line, before `if token.isdigit()`):

```python
    def _is_known_non_theme(
        self,
        token: str,
        budget_match: str | None = None,
        allow_style: bool = False,
    ) -> bool:
        # 标点、空白或过短的 token 不应被视为 theme
        stripped = token.strip()
        if len(stripped) < 2:
            return True
        if re.fullmatch(r"[，。,.;；：:！!？?·、\s]+", stripped):
            return True
        # 纯数字或 budget 已匹配到的子串不应被视为 theme
        if token.isdigit():
            return True
```

(Add `import re` at top of file if not already present — it is already imported at line 3.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && .venv/bin/pytest tests/services/test_intent_rule_extractor.py -v`
Expected: PASS — all tests including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/intent_rule_extractor.py agent-core/tests/services/test_intent_rule_extractor.py
git commit -m "fix(intent): reject punctuation/short tokens as theme candidates

'30万，主题圣诞节' was parsed as theme='，' because the token before 主题
was a comma. _is_known_non_theme now rejects tokens shorter than 2 chars
or pure punctuation."
```

---

### Task 2: Make few-shot retrieval failure non-fatal (Bug 4)

`IntentLLMExtractor.extract()` calls `await self._build_prompt(text)` *outside* its try/except. `_build_prompt` calls `_few_shot_prompt_fragment` which calls the few-shot library's `retrieve` (uses embedding API). If embedding throws (e.g. 智谱 429 / Ollama down), the exception propagates unhandled → agent-core 500 → DialogueService swallows into "处理出错了".

**Files:**
- Modify: `agent-core/app/services/intent_llm_extractor.py:66-74` (`_build_prompt`) and `:76-89` (`_few_shot_prompt_fragment`)
- Test: `agent-core/tests/services/test_intent_llm_extractor.py` (create if absent)

**Interfaces:**
- Produces: `IntentLLMExtractor.extract` returns `None` (not raises) when few-shot retrieval throws.

- [ ] **Step 1: Write failing test**

Create `agent-core/tests/services/test_intent_llm_extractor.py` (or append if exists):

```python
import pytest

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.taxonomy_loader import load_taxonomy


class _ThrowingFewShot:
    async def retrieve(self, space_type=None, theme=None, top_k=3):
        raise RuntimeError("embedding API 429")


class _StubLLM:
    async def complete(self, system_prompt, user_prompt, json_mode=False, temperature=0.7):
        return '{"space_type": null, "theme": "圣诞节"}'


@pytest.mark.asyncio
async def test_extract_swallows_few_shot_failure():
    extractor = IntentLLMExtractor(
        taxonomy=load_taxonomy(),
        llm_client=_StubLLM(),
        few_shot_library=_ThrowingFewShot(),
    )
    # Must not raise; few-shot failure is non-fatal
    result = await extractor.extract("圣诞节")
    assert result is not None
    assert result.theme == "圣诞节"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && .venv/bin/pytest tests/services/test_intent_llm_extractor.py::test_extract_swallows_few_shot_failure -v`
Expected: FAIL — `RuntimeError: embedding API 429`

- [ ] **Step 3: Wrap few-shot retrieval in try/except**

In `agent-core/app/services/intent_llm_extractor.py`, change `_few_shot_prompt_fragment` to catch exceptions:

```python
    async def _few_shot_prompt_fragment(self, text: str) -> str:
        if self._few_shot_library is None:
            return ""
        try:
            examples = await self._few_shot_library.retrieve(
                space_type=self._extract_space_type_hint(text),
                theme=self._extract_theme_hint(text),
                top_k=3,
            )
        except Exception as e:
            print(f"FewShotLibrary retrieve failed (non-fatal): {type(e).__name__}: {e}")
            return ""
        if not examples:
            return ""
        rendered = "\n参考示例（输入 -> 输出）：\n" + "\n".join(
            f"- 输入：{e.input_text}\n  输出：{self._example_output(e)}" for e in examples
        )
        return rendered + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && .venv/bin/pytest tests/services/test_intent_llm_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent-core/app/services/intent_llm_extractor.py agent-core/tests/services/test_intent_llm_extractor.py
git commit -m "fix(intent): make few-shot retrieval failure non-fatal

_build_prompt called few-shot retrieve outside try/except, so an embedding
API error crashed extraction and surfaced as '处理出错了'. Now wrapped so
retrieval failures degrade gracefully to no few-shot examples."
```

---

### Task 3: Remove clarification from parse-text output (Bug 1)

`TextParser._validated_intent_to_dict` currently emits `needs_clarification` / `clarification_question` / `missing_fields` / `low_confidence_fields` when the validator sets them. Under Approach A, completeness is decided post-merge in `DialogueService`, so parse-text must stop emitting these.

**Files:**
- Modify: `agent-core/app/agents/input_parser.py:167-197` (`_validated_intent_to_dict`)
- Test: `agent-core/tests/services/test_image_generation.py` is unrelated; add to a new or existing parser test. Check `agent-core/tests/agents/` for existing input_parser tests.

- [ ] **Step 1: Locate or create the parser test file**

Run: `ls agent-core/tests/agents/ 2>/dev/null || echo "no agents test dir"`
If `test_input_parser.py` exists, append; else create `agent-core/tests/agents/test_input_parser.py`:

```python
import pytest

from app.agents.input_parser import TextParser


@pytest.mark.asyncio
async def test_parse_text_omits_clarification_fields():
    """parse-text must not decide completeness; only extract fields."""
    parser = TextParser()
    result = await parser.parse("圣诞节")
    assert "needs_clarification" not in result
    assert "clarification_question" not in result
    assert "missing_fields" not in result
    assert "low_confidence_fields" not in result
    assert result["theme"] == "圣诞节"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && .venv/bin/pytest tests/agents/test_input_parser.py::test_parse_text_omits_clarification_fields -v`
Expected: FAIL — `AssertionError: 'needs_clarification' in result`

- [ ] **Step 3: Remove the clarification block from `_validated_intent_to_dict`**

In `agent-core/app/agents/input_parser.py`, replace the tail of `_validated_intent_to_dict` (lines 192-197):

```python
            "_recognition_meta": {
                "space_type_source": result.space_type.source if result.space_type else None,
                "space_type_confidence": result.space_type.confidence if result.space_type else 0.0,
            },
        }
        return data
```

i.e. delete the `if result.clarification and result.clarification.needs_clarification:` block (old lines 192-197). The method ends after building `data` and returns it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && .venv/bin/pytest tests/agents/test_input_parser.py -v`
Expected: PASS

- [ ] **Step 5: Run full agent-core suite to check no regression**

Run: `cd agent-core && .venv/bin/pytest tests/ -q`
Expected: all pass (some skipped ok).

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/agents/input_parser.py agent-core/tests/agents/test_input_parser.py
git commit -m "refactor(intent): remove clarification from parse-text output

parse-text is now a pure field extractor. Completeness is decided post-merge
in DialogueService so clarification reflects accumulated state, not just the
current message."
```

---

### Task 4: Add validity guard to mergeRequirements (Bug 3)

`mergeRequirements` overwrites an existing field with any non-empty current value. A garbage value like `theme="，"` (non-empty) overwrites a good `theme="圣诞节"`. Add `isValidValue` and use it in the merge loop.

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java:176-229` (`mergeRequirements`) and add `isValidValue`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java` (create)

**Interfaces:**
- Produces: `DialogueService.isValidValue(String field, Object value)` — used by both `mergeRequirements` (this task) and `findMissingCoreFields` (Task 5). Package-private for test access.
- Signature: `boolean isValidValue(String field, Object value)`

- [ ] **Step 1: Write failing test**

Create `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`:

```java
package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class DialogueServiceTest {

    private DialogueService dialogueService;

    @BeforeEach
    void setUp() {
        dialogueService = new DialogueService(
            WebClient.builder(),
            null, null, null, new ObjectMapper(), null, Runnable::run, "http://localhost:8000"
        );
    }

    @Test
    void isValidValue_rejectsPunctuationOnly() {
        assertThat(dialogueService.isValidValue("theme", "，")).isFalse();
        assertThat(dialogueService.isValidValue("theme", ",")).isFalse();
        assertThat(dialogueService.isValidValue("theme", "。")).isFalse();
    }

    @Test
    void isValidValue_rejectsNullAndBlank() {
        assertThat(dialogueService.isValidValue("theme", null)).isFalse();
        assertThat(dialogueService.isValidValue("theme", "")).isFalse();
        assertThat(dialogueService.isValidValue("theme", "   ")).isFalse();
    }

    @Test
    void isValidValue_acceptsMeaningfulString() {
        assertThat(dialogueService.isValidValue("theme", "圣诞节")).isTrue();
        assertThat(dialogueService.isValidValue("space_type", "快闪店")).isTrue();
        assertThat(dialogueService.isValidValue("budget", "30万")).isTrue();
    }

    @Test
    void isValidValue_acceptsNumericBudget() {
        assertThat(dialogueService.isValidValue("budget", 300000)).isTrue();
        assertThat(dialogueService.isValidValue("budget", 0)).isFalse();
    }

    @Test
    void isValidValue_rejectsPureDigitTheme() {
        assertThat(dialogueService.isValidValue("theme", "123")).isFalse();
        assertThat(dialogueService.isValidValue("space_type", "45")).isFalse();
    }

    @Test
    void mergeRequirements_doesNotOverwriteValidWithGarbage() {
        Map<String, Object> existing = Map.of("theme", "圣诞节");
        Map<String, Object> current = Map.of("theme", "，", "budget", 300000);
        Map<String, Object> merged = dialogueService.mergeRequirements(existing, current);
        assertThat(merged.get("theme")).isEqualTo("圣诞节");
        assertThat(merged.get("budget")).isEqualTo(300000);
    }
}
```

Note: `mergeRequirements` and `isValidValue` must be package-private (drop `private` → default access) so the test in the same package can call them.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn -q test -Dtest=DialogueServiceTest`
Expected: FAIL — methods not accessible / `isValidValue` not found.

- [ ] **Step 3: Add `isValidValue` and update `mergeRequirements`**

In `DialogueService.java`:

(a) Add the `isValidValue` method and constants (place near `mergeRequirements`):

```java
    private static final String PUNCT_CHARS = "，。,.;；：:！!？?·、\\s";
    private static final List<String> CORE_FIELDS = List.of("theme", "space_type", "budget");
    private static final Map<String, String> FIELD_QUESTIONS = Map.of(
        "space_type", "请问设计用在什么类型的商业空间？（如购物中心中庭、快闪店、百货入口等）",
        "budget", "项目预算大概是多少？",
        "theme", "您希望设计的主题或概念是什么？"
    );

    boolean isValidValue(String field, Object value) {
        if (value == null) return false;
        if (value instanceof Number n) {
            return n.doubleValue() > 0;
        }
        if (!(value instanceof String s)) return true;
        String trimmed = s.trim().replaceAll("^[" + PUNCT_CHARS + "]+|[" + PUNCT_CHARS + "]+$", "");
        if (trimmed.length() < 2) return false;
        if (trimmed.matches("^[" + PUNCT_CHARS + "]+$")) return false;
        if (("theme".equals(field) || "space_type".equals(field)) && trimmed.matches("^\\d+$")) return false;
        return true;
    }
```

(b) In `mergeRequirements`, change the simple-field overwrite condition (line ~190) from:

```java
            if (value != null && !(value instanceof String s && s.isEmpty())) {
                merged.put(key, value);
            }
```
to:
```java
            if (isValidValue(key, value)) {
                merged.put(key, value);
            }
```

(c) Change `mergeRequirements` and `mergePoints`/`mergeList` visibility from `private` to package-private (remove `private` keyword) only if tests need them — `mergeRequirements` is needed by the test.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-api && mvn -q test -Dtest=DialogueServiceTest`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java
git commit -m "fix(dialogue): add validity guard to mergeRequirements

Garbage values like theme='，' no longer overwrite valid accumulated
values. Adds isValidValue used by merge and completeness check."
```

---

### Task 5: Add post-merge completeness check + restructure processUserMessage (Bug 1)

Remove the Path A short-circuit (lines 78-101) that returned early on parse-text's `needs_clarification`. Instead: always merge first, then run `findMissingCoreFields` on the merged state; ask only for genuinely-missing core fields; if all present, proceed to requirement-analyst.

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java:55-174` (`processUserMessage`)
- Test: `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`

**Interfaces:**
- Produces: `findMissingCoreFields(Map) -> List<String>` and `buildCoreFieldFollowUp(List<String>) -> String` (package-private).

- [ ] **Step 1: Write failing tests for completeness helpers**

Append to `DialogueServiceTest.java`:

```java
    @Test
    void findMissingCoreFields_emptyWhenAllPresent() {
        Map<String, Object> merged = Map.of("theme", "圣诞节", "space_type", "快闪店", "budget", 300000);
        assertThat(dialogueService.findMissingCoreFields(merged)).isEmpty();
    }

    @Test
    void findMissingCoreFields_listsOnlyMissing() {
        Map<String, Object> merged = Map.of("theme", "圣诞节", "space_type", "", "budget", null);
        assertThat(dialogueService.findMissingCoreFields(merged))
            .containsExactlyInAnyOrder("space_type", "budget");
    }

    @Test
    void findMissingCoreFields_rejectsGarbageAsMissing() {
        Map<String, Object> merged = Map.of("theme", "，", "space_type", "快闪店", "budget", 300000);
        assertThat(dialogueService.findMissingCoreFields(merged)).containsExactly("theme");
    }

    @Test
    void buildCoreFieldFollowUp_listsEachMissingField() {
        String followUp = dialogueService.buildCoreFieldFollowUp(java.util.List.of("budget", "theme"));
        assertThat(followUp).contains("项目预算").contains("主题或概念");
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn -q test -Dtest=DialogueServiceTest`
Expected: FAIL — `findMissingCoreFields` / `buildCoreFieldFollowUp` not found.

- [ ] **Step 3: Add the two helper methods**

In `DialogueService.java`, add (near `isValidValue`):

```java
    java.util.List<String> findMissingCoreFields(Map<String, Object> merged) {
        java.util.List<String> missing = new java.util.ArrayList<>();
        for (String f : CORE_FIELDS) {
            if (!isValidValue(f, merged.get(f))) {
                missing.add(f);
            }
        }
        return missing;
    }

    String buildCoreFieldFollowUp(java.util.List<String> missing) {
        StringBuilder sb = new StringBuilder("为了给你生成更精准的设计方案，我还需要确认以下信息：\n\n");
        int i = 1;
        for (String f : missing) {
            sb.append(i).append(". ").append(FIELD_QUESTIONS.getOrDefault(f, "请补充" + f)).append("\n");
            i++;
        }
        sb.append("\n你可以一次性补充所有信息，我会继续分析。");
        return sb.toString();
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-api && mvn -q test -Dtest=DialogueServiceTest`
Expected: PASS — all completeness tests.

- [ ] **Step 5: Restructure `processUserMessage`**

In `DialogueService.java`, replace the body from the `// 1.5 意图不完整时...` block through the `// 5. 检查是否完整` block (current lines 78-138) with the new flow. The new section (replacing lines 78-138) is:

```java
            // 2. 与历史需求合并（含有效性校验，丢弃垃圾值）
            Map<String, Object> existingRequirement = parseJson(project.getRequirementJson());
            Map<String, Object> merged = mergeRequirements(existingRequirement, textParse);
            log.info("merged requirement: {}", merged);
            project.setRequirementJson(toJson(merged));
            projectRepository.save(project);

            // 3. 快速规则完整性检查（基于合并后状态，不调 LLM）
            List<String> missingCoreFields = findMissingCoreFields(merged);
            if (!missingCoreFields.isEmpty()) {
                String followUp = buildCoreFieldFollowUp(missingCoreFields);
                log.info("core fields still missing for project {}: {}", projectId, missingCoreFields);
                SessionMessage msg = sessionMessageService.addAssistantMessage(projectId, "text", followUp, project.getUserId());
                pushMessage(projectId, msg);
                Map<String, Object> initStatus = new HashMap<>();
                initStatus.put("project_id", projectId);
                initStatus.put("status", "INIT");
                initStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
                sseEmitterService.sendToProject(projectId, "status", initStatus);
                return;
            }

            // 4. 核心字段齐全 → 需求分析（深度分析 + 推荐值）
            pushThinking(projectId, "requirement_analyze", "started");
            Map<String, Object> requirement = postToAgent("/agents/requirement-analyst/analyze", merged);
            log.info("requirement_analyze result keys: {}", requirement.keySet());
            pushThinking(projectId, "requirement_analyze", "completed");

            // 5. 合并分析结果到已累积需求（保留核心字段，清理分析元数据）
            Map<String, Object> analyzed = mergeRequirements(merged, requirement);
            project.setRequirementJson(toJson(analyzed));
            projectRepository.save(project);
```

Then KEEP the existing `// 6. 检查是否有推荐值需要确认` block (lines 140-156) and the `// 7. 完整且无推荐确认则启动 L2 工作流` (line 159) unchanged. DELETE the old `// 5. 检查是否完整` block (lines 120-138, the analyst `is_complete`/`missing_fields` follow-up) since core completeness is already guaranteed by step 3 and only core fields are user-required.

Also delete the old `// 2. 与历史需求合并` (lines 103-106) since merge now happens in the new step 2 above. And delete the old `// 4. 保存当前合并后的需求` (lines 116-118) since save happens in step 5.

Net effect: lines 78-138 collapse into the new steps 2-5 above, and the recommendations/workflow blocks remain.

- [ ] **Step 6: Compile and run full agent-api tests**

Run: `cd agent-api && mvn -q test`
Expected: BUILD SUCCESS, all tests pass.

- [ ] **Step 7: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java
git commit -m "fix(dialogue): decide completeness post-merge, not per-message

Removes the parse-text needs_clarification short-circuit. Each turn now
merges into accumulated requirementJson, then a rule-based check asks only
for genuinely-missing core fields. Converges once theme+space_type+budget
are accumulated across turns."
```

---

### Task 6: Improve error logging in DialogueService catch block (Bug 4)

The catch block at line 160-173 logs `e.getMessage()` but the generic "处理出错了" message hides the root cause from the user and the stage log. Log the full stack trace to stage-issue.log and include the exception class.

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java:160-173`

- [ ] **Step 1: Update the catch block**

Replace the catch block (lines 160-173) with:

```java
        } catch (Exception e) {
            log.error("Dialogue processing failed for project {}: {} — {}",
                projectId, e.getClass().getName(), e.getMessage(), e);
            SessionMessage msg = sessionMessageService.addAssistantMessage(
                projectId, "text",
                "抱歉，处理你的需求时出错了（" + e.getClass().getSimpleName() + "），请再试一次或换个说法。",
                project.getUserId());
            pushMessage(projectId, msg);
            sseEmitterService.sendToProject(projectId, "status", Map.of(
                "project_id", projectId,
                "status", "FAILED",
                "current_level", ""
            ));
            Map<String, Object> errorEvent = new HashMap<>();
            errorEvent.put("project_id", projectId);
            errorEvent.put("message", e.getMessage() != null ? e.getMessage() : "处理失败");
            errorEvent.put("exception", e.getClass().getName());
            sseEmitterService.sendToProject(projectId, "error", errorEvent);
        }
```

Key change: the `log.error(..., e)` already passes the throwable for stack trace (it was there), but now the message includes `e.getClass().getName()` and the user-facing text includes `e.getClass().getSimpleName()` so the failure class is visible. The error SSE event also carries the exception type.

- [ ] **Step 2: Compile**

Run: `cd agent-api && mvn -q compile`
Expected: BUILD SUCCESS.

- [ ] **Step 3: Run agent-api tests**

Run: `cd agent-api && mvn -q test`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java
git commit -m "fix(dialogue): surface exception class in error logging

The generic '处理出错了' hid the root cause. Now logs exception class name
and includes it in the user-facing message and error SSE event."
```

---

### Task 7: End-to-end convergence verification

Replay the failing session flow to confirm convergence.

- [ ] **Step 1: Restart services**

Stop agent-core (port 8000) and agent-api (port 8080), then restart:

```bash
# agent-core
cd agent-core && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
# agent-api
cd agent-api && JWT_SECRET=72726cd76143094dce23cd58e66c8af800c541dc43d3386c6ac9e10d6465a97 mvn spring-boot:run -q &
```

- [ ] **Step 2: Verify parse-text no longer emits clarification**

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/input-parser/parse-text \
  -H 'Content-Type: application/json' \
  -d '{"text":"圣诞节"}' | python3 -m json.tool
```
Expected: response has `theme: "圣诞节"` and NO `needs_clarification` / `clarification_question` keys.

- [ ] **Step 3: Verify rule extractor fix**

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/input-parser/parse-text \
  -H 'Content-Type: application/json' \
  -d '{"text":"30万，主题圣诞节"}' | python3 -m json.tool
```
Expected: `theme: "圣诞节"`, `budget: 300000` — NOT `theme: "，"`.

- [ ] **Step 4: Replay the multi-turn flow via the web UI**

Open http://localhost:5173, start a new project, and send in sequence:
1. "圣诞节" → assistant should ask for space_type + budget only
2. "快闪店" → assistant should ask for budget ONLY (theme already captured, not re-asked)
3. "30万" → all three core fields present → assistant proceeds to recommendation confirmation (not re-asking)

Expected: after turn 3, the project advances to RECOMMENDATION_PENDING or workflow, status no longer stuck at INIT.

- [ ] **Step 5: Inspect the intent trace and agent-api log**

```bash
# Confirm theme persisted across turns in requirementJson
mysql -h127.0.0.1 -umeichen -pmeichen123 meichen -e "SELECT requirement_json FROM java_projects WHERE public_id='<new-project-public-id>' \G"
```
Expected: requirement_json contains theme=圣诞节, space_type=快闪店, budget=300000 together.

```bash
grep "core fields still missing\|merged requirement" agent-api/logs/agent-api.log | tail -20
```
Expected: missing fields shrink each turn; none missing after turn 3.

- [ ] **Step 6: Final commit (if any verification artifacts need saving)**

If no code changes needed from verification, skip. Otherwise commit fixes.

---

## Self-Review

**Spec coverage:**
- Bug 1 (convergence) → Task 3 (remove parse-text clarification) + Task 5 (post-merge completeness). ✓
- Bug 2 (rule mis-parse) → Task 1 (punctuation rejection). ✓
- Bug 3 (garbage overwrite) → Task 4 (isValidValue). ✓
- Bug 4 (first-turn error) → Task 2 (few-shot non-fatal) + Task 6 (error logging). ✓
- Testing (spec §9) → Tasks 1-6 include unit tests; Task 7 covers convergence E2E. ✓

**Placeholder scan:** No TBD/TODO. All code blocks complete. ✓

**Type consistency:** `isValidValue(String, Object)` signature consistent across Task 4 (defined) and Task 5 (used in `findMissingCoreFields`). `findMissingCoreFields(Map) -> List<String>` and `buildCoreFieldFollowUp(List<String>) -> String` consistent between Task 5 test and implementation. `CORE_FIELDS` and `FIELD_QUESTIONS` defined in Task 4, used in Task 5. ✓
