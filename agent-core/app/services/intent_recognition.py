from __future__ import annotations

import uuid
from typing import Protocol

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.intent_recognition_result import (
    IntentRecognitionResult,
    ValidatedIntent,
)
from app.services.intent_rule_extractor import IntentRuleExtractor
from app.services.intent_schemas import IntentOutput
from app.services.intent_validator import IntentValidator
from app.services.llm_client import llm_client as _default_llm_client
from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import Taxonomy, load_taxonomy

SEMANTIC_THRESHOLD = 0.82


def _merge_intent_outputs(llm_output: IntentOutput, rule_output: IntentOutput) -> IntentOutput:
    """规则只补齐 LLM 没有返回的字段。"""
    merged = llm_output.model_copy(deep=True) if llm_output else IntentOutput()
    for field_name in IntentOutput.model_fields:
        llm_value = getattr(merged, field_name)
        rule_value = getattr(rule_output, field_name)
        if field_name in ("points", "material_restrictions", "allowed_materials", "special_requirements"):
            if not llm_value and rule_value:
                setattr(merged, field_name, rule_value)
        elif llm_value is None or llm_value == "":
            if rule_value is not None and rule_value != "":
                setattr(merged, field_name, rule_value)
    return merged


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        ...


class IntentRecognitionService:
    """LLM 结构化输出优先的意图识别服务。"""

    def __init__(
        self,
        taxonomy: Taxonomy | None = None,
        llm_client: LLMClient | None = None,
        semantic_matcher: SemanticMatcher | None = None,
    ):
        self.taxonomy = taxonomy or load_taxonomy()
        self._llm_client = llm_client or _default_llm_client
        self._semantic_matcher = semantic_matcher or SemanticMatcher(
            self.taxonomy, threshold=SEMANTIC_THRESHOLD
        )
        self._llm_extractor = IntentLLMExtractor(self.taxonomy, self._llm_client)
        self._rule_extractor = IntentRuleExtractor(self.taxonomy)
        self._validator = IntentValidator(self.taxonomy)
        self._trace_recorder: "IntentTraceRecorder | None" = None  # set in Task 4

    async def recognize(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
    ) -> ValidatedIntent:
        trace_id = str(uuid.uuid4())

        llm_output = await self._llm_extractor.extract(text)
        rule_output = await self._rule_extractor.extract(text)
        merged_output = _merge_intent_outputs(llm_output, rule_output)

        validated = self._validator.validate(merged_output, text)
        validated = self._validator.merge_context(validated, previous_intent)
        validated = self.apply_defaults(validated)
        validated.trace_id = trace_id

        if self._trace_recorder is not None:
            await self._trace_recorder.record(
                trace_id=trace_id,
                project_id=None,  # filled by caller
                input_text=text,
                llm_output=llm_output,
                rule_output=rule_output,
                merged_output=merged_output,
                validated=validated,
            )

        return validated

    def fill_missing_from_context(
        self,
        result: IntentRecognitionResult,
        last_intent: IntentRecognitionResult | None,
    ) -> IntentRecognitionResult:
        if last_intent is None:
            return result

        inherit_fields = [
            "style",
            "color_preference",
            "brand_positioning",
            "design_system_preference",
        ]
        for field_name in inherit_fields:
            current = getattr(result, field_name)
            previous = getattr(last_intent, field_name)
            if current is None and previous is not None:
                setattr(result, field_name, previous)

        for field_name in ("material_restrictions", "special_requirements"):
            current = getattr(result, field_name)
            previous = getattr(last_intent, field_name)
            if not current and previous:
                setattr(result, field_name, previous)

        return result

    def apply_defaults(self, result: ValidatedIntent) -> ValidatedIntent:
        return self._validator.apply_defaults(result)


_intent_service: IntentRecognitionService | None = None


def get_intent_service() -> IntentRecognitionService:
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentRecognitionService()
    return _intent_service
