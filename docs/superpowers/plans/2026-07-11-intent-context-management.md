# 意图识别上下文管理优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 LLM 调用前传递三层上下文（结构化状态 + 滑动窗口 + 历史摘要），解决多轮对话中意图识别上下文丢失问题。

**Architecture:** Java 层（DialogueService）在调用 Python 端 parse-text API 前，从 `project.requirementJson` 提取已识别的结构化字段（previous_intent），从 `SessionMessageService` 检索最近 3 条用户消息（recent_messages），从 `raw_inputs` 生成历史摘要（conversation_summary）。Python 端在 LLM prompt 中加入 3 个上下文区块，并启用已有的 `merge_context` 机制。

**Tech Stack:** Java 17 / Spring Boot 3.2.5（agent-api），Python 3.11 / FastAPI / Pydantic（agent-core），智谱 GLM-4.7-Flash

## Global Constraints

- LLM/VLM 必须使用智谱 API，不允许 Ollama 本地模型回退
- LLM/VLM API 失败必须抛异常并记录详细错误信息
- 意图识别使用 LLM 结构化输出 + 规则后校验
- 异步任务必须使用线程池（dialogueExecutor）而非直接 new Thread()
- 同步数据库查询在异步上下文中必须通过 loop.run_in_executor 使用线程池
- 知识检索操作必须有超时保护
- 日志需记录阶段信息（stage name, duration, success/failure）
- previous_intent 从 requirementJson 提取时排除 raw_inputs、_recognition_meta、trace_id 等内部字段
- recent_messages 最多 3 条，每条截断到 200 字符
- conversation_summary 当 raw_inputs 数量 ≤ 3 时为空字符串
- conversation_summary 上限 50 行
- 任何上下文获取失败都不阻断主流程，降级为当前行为

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `agent-core/tests/services/test_intent_context.py` | Python 端上下文传递单元测试 |
| `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueContextTest.java` | Java 端上下文提取单元测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `agent-core/app/agents/input_parser.py` L157-165 | TextParser.parse 接收新参数；新增 `_dict_to_validated_intent` |
| `agent-core/app/api/routers.py` L77-82 | parse_text 端点接收 3 个新字段并透传 |
| `agent-core/app/services/intent_recognition.py` L67-95 | recognize 接收 recent_messages + summary，传给 extractor |
| `agent-core/app/services/intent_llm_extractor.py` L66-74, L152-168 | extract 和 _build_prompt 接收上下文；新增 3 个 prompt 片段方法 |
| `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java` L72-77 | 新增上下文提取逻辑，修改 postToAgent 请求体 |

### 不修改的文件

| 文件 | 原因 |
|------|------|
| `agent-core/app/services/intent_validator.py` L335-367 | `merge_context` 已实现，previous_intent 传入即生效 |

---

## Task 1: Python 端 — `_dict_to_validated_intent` 转换方法

**Files:**
- Modify: `agent-core/app/agents/input_parser.py:157-189`
- Test: `agent-core/tests/services/test_intent_context.py`

**Interfaces:**
- Produces: `TextParser._dict_to_validated_intent(self, data: dict | None) -> ValidatedIntent | None` — 将 Java 传来的简单 dict（如 `{"theme": "新春国潮"}`）转换为 `ValidatedIntent` 对象（含 `RecognizedField`）

- [ ] **Step 1: 写失败测试**

创建 `agent-core/tests/services/test_intent_context.py`：

```python
from __future__ import annotations

import pytest

from app.agents.input_parser import TextParser
from app.services.intent_recognition_result import ValidatedIntent, FieldSource


class TestDictToValidatedIntent:
    def test_none_returns_none(self):
        parser = TextParser()
        assert parser._dict_to_validated_intent(None) is None

    def test_empty_dict_returns_none(self):
        parser = TextParser()
        assert parser._dict_to_validated_intent({}) is None

    def test_simple_fields_converted(self):
        parser = TextParser()
        data = {
            "theme": "新春国潮",
            "style": "国潮",
            "space_type": "购物中心中庭",
            "budget": 1000000,
            "budget_level": "medium",
            "timeline": "2-3周",
            "color_preference": "",
            "brand_positioning": "",
        }
        result = parser._dict_to_validated_intent(data)
        assert result is not None
        assert isinstance(result, ValidatedIntent)
        assert result.theme is not None
        assert result.theme.value == "新春国潮"
        assert result.theme.source == FieldSource.UNKNOWN
        assert result.theme.confidence == 1.0
        assert result.style.value == "国潮"
        assert result.space_type.value == "购物中心中庭"
        assert result.budget.value == 1000000
        assert result.budget_level.value == "medium"
        assert result.timeline.value == "2-3周"
        # 空字符串字段应为 None
        assert result.color_preference is None
        assert result.brand_positioning is None

    def test_list_fields_converted(self):
        parser = TextParser()
        data = {
            "material_restrictions": ["真植物"],
            "allowed_materials": ["亚克力", "LED灯带"],
            "special_requirements": ["需要灯光效果"],
        }
        result = parser._dict_to_validated_intent(data)
        assert result is not None
        assert len(result.material_restrictions) == 1
        assert result.material_restrictions[0].value == "真植物"
        assert len(result.allowed_materials) == 2
        assert result.allowed_materials[0].value == "亚克力"
        assert len(result.special_requirements) == 1
        assert result.special_requirements[0].value == "需要灯光效果"

    def test_points_converted(self):
        parser = TextParser()
        data = {
            "points": [{"name": "中庭", "count": 1, "notes": ""}],
        }
        result = parser._dict_to_validated_intent(data)
        assert result is not None
        assert len(result.points) == 1
        assert result.points[0].value == "中庭"

    def test_empty_list_fields(self):
        parser = TextParser()
        data = {
            "material_restrictions": [],
            "allowed_materials": [],
            "special_requirements": [],
            "points": [],
        }
        result = parser._dict_to_validated_intent(data)
        assert result is not None
        assert len(result.material_restrictions) == 0
        assert len(result.allowed_materials) == 0
        assert len(result.special_requirements) == 0
        assert len(result.points) == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestDictToValidatedIntent -v`
Expected: FAIL with "AttributeError: 'TextParser' object has no attribute '_dict_to_validated_intent'"

- [ ] **Step 3: 实现 `_dict_to_validated_intent` 方法**

在 `agent-core/app/agents/input_parser.py` 的 `TextParser` 类中，在 `_validated_intent_to_dict` 方法之后（L189 后）新增：

```python
    def _dict_to_validated_intent(self, data: dict | None) -> ValidatedIntent | None:
        """将 Java 传来的简单 dict 转换为 ValidatedIntent 对象。"""
        if not data:
            return None

        from app.services.intent_recognition_result import (
            ValidatedIntent,
            RecognizedField,
            FieldSource,
        )

        def _field(name: str, value) -> RecognizedField | None:
            if value is None:
                return None
            if isinstance(value, str) and not value.strip():
                return None
            return RecognizedField(
                name=name,
                value=value,
                source=FieldSource.UNKNOWN,
                confidence=1.0,
            )

        def _list_fields(name: str, values) -> list[RecognizedField]:
            if not values or not isinstance(values, list):
                return []
            return [
                RecognizedField(name=name, value=v, source=FieldSource.UNKNOWN, confidence=1.0)
                for v in values
                if v is not None and (not isinstance(v, str) or v.strip())
            ]

        def _point_fields(points_data) -> list[RecognizedField]:
            if not points_data or not isinstance(points_data, list):
                return []
            result = []
            for p in points_data:
                if isinstance(p, dict):
                    name = p.get("name", "")
                    if name and name.strip():
                        result.append(
                            RecognizedField(
                                name="points",
                                value=name.strip(),
                                source=FieldSource.UNKNOWN,
                                confidence=1.0,
                            )
                        )
                elif isinstance(p, str) and p.strip():
                    result.append(
                        RecognizedField(
                            name="points",
                            value=p.strip(),
                            source=FieldSource.UNKNOWN,
                            confidence=1.0,
                        )
                    )
            return result

        intent = ValidatedIntent(
            theme=_field("theme", data.get("theme")),
            style=_field("style", data.get("style")),
            space_type=_field("space_type", data.get("space_type")),
            budget=_field("budget", data.get("budget")),
            budget_level=_field("budget_level", data.get("budget_level")),
            target_audience=_field("target_audience", data.get("target_audience")),
            timeline=_field("timeline", data.get("timeline")),
            color_preference=_field("color_preference", data.get("color_preference")),
            brand_positioning=_field("brand_positioning", data.get("brand_positioning")),
            design_system_preference=_field(
                "design_system_preference", data.get("design_system_preference")
            ),
            material_restrictions=_list_fields(
                "material_restrictions", data.get("material_restrictions")
            ),
            allowed_materials=_list_fields(
                "allowed_materials", data.get("allowed_materials")
            ),
            special_requirements=_list_fields(
                "special_requirements", data.get("special_requirements")
            ),
            points=_point_fields(data.get("points")),
        )

        # 检查是否有任何非空字段
        has_value = any(
            getattr(intent, f) is not None
            for f in (
                "theme", "style", "space_type", "budget", "budget_level",
                "target_audience", "timeline", "color_preference",
                "brand_positioning", "design_system_preference",
            )
        ) or any(
            getattr(intent, f)
            for f in (
                "material_restrictions", "allowed_materials",
                "special_requirements", "points",
            )
        )

        return intent if has_value else None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestDictToValidatedIntent -v`
Expected: PASS (6 tests)

- [ ] **Step 5: 运行已有测试确认无回归**

Run: `cd agent-core && python -m pytest tests/agents/test_input_parser.py tests/services/test_intent_recognition.py -v`
Expected: PASS (所有已有测试)

- [ ] **Step 6: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/agents/input_parser.py agent-core/tests/services/test_intent_context.py
git commit -m "feat: add _dict_to_validated_intent converter for context passing"
```

---

## Task 2: Python 端 — LLM Prompt 上下文区块

**Files:**
- Modify: `agent-core/app/services/intent_llm_extractor.py:66-74, 152-168`
- Test: `agent-core/tests/services/test_intent_context.py`（追加测试类）

**Interfaces:**
- Consumes: `ValidatedIntent` from `intent_recognition_result.py`
- Produces: `IntentLLMExtractor.extract(text, previous_intent=None, recent_messages=None, conversation_summary="")` — 支持上下文的 extract 方法
- Produces: `IntentLLMExtractor._build_prompt(text, previous_intent=None, recent_messages=None, conversation_summary="")` — 支持上下文的 prompt 构建

- [ ] **Step 1: 写失败测试**

在 `agent-core/tests/services/test_intent_context.py` 中追加：

```python
from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.intent_recognition_result import (
    ValidatedIntent,
    RecognizedField,
    FieldSource,
)
from app.services.taxonomy_loader import load_taxonomy


class _StubLLM:
    """记录收到的 prompt，返回空输出。"""
    def __init__(self):
        self.last_prompt = ""

    async def complete(self, system_prompt, user_prompt, json_mode=False, temperature=0.7):
        self.last_prompt = user_prompt
        return '{"space_type": null, "theme": null}'


class TestBuildPromptWithContext:
    @pytest.mark.asyncio
    async def test_prompt_without_context_has_no_context_sections(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        await extractor.extract("购物中心中庭")
        prompt = extractor._llm_client.last_prompt
        assert "之前已识别的需求" not in prompt
        assert "最近的对话" not in prompt
        assert "对话历史摘要" not in prompt

    @pytest.mark.asyncio
    async def test_prompt_with_previous_intent_has_context_section(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        previous = ValidatedIntent(
            theme=RecognizedField(name="theme", value="新春国潮", source=FieldSource.LLM, confidence=0.85),
            style=RecognizedField(name="style", value="国潮", source=FieldSource.LLM, confidence=1.0),
        )
        await extractor.extract("购物中心中庭", previous_intent=previous)
        prompt = extractor._llm_client.last_prompt
        assert "之前已识别的需求" in prompt
        assert "新春国潮" in prompt
        assert "国潮" in prompt

    @pytest.mark.asyncio
    async def test_prompt_with_recent_messages_has_dialogue_section(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        await extractor.extract(
            "预算100万",
            recent_messages=["新春国潮国潮风格", "预算加到100万"],
        )
        prompt = extractor._llm_client.last_prompt
        assert "最近的对话" in prompt
        assert "新春国潮国潮风格" in prompt
        assert "预算加到100万" in prompt

    @pytest.mark.asyncio
    async def test_prompt_with_summary_has_history_section(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        summary = "第1轮：主题=新春国潮，风格=国潮\n第2轮：空间类型=购物中心中庭"
        await extractor.extract("预算100万", conversation_summary=summary)
        prompt = extractor._llm_client.last_prompt
        assert "对话历史摘要" in prompt
        assert "主题=新春国潮" in prompt

    @pytest.mark.asyncio
    async def test_prompt_with_empty_previous_intent_no_section(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        previous = ValidatedIntent()  # 所有字段为 None/空
        await extractor.extract("购物中心中庭", previous_intent=previous)
        prompt = extractor._llm_client.last_prompt
        assert "之前已识别的需求" not in prompt

    @pytest.mark.asyncio
    async def test_recent_messages_truncated_to_200_chars(self):
        extractor = IntentLLMExtractor(
            taxonomy=load_taxonomy(),
            llm_client=_StubLLM(),
        )
        long_msg = "A" * 300
        await extractor.extract("测试", recent_messages=[long_msg])
        prompt = extractor._llm_client.last_prompt
        # 消息被截断到 200 字符
        assert "A" * 200 in prompt
        assert "A" * 201 not in prompt
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestBuildPromptWithContext -v`
Expected: FAIL with "TypeError: extract() got an unexpected keyword argument 'previous_intent'"

- [ ] **Step 3: 修改 `extract` 和 `_build_prompt` 方法签名**

在 `agent-core/app/services/intent_llm_extractor.py` 中：

**修改 `extract` 方法**（L152-168）：

```python
    async def extract(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
        recent_messages: list[str] | None = None,
        conversation_summary: str = "",
    ) -> IntentOutput | None:
        prompt = await self._build_prompt(
            text,
            previous_intent=previous_intent,
            recent_messages=recent_messages,
            conversation_summary=conversation_summary,
        )
        for attempt in range(self._max_retries + 1):
            try:
                raw = await self._llm_client.complete(
                    system_prompt=_INTENT_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    json_mode=True,
                    temperature=0.3,
                )
                parsed = self._parse_llm_output(raw)
                if parsed is not None:
                    return parsed
            except Exception as e:
                print(f"IntentLLMExtractor attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                if attempt == self._max_retries:
                    break
        return None
```

**修改 `_build_prompt` 方法**（L66-74）：

```python
    async def _build_prompt(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
        recent_messages: list[str] | None = None,
        conversation_summary: str = "",
    ) -> str:
        schema_json = IntentOutput.model_json_schema()
        parts: list[str] = [f"用户输入：\"{text}\"\n"]

        context_fragment = self._context_prompt_fragment(
            previous_intent, recent_messages, conversation_summary
        )
        if context_fragment:
            parts.append(context_fragment)

        parts.append("\n请提取设计需求并输出符合以下 JSON Schema 的对象：\n")
        parts.append(f"{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n")
        parts.append(self._taxonomy_prompt_fragment())
        parts.append(await self._few_shot_prompt_fragment(text))
        return "".join(parts)
```

**新增 `_context_prompt_fragment` 方法**（在 `_build_prompt` 之后）：

```python
    def _context_prompt_fragment(
        self,
        previous_intent: ValidatedIntent | None,
        recent_messages: list[str] | None,
        conversation_summary: str,
    ) -> str:
        """构建上下文 prompt 片段，包含已识别需求、最近对话和历史摘要。"""
        sections: list[str] = []

        # 第 1 层：之前已识别的需求
        prev_lines = self._previous_intent_lines(previous_intent)
        if prev_lines:
            sections.append("── 之前已识别的需求 ──\n" + "\n".join(prev_lines) + "\n")

        # 第 2 层：最近的对话
        if recent_messages:
            msg_lines = []
            for msg in recent_messages:
                truncated = msg[:200] if len(msg) > 200 else msg
                msg_lines.append(f'用户："{truncated}"')
            sections.append("── 最近的对话 ──\n" + "\n".join(msg_lines) + "\n")

        # 第 3 层：对话历史摘要
        if conversation_summary and conversation_summary.strip():
            summary = conversation_summary.strip()
            if len(summary) > 2500:
                lines = summary.split("\n")
                summary = "\n".join(lines[:50])
            sections.append("── 对话历史摘要 ──\n" + summary + "\n")

        return "\n".join(sections)

    def _previous_intent_lines(self, previous_intent: ValidatedIntent | None) -> list[str]:
        """从 ValidatedIntent 提取非空字段，返回简洁的 key-value 行。"""
        if previous_intent is None:
            return []

        labels = {
            "theme": "主题",
            "style": "风格",
            "space_type": "空间类型",
            "budget": "预算",
            "budget_level": "预算等级",
            "target_audience": "目标受众",
            "timeline": "时间线",
            "color_preference": "颜色偏好",
            "brand_positioning": "品牌定位",
            "design_system_preference": "设计系统偏好",
        }

        lines: list[str] = []
        for field_name, label in labels.items():
            field = getattr(previous_intent, field_name, None)
            if field is not None and field.value is not None:
                lines.append(f"- {label}：{field.value}")

        for field_name, label in {
            "material_restrictions": "材料限制",
            "allowed_materials": "允许材料",
            "special_requirements": "特殊要求",
        }.items():
            items = getattr(previous_intent, field_name, [])
            if items:
                values = ", ".join(str(item.value) for item in items)
                lines.append(f"- {label}：{values}")

        points = getattr(previous_intent, "points", [])
        if points:
            point_values = ", ".join(str(p.value) for p in points)
            lines.append(f"- 点位：{point_values}")

        return lines
```

**新增 import**（在文件顶部已有的 import 区域追加）：

```python
from app.services.intent_recognition_result import ValidatedIntent
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestBuildPromptWithContext -v`
Expected: PASS (6 tests)

- [ ] **Step 5: 运行已有测试确认无回归**

Run: `cd agent-core && python -m pytest tests/services/test_intent_llm_extractor.py tests/intent/test_intent_llm_extractor.py -v`
Expected: PASS (所有已有测试)

- [ ] **Step 6: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/services/intent_llm_extractor.py agent-core/tests/services/test_intent_context.py
git commit -m "feat: add context sections to LLM prompt (previous_intent, recent_messages, summary)"
```

---

## Task 3: Python 端 — `recognize` 方法传递上下文

**Files:**
- Modify: `agent-core/app/services/intent_recognition.py:67-95`
- Test: `agent-core/tests/services/test_intent_context.py`（追加测试类）

**Interfaces:**
- Consumes: `IntentLLMExtractor.extract(text, previous_intent, recent_messages, conversation_summary)` from Task 2
- Produces: `IntentRecognitionService.recognize(text, previous_intent=None, project_id=None, recent_messages=None, conversation_summary="")` — 支持上下文的 recognize 方法

- [ ] **Step 1: 写失败测试**

在 `agent-core/tests/services/test_intent_context.py` 中追加：

```python
from app.services.intent_recognition import IntentRecognitionService


class _ContextCapturingLLM:
    """捕获传给 extractor 的上下文参数。"""
    def __init__(self):
        self.captured_prompt = ""

    async def complete(self, system_prompt, user_prompt, json_mode=False, temperature=0.7):
        self.captured_prompt = user_prompt
        return '{"space_type": "购物中心中庭", "budget": 1000000}'


class TestRecognizePassesContext:
    @pytest.mark.asyncio
    async def test_recognize_passes_previous_intent_to_llm(self):
        service = IntentRecognitionService(
            llm_client=_ContextCapturingLLM(),
            semantic_matcher=DummySemanticMatcher(),
        )
        previous = ValidatedIntent(
            theme=RecognizedField(name="theme", value="新春国潮", source=FieldSource.LLM, confidence=0.85),
            style=RecognizedField(name="style", value="国潮", source=FieldSource.LLM, confidence=1.0),
        )
        await service.recognize("购物中心中庭", previous_intent=previous)
        prompt = service._llm_client.captured_prompt
        assert "新春国潮" in prompt
        assert "国潮" in prompt

    @pytest.mark.asyncio
    async def test_recognize_passes_recent_messages_to_llm(self):
        service = IntentRecognitionService(
            llm_client=_ContextCapturingLLM(),
            semantic_matcher=DummySemanticMatcher(),
        )
        await service.recognize(
            "预算100万",
            recent_messages=["新春国潮国潮风格"],
        )
        prompt = service._llm_client.captured_prompt
        assert "新春国潮国潮风格" in prompt

    @pytest.mark.asyncio
    async def test_recognize_passes_summary_to_llm(self):
        service = IntentRecognitionService(
            llm_client=_ContextCapturingLLM(),
            semantic_matcher=DummySemanticMatcher(),
        )
        await service.recognize(
            "预算100万",
            conversation_summary="第1轮：主题=新春国潮",
        )
        prompt = service._llm_client.captured_prompt
        assert "主题=新春国潮" in prompt

    @pytest.mark.asyncio
    async def test_recognize_without_context_still_works(self):
        service = IntentRecognitionService(
            llm_client=_ContextCapturingLLM(),
            semantic_matcher=DummySemanticMatcher(),
        )
        result = await service.recognize("购物中心中庭")
        assert result.space_type is not None
        assert result.space_type.value == "购物中心中庭"

    @pytest.mark.asyncio
    async def test_merge_context_inherits_theme_from_previous(self):
        """验证 previous_intent 传入后 merge_context 正确继承字段。"""
        service = IntentRecognitionService(
            llm_client=_ContextCapturingLLM(),
            semantic_matcher=DummySemanticMatcher(),
        )
        previous = ValidatedIntent(
            theme=RecognizedField(name="theme", value="新春国潮", source=FieldSource.LLM, confidence=0.85),
            style=RecognizedField(name="style", value="国潮", source=FieldSource.LLM, confidence=1.0),
        )
        # LLM 返回 space_type + budget，不含 theme/style
        result = await service.recognize("购物中心中庭100万", previous_intent=previous)
        # space_type 和 budget 来自当前轮
        assert result.space_type is not None
        assert result.budget is not None
        # theme 和 style 从 previous_intent 继承
        assert result.theme is not None
        assert result.theme.value == "新春国潮"
        assert result.style is not None
        assert result.style.value == "国潮"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestRecognizePassesContext -v`
Expected: FAIL with "TypeError: recognize() got an unexpected keyword argument 'recent_messages'"

- [ ] **Step 3: 修改 `recognize` 方法**

在 `agent-core/app/services/intent_recognition.py` 中，修改 `recognize` 方法（L67-95）：

```python
    async def recognize(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
        project_id: str | None = None,
        recent_messages: list[str] | None = None,
        conversation_summary: str = "",
    ) -> ValidatedIntent:
        trace_id = str(uuid.uuid4())

        llm_output = await self._llm_extractor.extract(
            text,
            previous_intent=previous_intent,
            recent_messages=recent_messages,
            conversation_summary=conversation_summary,
        )
        rule_output = await self._rule_extractor.extract(text)
        merged_output = _merge_intent_outputs(llm_output, rule_output)

        validated = self._validator.validate(merged_output, text)
        validated = self._validator.merge_context(validated, previous_intent)
        validated = self.apply_defaults(validated)
        validated.trace_id = trace_id

        if self._trace_recorder is not None:
            await self._trace_recorder.record(
                trace_id=trace_id,
                project_id=project_id,
                input_text=text,
                llm_output=llm_output,
                rule_output=rule_output,
                merged_output=merged_output,
                validated=validated,
            )

        return validated
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestRecognizePassesContext -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 运行已有测试确认无回归**

Run: `cd agent-core && python -m pytest tests/services/test_intent_recognition.py tests/intent/test_intent_recognition.py -v`
Expected: PASS (所有已有测试)

- [ ] **Step 6: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/services/intent_recognition.py agent-core/tests/services/test_intent_context.py
git commit -m "feat: recognize passes context (previous_intent, recent_messages, summary) to LLM extractor"
```

---

## Task 4: Python 端 — API 端点和 parse 方法接线

**Files:**
- Modify: `agent-core/app/api/routers.py:77-82`
- Modify: `agent-core/app/agents/input_parser.py:157-165`
- Test: `agent-core/tests/services/test_intent_context.py`（追加测试类）

**Interfaces:**
- Consumes: `IntentRecognitionService.recognize(text, previous_intent, project_id, recent_messages, conversation_summary)` from Task 3
- Consumes: `TextParser._dict_to_validated_intent(data)` from Task 1
- Produces: `POST /agents/input-parser/parse-text` 接受 `previous_intent`、`recent_messages`、`conversation_summary` 字段

- [ ] **Step 1: 写失败测试**

在 `agent-core/tests/services/test_intent_context.py` 中追加：

```python
from app.agents.input_parser import TextParser
from unittest.mock import AsyncMock, patch


class TestTextParserParseWithContext:
    @pytest.mark.asyncio
    async def test_parse_passes_all_context_to_recognize(self):
        parser = TextParser()

        mock_service = AsyncMock()
        mock_service.recognize = AsyncMock(return_value=ValidatedIntent(
            space_type=RecognizedField(name="space_type", value="购物中心中庭", source=FieldSource.LLM, confidence=1.0),
        ))

        with patch.object(parser, "_intent_service", mock_service):
            await parser.parse(
                "购物中心中庭",
                project_id="test-123",
                previous_intent={"theme": "新春国潮", "style": "国潮"},
                recent_messages=["新春国潮国潮风格"],
                conversation_summary="第1轮：主题=新春国潮",
            )

        mock_service.recognize.assert_called_once()
        call_kwargs = mock_service.recognize.call_args.kwargs
        assert call_kwargs["text"] == "购物中心中庭"
        assert call_kwargs["project_id"] == "test-123"
        assert call_kwargs["previous_intent"] is not None
        assert call_kwargs["previous_intent"].theme.value == "新春国潮"
        assert call_kwargs["recent_messages"] == ["新春国潮国潮风格"]
        assert call_kwargs["conversation_summary"] == "第1轮：主题=新春国潮"

    @pytest.mark.asyncio
    async def test_parse_without_context_still_works(self):
        parser = TextParser()

        mock_service = AsyncMock()
        mock_service.recognize = AsyncMock(return_value=ValidatedIntent(
            space_type=RecognizedField(name="space_type", value="快闪店", source=FieldSource.LLM, confidence=1.0),
        ))

        with patch.object(parser, "_intent_service", mock_service):
            result = await parser.parse("快闪店")

        mock_service.recognize.assert_called_once()
        call_kwargs = mock_service.recognize.call_args.kwargs
        assert call_kwargs["previous_intent"] is None
        assert call_kwargs["recent_messages"] is None
        assert call_kwargs["conversation_summary"] == ""
        assert result["space_type"] == "快闪店"

    @pytest.mark.asyncio
    async def test_parse_with_invalid_previous_intent_degrades_gracefully(self):
        parser = TextParser()

        mock_service = AsyncMock()
        mock_service.recognize = AsyncMock(return_value=ValidatedIntent(
            space_type=RecognizedField(name="space_type", value="快闪店", source=FieldSource.LLM, confidence=1.0),
        ))

        with patch.object(parser, "_intent_service", mock_service):
            await parser.parse(
                "快闪店",
                previous_intent={"invalid": "data"},
            )

        call_kwargs = mock_service.recognize.call_args.kwargs
        # 无效的 previous_intent 转换后为 None，不阻断流程
        assert call_kwargs["previous_intent"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestTextParserParseWithContext -v`
Expected: FAIL with "TypeError: parse() got an unexpected keyword argument 'previous_intent'"

- [ ] **Step 3: 修改 `TextParser.parse` 方法**

在 `agent-core/app/agents/input_parser.py` 中，修改 `parse` 方法（L157-165）：

```python
    async def parse(
        self,
        text: str,
        project_id: str | None = None,
        previous_intent: dict | None = None,
        recent_messages: list[str] | None = None,
        conversation_summary: str = "",
    ) -> dict[str, Any]:
        from app.core.config import settings

        if getattr(settings, "intent_parser_legacy", False):
            return self._get_fallback_parse(text)

        service = self._intent_service or get_intent_service()

        prev_validated = None
        if previous_intent:
            try:
                prev_validated = self._dict_to_validated_intent(previous_intent)
            except Exception as e:
                print(f"TextParser.parse: _dict_to_validated_intent failed (non-fatal): {type(e).__name__}: {e}")
                prev_validated = None

        result = await service.recognize(
            text,
            previous_intent=prev_validated,
            project_id=project_id,
            recent_messages=recent_messages,
            conversation_summary=conversation_summary,
        )
        return self._validated_intent_to_dict(result)
```

- [ ] **Step 4: 修改 `routers.py` 的 `parse_text` 端点**

在 `agent-core/app/api/routers.py` 中，修改 `parse_text`（L77-82）：

```python
@router.post("/agents/input-parser/parse-text")
async def parse_text(payload: dict):
    text = payload.get("text", "")
    project_id = payload.get("project_id")
    previous_intent = payload.get("previous_intent")
    recent_messages = payload.get("recent_messages")
    conversation_summary = payload.get("conversation_summary", "")
    parser = TextParser()
    return await parser.parse(
        text,
        project_id=project_id,
        previous_intent=previous_intent,
        recent_messages=recent_messages,
        conversation_summary=conversation_summary,
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd agent-core && python -m pytest tests/services/test_intent_context.py::TestTextParserParseWithContext -v`
Expected: PASS (3 tests)

- [ ] **Step 6: 运行全部 Python 测试确认无回归**

Run: `cd agent-core && python -m pytest tests/ -v --tb=short`
Expected: PASS (所有测试)

- [ ] **Step 7: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/api/routers.py agent-core/app/agents/input_parser.py agent-core/tests/services/test_intent_context.py
git commit -m "feat: wire context passing through parse_text endpoint and TextParser.parse"
```

---

## Task 5: Java 端 — DialogueService 提取上下文

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java:72-77`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueContextTest.java`

**Interfaces:**
- Consumes: `SessionMessageService.listMessages(projectId, userId)` — 已有
- Consumes: `Project.getRequirementJson()` — 已有
- Produces: `DialogueService.extractPreviousIntent(Map<String, Object> requirementJson)` — 提取已识别字段
- Produces: `DialogueService.getRecentUserMessages(String projectId, Long userId, int limit, String excludeContent)` — 检索最近用户消息
- Produces: `DialogueService.generateConversationSummary(List<Object> rawInputs)` — 从 raw_inputs 生成摘要

- [ ] **Step 1: 写失败测试**

创建 `agent-api/src/test/java/com/meichen/orchestrator/service/DialogueContextTest.java`：

```java
package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.*;

import static org.assertj.core.api.Assertions.assertThat;

class DialogueContextTest {

    private DialogueService dialogueService;

    @BeforeEach
    void setUp() {
        dialogueService = new DialogueService(
            WebClient.builder(),
            null, null, null, new ObjectMapper(), null, Runnable::run, "http://localhost:8000"
        );
    }

    @Test
    void extractPreviousIntent_excludesInternalFields() {
        Map<String, Object> requirementJson = new HashMap<>();
        requirementJson.put("theme", "新春国潮");
        requirementJson.put("style", "国潮");
        requirementJson.put("space_type", "购物中心中庭");
        requirementJson.put("budget", 1000000);
        requirementJson.put("budget_level", "medium");
        requirementJson.put("timeline", "2-3周");
        requirementJson.put("raw_inputs", List.of(Map.of("theme", "新春国潮")));
        requirementJson.put("_recognition_meta", Map.of("trace_id", "abc"));
        requirementJson.put("trace_id", "abc-123");
        requirementJson.put("source_type", "text");
        requirementJson.put("space_description", "购物中心中庭商业空间");
        requirementJson.put("color_palette", List.of("#FFFFFF"));
        requirementJson.put("material_suggestions", List.of("亚克力"));

        Map<String, Object> result = dialogueService.extractPreviousIntent(requirementJson);

        assertThat(result).containsKeys("theme", "style", "space_type", "budget", "budget_level", "timeline");
        assertThat(result).doesNotContainKeys(
            "raw_inputs", "_recognition_meta", "trace_id", "source_type",
            "space_description", "color_palette", "material_suggestions",
            "constraints", "conflicts", "needs_confirmation", "missing_fields",
            "is_complete", "mood_keywords", "design_direction", "spatial_notes",
            "risk_hints", "needs_clarification", "clarification_question",
            "low_confidence_fields"
        );
        assertThat(result.get("theme")).isEqualTo("新春国潮");
        assertThat(result.get("style")).isEqualTo("国潮");
    }

    @Test
    void extractPreviousIntent_emptyJsonReturnsEmptyMap() {
        Map<String, Object> result = dialogueService.extractPreviousIntent(new HashMap<>());
        assertThat(result).isEmpty();
    }

    @Test
    void extractPreviousIntent_nullReturnsEmptyMap() {
        Map<String, Object> result = dialogueService.extractPreviousIntent(null);
        assertThat(result).isEmpty();
    }

    @Test
    void extractPreviousIntent_includesListFields() {
        Map<String, Object> requirementJson = new HashMap<>();
        requirementJson.put("material_restrictions", List.of("真植物"));
        requirementJson.put("allowed_materials", List.of("亚克力"));
        requirementJson.put("special_requirements", List.of("需要灯光"));
        requirementJson.put("points", List.of(Map.of("name", "中庭", "count", 1)));

        Map<String, Object> result = dialogueService.extractPreviousIntent(requirementJson);

        assertThat(result).containsKey("material_restrictions");
        assertThat(result).containsKey("allowed_materials");
        assertThat(result).containsKey("special_requirements");
        assertThat(result).containsKey("points");
    }

    @Test
    void generateConversationSummary_moreThanThreeRounds() {
        List<Object> rawInputs = new ArrayList<>();
        rawInputs.add(Map.of("theme", "新春国潮", "style", "国潮"));
        rawInputs.add(Map.of("space_type", "购物中心中庭", "budget", 1000000));
        rawInputs.add(Map.of("points", List.of(Map.of("name", "中庭"))));
        rawInputs.add(Map.of("budget", 2000000));

        String summary = dialogueService.generateConversationSummary(rawInputs);

        assertThat(summary).contains("新春国潮");
        assertThat(summary).contains("国潮");
        assertThat(summary).contains("购物中心中庭");
    }

    @Test
    void generateConversationSummary_threeOrFewerReturnsEmpty() {
        List<Object> rawInputs = new ArrayList<>();
        rawInputs.add(Map.of("theme", "新春国潮"));

        String summary = dialogueService.generateConversationSummary(rawInputs);
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_emptyReturnsEmpty() {
        String summary = dialogueService.generateConversationSummary(Collections.emptyList());
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_nullReturnsEmpty() {
        String summary = dialogueService.generateConversationSummary(null);
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_cappedAtFiftyLines() {
        List<Object> rawInputs = new ArrayList<>();
        for (int i = 0; i < 60; i++) {
            rawInputs.add(Map.of("theme", "主题" + i));
        }

        String summary = dialogueService.generateConversationSummary(rawInputs);
        String[] lines = summary.split("\n");
        assertThat(lines.length).isLessThanOrEqualTo(50);
    }
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-api && mvn test -pl agent-api -Dtest=DialogueContextTest -q`
Expected: FAIL with "cannot find symbol: method extractPreviousIntent"

- [ ] **Step 3: 实现上下文提取方法**

在 `agent-core/app/services/intent_llm_extractor.py` 的 `DialogueService` 类中，在 `findDiscardedFields` 方法之后（L256 后）新增 3 个方法：

```java
    private static final Set<String> INTERNAL_FIELDS = Set.of(
        "raw_inputs", "_recognition_meta", "trace_id", "source_type",
        "space_description", "color_palette", "material_suggestions",
        "mood_keywords", "design_direction", "spatial_notes",
        "risk_hints", "constraints", "conflicts", "needs_confirmation",
        "missing_fields", "is_complete", "needs_clarification",
        "clarification_question", "low_confidence_fields", "references"
    );

    private static final Set<String> CONTEXT_FIELDS = Set.of(
        "theme", "style", "space_type", "budget", "budget_level",
        "target_audience", "timeline", "color_preference", "brand_positioning",
        "design_system_preference", "material_restrictions", "allowed_materials",
        "special_requirements", "points"
    );

    Map<String, Object> extractPreviousIntent(Map<String, Object> requirementJson) {
        if (requirementJson == null || requirementJson.isEmpty()) {
            return new HashMap<>();
        }
        Map<String, Object> result = new HashMap<>();
        for (String key : CONTEXT_FIELDS) {
            Object value = requirementJson.get(key);
            if (value != null) {
                if (value instanceof String s && s.isBlank()) {
                    continue;
                }
                if (value instanceof Collection<?> c && c.isEmpty()) {
                    continue;
                }
                result.put(key, value);
            }
        }
        return result;
    }

    List<String> getRecentUserMessages(String projectId, Long userId, int limit, String excludeContent) {
        try {
            List<SessionMessage> messages = sessionMessageService.listMessages(projectId, userId);
            List<String> userMessages = new ArrayList<>();
            // 从最新到最旧遍历，跳过当前轮的消息
            for (int i = messages.size() - 1; i >= 0 && userMessages.size() < limit; i--) {
                SessionMessage msg = messages.get(i);
                if ("user".equals(msg.getRole()) && !msg.getContent().equals(excludeContent)) {
                    String content = msg.getContent();
                    if (content.length() > 200) {
                        content = content.substring(0, 200);
                    }
                    userMessages.add(content);
                }
            }
            // 反转为时间正序
            Collections.reverse(userMessages);
            return userMessages;
        } catch (Exception e) {
            log.warn("Failed to retrieve recent user messages for project {}: {} — {}",
                projectId, e.getClass().getName(), e.getMessage());
            return Collections.emptyList();
        }
    }

    String generateConversationSummary(List<Object> rawInputs) {
        if (rawInputs == null || rawInputs.size() <= 3) {
            return "";
        }
        try {
            List<String> lines = new ArrayList<>();
            int startIdx = Math.max(0, rawInputs.size() - 50);
            for (int i = startIdx; i < rawInputs.size(); i++) {
                @SuppressWarnings("unchecked")
                Map<String, Object> input = (Map<String, Object>) rawInputs.get(i);
                if (input == null) continue;
                List<String> parts = new ArrayList<>();
                addSummaryField(parts, input, "theme", "主题");
                addSummaryField(parts, input, "style", "风格");
                addSummaryField(parts, input, "space_type", "空间类型");
                addSummaryField(parts, input, "budget", "预算");
                if (!parts.isEmpty()) {
                    lines.add("第" + (i + 1) + "轮：" + String.join("，", parts));
                }
            }
            return String.join("\n", lines);
        } catch (Exception e) {
            log.warn("Failed to generate conversation summary: {} — {}", e.getClass().getName(), e.getMessage());
            return "";
        }
    }

    @SuppressWarnings("unchecked")
    private void addSummaryField(List<String> parts, Map<String, Object> input, String key, String label) {
        Object value = input.get(key);
        if (value != null && !(value instanceof String s && s.isBlank())) {
            parts.add(label + "=" + value);
        }
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd agent-api && mvn test -pl agent-api -Dtest=DialogueContextTest -q`
Expected: PASS (9 tests)

- [ ] **Step 5: 修改 `processUserMessage` 中的 `postToAgent` 调用**

在 `agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java` 中，修改 L72-77：

将：
```java
            // 1. 文本解析
            pushThinking(projectId, "text_parse", "started");
            Map<String, Object> textParse = postToAgent(
                "/agents/input-parser/parse-text",
                Map.of("text", content, "project_id", projectId)
            );
```

改为：
```java
            // 1. 文本解析（传入上下文：已识别需求 + 最近对话 + 历史摘要）
            pushThinking(projectId, "text_parse", "started");
            Map<String, Object> existingReq = parseJson(project.getRequirementJson());
            Map<String, Object> previousIntent = extractPreviousIntent(existingReq);
            List<String> recentMessages = getRecentUserMessages(projectId, userId, 3, content);
            @SuppressWarnings("unchecked")
            List<Object> rawInputs = (List<Object>) existingReq.getOrDefault("raw_inputs", Collections.emptyList());
            String conversationSummary = generateConversationSummary(rawInputs);

            Map<String, Object> parseRequest = new HashMap<>();
            parseRequest.put("text", content);
            parseRequest.put("project_id", projectId);
            if (!previousIntent.isEmpty()) {
                parseRequest.put("previous_intent", previousIntent);
            }
            if (!recentMessages.isEmpty()) {
                parseRequest.put("recent_messages", recentMessages);
            }
            if (!conversationSummary.isEmpty()) {
                parseRequest.put("conversation_summary", conversationSummary);
            }
            log.info("text_parse context: previous_intent_keys={}, recent_messages_count={}, summary_lines={}",
                previousIntent.keySet(), recentMessages.size(),
                conversationSummary.isEmpty() ? 0 : conversationSummary.split("\n").length);

            Map<String, Object> textParse = postToAgent("/agents/input-parser/parse-text", parseRequest);
```

- [ ] **Step 6: 运行已有测试确认无回归**

Run: `cd agent-api && mvn test -pl agent-api -Dtest=DialogueServiceTest,DialogueContextTest -q`
Expected: PASS (所有测试)

- [ ] **Step 7: 提交**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java agent-api/src/test/java/com/meichen/orchestrator/service/DialogueContextTest.java
git commit -m "feat: DialogueService extracts and passes context (previous_intent, recent_messages, summary) to parse-text API"
```

---

## Task 6: 集成验证和回归测试

**Files:**
- Test: 手动验证 + 回归测试

**Interfaces:**
- Consumes: 所有前 5 个任务的成果

- [ ] **Step 1: 运行全部 Python 测试**

Run: `cd agent-core && python -m pytest tests/ -v --tb=short`
Expected: PASS (所有测试)

- [ ] **Step 2: 运行全部 Java 测试**

Run: `cd agent-api && mvn test -pl agent-api -q`
Expected: PASS (所有测试)

- [ ] **Step 3: 启动服务进行手动验证**

启动 agent-core：
```bash
cd agent-core && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

启动 agent-api：
```bash
cd agent-api && mvn spring-boot:run -pl agent-api &
```

- [ ] **Step 4: 模拟多轮对话场景验证**

创建新项目，发送第一条消息：
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"theme": "新春国潮", "space_type": "购物中心中庭"}'
```

发送第一条对话（只提主题和风格）：
```bash
curl -X POST http://localhost:8080/api/dialogue/649797d9-bf8a-496b-ab12-c440139a9af1/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "新春国潮国潮风格"}'
```

发送第二条对话（只提空间类型和预算）：
```bash
curl -X POST http://localhost:8080/api/dialogue/649797d9-bf8a-496b-ab12-c440139a9af1/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "购物中心中庭预算100万"}'
```

检查 agent-core 日志：
- 确认第二次调用 parse-text 时请求体包含 `previous_intent`（含 theme="新春国潮", style="国潮"）
- 确认包含 `recent_messages`（含"新春国潮国潮风格"）
- 确认 LLM prompt 包含"之前已识别的需求"区块
- 确认 LLM 返回结果包含 theme 和 style（从上下文继承）

- [ ] **Step 5: 验证首次对话行为不变**

创建新项目，发送第一条消息，确认：
- 请求体不包含 `previous_intent`、`recent_messages`、`conversation_summary`
- LLM prompt 不包含上下文区块
- 识别结果与当前行为一致

- [ ] **Step 6: 提交最终验证记录**

```bash
cd /Users/liulei/private-work/design-agent
git log --oneline -6
```

确认 6 个提交都在分支上。

---

## Self-Review

### Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|----------|
| previous_intent 从 requirementJson 提取，排除内部字段 | Task 5: extractPreviousIntent |
| recent_messages 检索最近 3 条用户消息 | Task 5: getRecentUserMessages |
| conversation_summary 从 raw_inputs 生成，≤3 轮为空 | Task 5: generateConversationSummary |
| LLM prompt 包含 3 个上下文区块 | Task 2: _context_prompt_fragment |
| merge_context 启用（previous_intent 传入即生效） | Task 3: recognize 传 previous_intent |
| 首次对话行为不变 | Task 6: Step 5 回归验证 |
| Token 预算控制 | Task 2: 截断 200 字符 + 50 行上限 |
| 错误降级不阻断主流程 | Task 4: try-except 降级 + Task 5: getRecentUserMessages try-catch |

### Placeholder 扫描

- ✅ 无 TBD/TODO
- ✅ 每个步骤都有完整代码
- ✅ 每个测试都有具体断言
- ✅ 命令和预期输出明确

### 类型一致性

- `extractPreviousIntent` — Java: `Map<String, Object> extractPreviousIntent(Map<String, Object>)` → Task 5 定义并使用
- `getRecentUserMessages` — Java: `List<String> getRecentUserMessages(String, Long, int, String)` → Task 5 定义并使用
- `generateConversationSummary` — Java: `String generateConversationSummary(List<Object>)` → Task 5 定义并使用
- `_dict_to_validated_intent` — Python: `ValidatedIntent | None _dict_to_validated_intent(dict | None)` → Task 1 定义，Task 4 使用
- `extract` — Python: `async def extract(text, previous_intent=None, recent_messages=None, conversation_summary="")` → Task 2 定义，Task 3 使用
- `recognize` — Python: `async def recognize(text, previous_intent=None, project_id=None, recent_messages=None, conversation_summary="")` → Task 3 定义，Task 4 使用
- `parse` — Python: `async def parse(text, project_id=None, previous_intent=None, recent_messages=None, conversation_summary="")` → Task 4 定义
