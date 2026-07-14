from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.meichen.skills.input_parser import TextParser
from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.intent_recognition_result import ValidatedIntent, RecognizedField, FieldSource
from app.services.taxonomy_loader import load_taxonomy


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


class DummySemanticMatcher:
    async def match(self, text: str, field_type: str) -> tuple[str | None, float]:
        return None, 0.0


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
