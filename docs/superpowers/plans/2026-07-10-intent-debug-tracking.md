# 意图识别调试追踪实现计划

> **执行须知：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐个实现。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 为意图识别增加可观测性 —— 暴露解析器输入、各字段置信度/来源、以及被丢弃的字段，使收敛问题可从日志、API 和前端三个层面诊断。

**架构概述：** 现有 `IntentTraceRecorder` 已将 llm/rule/merged/validated 输出记录到 JSONL 文件，调试 API 端点也已存在于 `/api/v1/debug/intent-traces/{project_id}`。当前存在五个缺口：（1）`project_id` 未贯穿 parse-text 调用链，导致 trace 无法关联到项目；（2）parse-text 响应丢弃了大部分字段的识别元数据（仅暴露了 space_type 的 source/confidence）；（3）Java 端 `mergeRequirements` 静默丢弃无效字段，无任何日志；（4）无 SSE 事件将识别信息推送到前端；（5）前端无调试展示面板。本计划闭合全部五个缺口。

**技术栈：** Python 3.9+ / FastAPI / Pydantic（agent-core），Java 17 / Spring Boot（agent-api），Vue 3 / Element Plus（agent-web）

## 全局约束

- LLM/VLM 必须使用智谱 API（GLM-4.7-Flash）
- 异步任务必须使用线程池，禁止直接 new Thread()
- 异步上下文中的同步数据库查询必须通过 loop.run_in_executor 使用线程池
- 内部数据库操作使用数字 ID 作为外键；public_id 仅用于外部暴露
- 会话阶段日志：专门的 stage-issue.log 记录每个会话阶段的开始/成功/失败
- 测试禁止调用真实 LLM API —— 使用 stub/mock
- Python 测试：`cd agent-core && python -m pytest <path> -v`（addopts 已排除集成测试）
- Java 测试：`cd agent-api && mvn test -Dtest=<ClassName>#<methodName> -q`

## 文件结构

**Python（agent-core）：**
- `app/api/routers.py` — parse-text 端点：从 payload 中接收 `project_id`，传给 TextParser
- `app/agents/input_parser.py` — `TextParser.parse()`：接收 `project_id`，传给 `service.recognize()`；丰富 `_recognition_meta` 使其包含所有核心字段
- `tests/api/test_debug_endpoints.py` — 新建：测试调试 API 端点（列表 + 按 trace_id 查询）
- `tests/agents/test_input_parser.py` — 扩展：验证 `project_id` 传递和丰富的 `_recognition_meta`

**Java（agent-api）：**
- `src/main/java/com/meichen/orchestrator/service/DialogueService.java` — 向 parse-text 调用传递 `project_id`；新增 `findDiscardedFields` 辅助方法；在 `mergeRequirements` 中记录被丢弃字段；发送识别摘要 SSE 事件
- `src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java` — 扩展：测试 `findDiscardedFields`

**前端（agent-web）：**
- `src/views/ChatView.vue` — 监听 "recognition" SSE 事件；渲染可折叠调试面板
- `src/api/client.js` — 新增 `debugApi`，包含 `listIntentTraces` 和 `getIntentTrace`
- `src/components/chat/RecognitionDebug.vue` — 新建：展示识别详情的可折叠面板

---

### Task 1: 贯穿 project_id 到 parse-text 端点

**文件：**
- 修改: `agent-core/app/api/routers.py:77-81`
- 修改: `agent-core/app/agents/input_parser.py:157-165`
- 测试: `agent-core/tests/api/test_debug_endpoints.py`（新建）
- 测试: `agent-core/tests/agents/test_input_parser.py`（扩展）

**接口：**
- 依赖: `IntentRecognitionService.recognize(text, project_id=...)` 已接受 `project_id` 参数
- 产出: parse-text 端点现在接受 `{"text": "...", "project_id": "..."}`，trace 可关联到项目

- [ ] **Step 1: 编写调试 API 端点的失败测试**

新建 `agent-core/tests/api/test_debug_endpoints.py`：

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_intent_traces_returns_empty_for_unknown_project():
    response = client.get("/api/v1/debug/intent-traces/nonexistent-project")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "nonexistent-project"
    assert data["traces"] == []


def test_get_intent_trace_returns_404_for_unknown_trace():
    response = client.get("/api/v1/debug/intent-traces/some-project/nonexistent-trace-id")
    assert response.status_code == 404
```

- [ ] **Step 2: 运行测试验证通过（端点已存在）**

运行: `cd agent-core && python -m pytest tests/api/test_debug_endpoints.py -v`
预期: PASS（两个测试 —— 端点已存在，只是之前未测试）

- [ ] **Step 3: 编写 project_id 传递的失败测试**

添加到 `agent-core/tests/agents/test_input_parser.py`：

```python
@pytest.mark.asyncio
async def test_parse_text_passes_project_id_to_recognize(monkeypatch):
    """project_id must be threaded through to recognize() so traces are correlatable."""
    captured_project_id = {}

    class StubService:
        async def recognize(self, text, previous_intent=None, project_id=None):
            captured_project_id["value"] = project_id
            from app.services.intent_recognition_result import ValidatedIntent
            return ValidatedIntent(raw_text=text)

    monkeypatch.setattr("app.agents.input_parser.get_intent_service", lambda: StubService())
    parser = TextParser()
    await parser.parse("圣诞节", project_id="proj-abc-123")
    assert captured_project_id["value"] == "proj-abc-123"
```

- [ ] **Step 4: 运行测试验证失败**

运行: `cd agent-core && python -m pytest tests/agents/test_input_parser.py::test_parse_text_passes_project_id_to_recognize -v`
预期: FAIL，报错 `TypeError: parse() got an unexpected keyword argument 'project_id'`

- [ ] **Step 5: 修改 TextParser.parse() 接受 project_id**

在 `agent-core/app/agents/input_parser.py` 中，修改 `TextParser.parse()` 方法签名和函数体：

```python
async def parse(self, text: str, project_id: str | None = None) -> dict[str, Any]:
    from app.core.config import settings

    if getattr(settings, "intent_parser_legacy", False):
        return self._get_fallback_parse(text)

    service = self._intent_service or get_intent_service()
    result = await service.recognize(text, project_id=project_id)
    return self._validated_intent_to_dict(result)
```

- [ ] **Step 6: 修改 parse-text 端点接收并传递 project_id**

在 `agent-core/app/api/routers.py` 中，修改 `parse_text` 函数：

```python
@router.post("/agents/input-parser/parse-text")
async def parse_text(payload: dict):
    text = payload.get("text", "")
    project_id = payload.get("project_id")
    parser = TextParser()
    return await parser.parse(text, project_id=project_id)
```

- [ ] **Step 7: 运行测试验证通过**

运行: `cd agent-core && python -m pytest tests/agents/test_input_parser.py::test_parse_text_passes_project_id_to_recognize -v`
预期: PASS

- [ ] **Step 8: 运行全部调试端点测试**

运行: `cd agent-core && python -m pytest tests/api/test_debug_endpoints.py tests/agents/test_input_parser.py -v`
预期: 全部 PASS

- [ ] **Step 9: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/api/routers.py agent-core/app/agents/input_parser.py agent-core/tests/api/test_debug_endpoints.py agent-core/tests/agents/test_input_parser.py
git commit -m "feat: thread project_id through parse-text for trace correlation"
```

---

### Task 2: 丰富 parse-text 响应中的 _recognition_meta

**文件：**
- 修改: `agent-core/app/agents/input_parser.py:167-192`（`_validated_intent_to_dict` 方法）
- 测试: `agent-core/tests/agents/test_input_parser.py`（扩展）

**接口：**
- 依赖: `ValidatedIntent` 字段中的 `RecognizedField`（source, confidence, raw_text）
- 产出: parse-text 响应的 `._recognition_meta` 现在包含所有核心字段（theme, space_type, budget, budget_level, style）的 source/confidence/raw_text，而非仅 space_type

- [ ] **Step 1: 编写 _recognition_meta 丰富的失败测试**

添加到 `agent-core/tests/agents/test_input_parser.py`：

```python
@pytest.mark.asyncio
async def test_parse_text_returns_enriched_recognition_meta(monkeypatch):
    """_recognition_meta must include source/confidence for all core fields."""
    from app.services.intent_recognition_result import (
        FieldSource,
        RecognizedField,
        ValidatedIntent,
    )

    class StubService:
        async def recognize(self, text, previous_intent=None, project_id=None):
            return ValidatedIntent(
                raw_text=text,
                theme=RecognizedField(name="theme", value="圣诞节", source=FieldSource.LLM, confidence=0.85, raw_text="圣诞节"),
                space_type=RecognizedField(name="space_type", value="购物中心中庭", source=FieldSource.LLM, confidence=1.0, raw_text="购物中心中庭"),
                budget=RecognizedField(name="budget", value=300000, source=FieldSource.VALIDATED, confidence=0.95, raw_text="30万"),
            )

    monkeypatch.setattr("app.agents.input_parser.get_intent_service", lambda: StubService())
    parser = TextParser()
    result = await parser.parse("圣诞节，购物中心中庭，30万")
    meta = result["_recognition_meta"]
    # theme
    assert meta["theme_source"] == "llm"
    assert meta["theme_confidence"] == 0.85
    assert meta["theme_raw_text"] == "圣诞节"
    # space_type
    assert meta["space_type_source"] == "llm"
    assert meta["space_type_confidence"] == 1.0
    # budget
    assert meta["budget_source"] == "validated"
    assert meta["budget_confidence"] == 0.95
    # missing field (style not set)
    assert meta["style_source"] is None
    assert meta["style_confidence"] == 0.0
```

- [ ] **Step 2: 运行测试验证失败**

运行: `cd agent-core && python -m pytest tests/agents/test_input_parser.py::test_parse_text_returns_enriched_recognition_meta -v`
预期: FAIL，报错 `KeyError: 'theme_source'`（当前只有 space_type_source）

- [ ] **Step 3: 丰富 _validated_intent_to_dict**

在 `agent-core/app/agents/input_parser.py` 中，替换 `_validated_intent_to_dict` 内的 `_recognition_meta` 块：

```python
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
        "_recognition_meta": self._build_recognition_meta(result),
    }
    return data

def _build_recognition_meta(self, result) -> dict[str, Any]:
    """Extract source/confidence/raw_text for all core fields for debug observability."""
    meta: dict[str, Any] = {"trace_id": result.trace_id}
    for field_name in ("theme", "space_type", "budget", "budget_level", "style"):
        field = getattr(result, field_name)
        if field is not None:
            source = field.source
            meta[f"{field_name}_source"] = source.value if hasattr(source, "value") else str(source)
            meta[f"{field_name}_confidence"] = field.confidence
            meta[f"{field_name}_raw_text"] = field.raw_text
        else:
            meta[f"{field_name}_source"] = None
            meta[f"{field_name}_confidence"] = 0.0
            meta[f"{field_name}_raw_text"] = ""
    return meta
```

- [ ] **Step 4: 运行测试验证通过**

运行: `cd agent-core && python -m pytest tests/agents/test_input_parser.py::test_parse_text_returns_enriched_recognition_meta -v`
预期: PASS

- [ ] **Step 5: 运行全部 input_parser 测试检查回归**

运行: `cd agent-core && python -m pytest tests/agents/test_input_parser.py -v`
预期: 全部 PASS

- [ ] **Step 6: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/agents/input_parser.py agent-core/tests/agents/test_input_parser.py
git commit -m "feat: enrich _recognition_meta with all core fields' source/confidence"
```

---

### Task 3: Java 端传递 project_id + 记录合并时被丢弃的字段

**文件：**
- 修改: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java`（第 74 行、第 160-213 行）
- 测试: `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`（扩展）

**接口：**
- 依赖: parse-text 端点现在接受 `{"text": "...", "project_id": "..."}`（来自 Task 1）；响应中的 `_recognition_meta`（来自 Task 2）
- 产出: `findDiscardedFields` 辅助方法（包级可见，可测试）；被丢弃无效字段值的结构化日志

- [ ] **Step 1: 编写 findDiscardedFields 的失败测试**

添加到 `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`：

```java
@Test
void findDiscardedFields_identifiesInvalidValues() {
    Map<String, Object> current = new java.util.HashMap<>();
    current.put("theme", "，");
    current.put("space_type", "快闪店");
    current.put("budget", "abc");
    current.put("style", "123");
    Map<String, Object> discarded = dialogueService.findDiscardedFields(current);
    assertThat(discarded).containsKeys("theme", "budget", "style");
    assertThat(discarded).doesNotContainKey("space_type");
    assertThat(discarded.get("theme")).isEqualTo("，");
}

@Test
void findDiscardedFields_emptyWhenAllValid() {
    Map<String, Object> current = Map.of("theme", "圣诞节", "space_type", "快闪店", "budget", 300000);
    Map<String, Object> discarded = dialogueService.findDiscardedFields(current);
    assertThat(discarded).isEmpty();
}
```

- [ ] **Step 2: 运行测试验证失败**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest#findDiscardedFields_identifiesInvalidValues+findDiscardedFields_emptyWhenAllValid -q`
预期: FAIL —— `findDiscardedFields` 方法不存在

- [ ] **Step 3: 新增 findDiscardedFields 方法并在 mergeRequirements 中记录日志**

在 `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java` 中：

新增 `findDiscardedFields` 方法（放在 `isValidValue` 之后、`findMissingCoreFields` 之前）：

```java
Map<String, Object> findDiscardedFields(Map<String, Object> current) {
    Map<String, Object> discarded = new LinkedHashMap<>();
    if (current == null) return discarded;
    for (String key : List.of("theme", "style", "space_type", "budget", "budget_level",
            "target_audience", "timeline", "color_preference", "brand_positioning",
            "design_system_preference", "space_description")) {
        Object value = current.get(key);
        if (value != null && !isValidValue(key, value)) {
            discarded.put(key, value);
        }
    }
    return discarded;
}
```

无需添加 `import java.util.LinkedHashMap;` —— `java.util.*` 已导入。

在 `mergeRequirements` 中，在简单字段合并循环之后（`for (String key : List.of(...))` 块之后、`mergeList` 之前），添加被丢弃字段的日志：

```java
        // Log discarded invalid field values for debug observability
        Map<String, Object> discarded = findDiscardedFields(current);
        if (!discarded.isEmpty()) {
            log.info("discarded invalid field values during merge: {}", discarded);
        }
```

- [ ] **Step 4: 修改 parse-text 调用传递 project_id**

在 `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java` 中，修改 parse-text 调用（约第 74 行）：

```java
            // 1. 文本解析
            pushThinking(projectId, "text_parse", "started");
            Map<String, Object> textParse = postToAgent(
                "/agents/input-parser/parse-text",
                Map.of("text", content, "project_id", projectId)
            );
            log.info("text_parse result: {}", textParse);
            pushThinking(projectId, "text_parse", "completed");
```

- [ ] **Step 5: 运行测试验证通过**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest#findDiscardedFields_identifiesInvalidValues+findDiscardedFields_emptyWhenAllValid -q`
预期: PASS

- [ ] **Step 6: 运行全部 DialogueServiceTest 测试检查回归**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest -q`
预期: 全部 12 个测试 PASS（10 个已有 + 2 个新增）

- [ ] **Step 7: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java
git commit -m "feat: pass project_id to parse-text + log discarded invalid fields in merge"
```

---

### Task 4: 发送意图识别摘要 SSE 事件

**文件：**
- 修改: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java`（在 `processUserMessage` 中，合并 + 缺失字段检查之后）
- 测试: `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`（扩展）

**接口：**
- 依赖: `textParse` 响应中的 `_recognition_meta`（来自 Task 2）；`findDiscardedFields`（来自 Task 3）；`findMissingCoreFields`（已有）
- 产出: SSE 事件 `"recognition"` 推送到前端，包含: `project_id`、`trace_id`、`input_text`、`recognition_meta`、`discarded_fields`、`missing_core_fields`

- [ ] **Step 1: 编写 buildRecognitionSummary 的失败测试**

添加到 `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java`：

```java
@Test
void buildRecognitionSummary_includesAllDebugInfo() {
    Map<String, Object> textParse = new java.util.HashMap<>();
    textParse.put("trace_id", "trace-abc");
    textParse.put("theme", "圣诞节");
    textParse.put("_recognition_meta", Map.of(
        "theme_source", "llm",
        "theme_confidence", 0.85,
        "space_type_source", null,
        "space_type_confidence", 0.0
    ));
    Map<String, Object> discarded = Map.of("budget", "abc");
    java.util.List<String> missing = java.util.List.of("space_type", "budget");

    Map<String, Object> summary = dialogueService.buildRecognitionSummary(
        "proj-123", "用户输入圣诞节", textParse, discarded, missing
    );

    assertThat(summary.get("project_id")).isEqualTo("proj-123");
    assertThat(summary.get("trace_id")).isEqualTo("trace-abc");
    assertThat(summary.get("input_text")).isEqualTo("用户输入圣诞节");
    assertThat(summary.get("discarded_fields")).isEqualTo(discarded);
    assertThat(summary.get("missing_core_fields")).isEqualTo(missing);
    assertThat(summary.get("recognition_meta")).isNotNull();
}

@Test
void buildRecognitionSummary_handlesNullMeta() {
    Map<String, Object> textParse = Map.of("trace_id", "t1");
    Map<String, Object> summary = dialogueService.buildRecognitionSummary(
        "p1", "hello", textParse, Map.of(), java.util.List.of()
    );
    assertThat(summary.get("recognition_meta")).isInstanceOf(Map.class);
    assertThat((Map<?, ?>) summary.get("recognition_meta")).isEmpty();
}
```

- [ ] **Step 2: 运行测试验证失败**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest#buildRecognitionSummary_includesAllDebugInfo+buildRecognitionSummary_handlesNullMeta -q`
预期: FAIL —— `buildRecognitionSummary` 方法不存在

- [ ] **Step 3: 新增 buildRecognitionSummary 方法并发送 SSE 事件**

在 `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java` 中：

新增 `buildRecognitionSummary` 方法（放在 `buildCoreFieldFollowUp` 之后）：

```java
@SuppressWarnings("unchecked")
Map<String, Object> buildRecognitionSummary(
        String projectId,
        String inputText,
        Map<String, Object> textParse,
        Map<String, Object> discardedFields,
        List<String> missingCoreFields) {
    Map<String, Object> summary = new HashMap<>();
    summary.put("project_id", projectId);
    summary.put("trace_id", textParse.getOrDefault("trace_id", ""));
    summary.put("input_text", inputText);
    Object meta = textParse.get("_recognition_meta");
    summary.put("recognition_meta", meta instanceof Map ? meta : new HashMap<>());
    summary.put("discarded_fields", discardedFields);
    summary.put("missing_core_fields", missingCoreFields);
    return summary;
}
```

在 `processUserMessage` 中，在合并和缺失字段检查之后（紧接 `List<String> missingCoreFields = findMissingCoreFields(merged);` 之后、`if (!missingCoreFields.isEmpty())` 分支之前），添加 SSE 事件：

```java
            // 3. 快速规则完整性检查（基于合并后状态，不调 LLM）
            List<String> missingCoreFields = findMissingCoreFields(merged);

            // 发送意图识别调试事件（供前端展示）
            Map<String, Object> discarded = findDiscardedFields(textParse);
            Map<String, Object> recognitionSummary = buildRecognitionSummary(
                projectId, content, textParse, discarded, missingCoreFields);
            sseEmitterService.sendToProject(projectId, "recognition", recognitionSummary);

            if (!missingCoreFields.isEmpty()) {
```

- [ ] **Step 4: 运行测试验证通过**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest#buildRecognitionSummary_includesAllDebugInfo+buildRecognitionSummary_handlesNullMeta -q`
预期: PASS

- [ ] **Step 5: 运行全部 DialogueServiceTest 测试检查回归**

运行: `cd agent-api && mvn test -Dtest=DialogueServiceTest -q`
预期: 全部 14 个测试 PASS（12 个已有 + 2 个新增）

- [ ] **Step 6: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java agent-api/src/test/java/com/meichen/orchestrator/service/DialogueServiceTest.java
git commit -m "feat: send recognition summary SSE event for debug observability"
```

---

### Task 5: 前端意图识别调试展示

**文件：**
- 新建: `agent-web/src/components/chat/RecognitionDebug.vue`
- 修改: `agent-web/src/views/ChatView.vue`（监听 "recognition" SSE 事件，渲染面板）
- 修改: `agent-web/src/api/client.js`（新增 debugApi）

**接口：**
- 依赖: SSE 事件 `"recognition"`（来自 Task 4）；调试 API `/api/v1/debug/intent-traces/{project_id}`（已有）
- 产出: 聊天界面中的可折叠调试面板，展示输入文本、各字段识别来源/置信度、被丢弃字段、缺失字段、trace_id

- [ ] **Step 1: 在 client.js 中添加 debugApi**

在 `agent-web/src/api/client.js` 中，`thinkingApi` 之后添加：

```javascript
export const debugApi = {
  listIntentTraces: (projectId) => request.get(`/debug/intent-traces/${projectId}`),
  getIntentTrace: (projectId, traceId) => request.get(`/debug/intent-traces/${projectId}/${traceId}`),
}
```

- [ ] **Step 2: 创建 RecognitionDebug.vue 组件**

新建 `agent-web/src/components/chat/RecognitionDebug.vue`：

```vue
<template>
  <div class="recognition-debug">
    <div class="debug-header" @click="expanded = !expanded">
      <el-icon class="debug-icon"><View /></el-icon>
      <span class="debug-title">意图识别调试</span>
      <el-icon class="expand-icon" :class="{ expanded }"><ArrowDown /></el-icon>
    </div>
    <div v-show="expanded" class="debug-body">
      <div class="debug-section">
        <p class="section-label">输入文本</p>
        <p class="section-value">{{ summary.input_text }}</p>
      </div>
      <div class="debug-section">
        <p class="section-label">Trace ID</p>
        <p class="section-value mono">{{ summary.trace_id || '—' }}</p>
      </div>
      <div class="debug-section">
        <p class="section-label">识别字段</p>
        <div class="field-grid">
          <div v-for="field in parsedFields" :key="field.name" class="field-item">
            <span class="field-name">{{ field.name }}</span>
            <span class="field-value" :class="{ missing: !field.present }">{{ field.display }}</span>
            <span v-if="field.present" class="field-meta">{{ field.source }} · {{ (field.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
      <div v-if="summary.discarded_fields && Object.keys(summary.discarded_fields).length > 0" class="debug-section warn">
        <p class="section-label">已丢弃字段</p>
        <div v-for="(value, key) in summary.discarded_fields" :key="key" class="discarded-item">
          <span class="field-name">{{ key }}</span>
          <span class="field-value rejected">{{ value }}</span>
        </div>
      </div>
      <div v-if="summary.missing_core_fields && summary.missing_core_fields.length > 0" class="debug-section warn">
        <p class="section-label">缺失核心字段</p>
        <p class="section-value">{{ summary.missing_core_fields.join('、') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { View, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  summary: { type: Object, default: () => ({}) },
})

const expanded = ref(false)

const FIELD_LABELS = {
  theme: '主题',
  space_type: '空间类型',
  budget: '预算',
  budget_level: '预算等级',
  style: '风格',
}

const parsedFields = computed(() => {
  const meta = props.summary.recognition_meta || {}
  return Object.entries(FIELD_LABELS).map(([key, label]) => {
    const source = meta[`${key}_source`]
    const confidence = meta[`${key}_confidence`] || 0
    const rawText = meta[`${key}_raw_text`]
    return {
      name: label,
      present: source != null,
      display: rawText || (source != null ? '已识别' : '未识别'),
      source: source || '—',
      confidence,
    }
  })
})
</script>

<style scoped>
.recognition-debug {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  max-width: 560px;
  margin-bottom: 12px;
}

.debug-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
}

.debug-header:hover {
  background: #e2e8f0;
}

.debug-icon {
  font-size: 13px;
  color: #64748b;
}

.debug-title {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  flex: 1;
}

.expand-icon {
  font-size: 11px;
  color: #94a3b8;
  transition: transform 0.2s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.debug-body {
  padding: 0 12px 10px;
}

.debug-section {
  padding: 6px 0;
  border-bottom: 1px dashed #cbd5e1;
}

.debug-section:last-child {
  border-bottom: none;
}

.debug-section.warn {
  background: #fef3c7;
  margin: 0 -12px;
  padding: 6px 12px;
}

.section-label {
  margin: 0 0 2px;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
}

.section-value {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.section-value.mono {
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
}

.field-grid {
  display: grid;
  gap: 4px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.field-name {
  color: #64748b;
  min-width: 60px;
}

.field-value {
  color: #1e293b;
  flex: 1;
}

.field-value.missing {
  color: #cbd5e1;
}

.field-value.rejected {
  color: #ef4444;
  text-decoration: line-through;
}

.field-meta {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
}

.discarded-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 2px 0;
}
</style>
```

- [ ] **Step 3: 集成到 ChatView.vue**

在 `agent-web/src/views/ChatView.vue` 中：

添加导入（在已有组件导入之后，约第 237 行）：
```javascript
import RecognitionDebug from '../components/chat/RecognitionDebug.vue'
```

添加状态 ref（在 `thinkingLogs` ref 之后，约第 251 行）：
```javascript
const recognitionSummary = ref(null)
```

在 `fetchEventSource` 回调中添加 SSE 事件处理（在 `else if (msg.event === 'thinking')` 块之后，约第 480 行）：
```javascript
        } else if (msg.event === 'recognition') {
          recognitionSummary.value = data
```

在模板中添加组件（在 ThinkingProcess wrapper 之后，约第 135 行）：
```html
            <RecognitionDebug v-if="recognitionSummary" :summary="recognitionSummary" />
```

切换会话时重置 —— 在会话加载/切换函数中（`thinkingLogs.value = []` 所在位置，约第 349 行）：
```javascript
    recognitionSummary.value = null
```

- [ ] **Step 4: 启动开发服务器并在浏览器中验证**

启动三个服务（如未运行）：
```bash
cd /Users/liulei/private-work/design-agent/agent-core && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd /Users/liulei/private-work/design-agent/agent-api && JWT_SECRET=dev-secret-123456 mvn spring-boot:run &
cd /Users/liulei/private-work/design-agent/agent-web && npm run dev &
```

打开 `http://localhost:5173`，登录后创建主题为"圣诞节"的项目并发送消息。验证：
- "意图识别调试"面板出现在思考过程下方
- 展开后显示：输入文本、trace_id、各字段识别来源和置信度
- 如果某字段无效（如只发送"，"），被丢弃字段区域以黄色高亮显示
- 缺失的核心字段被列出

- [ ] **Step 5: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-web/src/components/chat/RecognitionDebug.vue agent-web/src/views/ChatView.vue agent-web/src/api/client.js
git commit -m "feat: add recognition debug panel to chat view"
```

---

## 自审

**1. 规格覆盖：** 目标是"暴露解析器输入、置信度、被丢弃字段，使收敛问题可诊断"。
- 解析器输入：Task 1 贯穿 project_id（使 trace 可关联到项目/输入）；现有 IntentTraceRecorder 已记录 input_text
- 置信度：Task 2 丰富 _recognition_meta 包含所有核心字段的 source/confidence；Task 4 通过 SSE 推送
- 被丢弃字段：Task 3 新增 findDiscardedFields + 在 mergeRequirements 中记录日志；Task 4 通过 SSE 推送
- 日志可诊断：Task 3 记录被丢弃字段；现有 `log.info("text_parse result: {}")` 记录解析输出
- API 可诊断：Task 1 测试调试 API 端点（已存在但之前未测试）
- 前端可诊断：Task 5 新增调试面板

**2. 占位符扫描：** 无 TBD/TODO 占位符。所有步骤包含完整代码。所有测试代码完整。

**3. 类型一致性：**
- `findDiscardedFields(Map<String, Object>)` → 返回 `Map<String, Object>` —— 在 Task 3（日志）和 Task 4（SSE 摘要）中使用
- `buildRecognitionSummary(String, String, Map, Map, List)` → 返回 `Map<String, Object>` —— 在 Task 4（SSE 事件）中使用
- `parse(text, project_id=None)` —— Task 1 中的 Python 签名，Task 3 中 Java 以 `Map.of("text", content, "project_id", projectId)` 调用
- `_recognition_meta` 键名: `{field}_source`、`{field}_confidence`、`{field}_raw_text` —— Task 2 产出，Task 5 前端消费
- SSE 事件名 `"recognition"` —— Task 4 发送，Task 5 监听

未发现类型不一致。

## 执行交接

**计划已完成并保存到 `docs/superpowers/plans/2026-07-10-intent-debug-tracking.md`。两种执行方式：**

**1. Subagent 驱动（推荐）** —— 每个任务派发全新 subagent，任务间审查，快速迭代

**2. 内联执行** —— 在当前会话中使用 executing-plans 执行，批量执行+检查点审查

**选择哪种方式？**
