from __future__ import annotations

import contextlib
import json
import re
from typing import Protocol

import jieba  # type: ignore[import-untyped]
from rapidfuzz import fuzz

from app.services.intent_recognition_result import (
    FieldSource,
    IntentRecognitionResult,
    RecognizedField,
)
from app.services.llm_client import llm_client as _default_llm_client
from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import Taxonomy, load_taxonomy

FUZZY_THRESHOLD = 0.75
FUZZY_THRESHOLD_CRITICAL = 0.85
SEMANTIC_THRESHOLD = 0.82


class LLMClient(Protocol):
    async def complete(self, system: str, prompt: str, json_mode: bool = True) -> str:
        ...


class IntentRecognitionService:
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
        self._load_jieba_dict()

    def _load_jieba_dict(self) -> None:
        terms: list[str] = []
        sources = (
            self.taxonomy.space_types
            + self.taxonomy.points
            + self.taxonomy.styles
            + self.taxonomy.materials
        )
        for item in sources:
            terms.append(item["name"])
            terms.extend(item.get("aliases", []))
        for term in set(terms):
            jieba.add_word(term, freq=1000)

    async def recognize(self, text: str) -> IntentRecognitionResult:
        tokens = [t for t in jieba.lcut(text) if t.strip()]
        result = IntentRecognitionResult(raw_text=text)

        result.space_type = await self._match_field(
            tokens, "space_type", self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type
        )
        result.points = self._match_points(tokens, text)
        result.budget = self._extract_budget(text)
        result.budget_level = self._extract_budget_level(text, result.budget)
        result.style = await self._match_field(
            tokens, "style", self.taxonomy.style_names, self.taxonomy.alias_to_style
        )
        result.material_restrictions = await self._match_multi(
            tokens, "material", self.taxonomy.material_names, self.taxonomy.alias_to_material
        )
        result.theme = self._extract_regex_field(text, r"(?:主题|概念|theme)\s*[：:]\s*([^\n，。]+)")
        result.timeline = self._extract_regex_field(text, r"(?:工期|时间|timeline)\s*[：:]\s*([^\n，。]+)")
        result.color_preference = self._extract_regex_field(text, r"(?:颜色|色彩|color)\s*[：:]\s*([^\n，。]+)")

        result = await self._llm_fallback(result, text)
        return result

    async def _match_field(
        self,
        tokens: list[str],
        field_type: str,
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> RecognizedField | None:
        for token in tokens:
            if token in exact_names:
                return RecognizedField(
                    name=field_type,
                    value=token,
                    source=FieldSource.EXACT,
                    confidence=1.0,
                    raw_text=token,
                )

        for token in tokens:
            key = token.lower()
            if key in alias_map:
                standard = alias_map[key]
                return RecognizedField(
                    name=field_type,
                    value=standard,
                    source=FieldSource.ALIAS,
                    confidence=0.95,
                    raw_text=token,
                )

        best: tuple[str, float] | None = None
        all_targets: dict[str, str] = {}
        for name in exact_names:
            all_targets[name] = name
        for alias, standard in alias_map.items():
            all_targets[alias] = standard

        for token in tokens:
            for target, standard in all_targets.items():
                score = fuzz.ratio(token, target) / 100.0
                if score >= FUZZY_THRESHOLD and (best is None or score > best[1]):
                    best = (standard, score)

        if best and best[1] >= FUZZY_THRESHOLD_CRITICAL:
            return RecognizedField(
                name=field_type,
                value=best[0],
                source=FieldSource.FUZZY,
                confidence=round(best[1], 2),
                raw_text=" ".join(tokens),
            )

        semantic_name, score = await self._semantic_matcher.match(" ".join(tokens), field_type)
        if semantic_name:
            return RecognizedField(
                name=field_type,
                value=semantic_name,
                source=FieldSource.SEMANTIC,
                confidence=round(score, 2),
                raw_text=" ".join(tokens),
            )

        return None

    def _match_points(self, tokens: list[str], text: str) -> list[RecognizedField]:
        found: list[RecognizedField] = []
        seen: set[str] = set()

        for token in tokens:
            if token in self.taxonomy.point_names and token not in seen:
                found.append(
                    RecognizedField(
                        name="point",
                        value=token,
                        source=FieldSource.EXACT,
                        confidence=1.0,
                        raw_text=token,
                    )
                )
                seen.add(token)
                continue
            key = token.lower()
            if key in self.taxonomy.alias_to_point:
                standard = self.taxonomy.alias_to_point[key]
                if standard not in seen:
                    found.append(
                        RecognizedField(
                            name="point",
                            value=standard,
                            source=FieldSource.ALIAS,
                            confidence=0.95,
                            raw_text=token,
                        )
                    )
                    seen.add(standard)

        for field in found:
            name = str(field.value)
            pattern = re.search(rf"{re.escape(name)}\s*[×xX*]\s*(\d+)", text)
            if pattern:
                field.value = {"name": name, "count": int(pattern.group(1))}
            else:
                field.value = {"name": name, "count": 1}
        return found

    def _extract_budget(self, text: str) -> RecognizedField | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|元|千)", text)
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            if unit == "万":
                amount *= 10000
            elif unit == "千":
                amount *= 1000
            return RecognizedField(
                name="budget",
                value=int(amount),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
            )
        return None

    def _extract_budget_level(self, text: str, budget: RecognizedField | None) -> RecognizedField | None:
        for alias, standard in self.taxonomy.alias_to_budget_level.items():
            if alias in text.lower() and len(alias) > 1:
                return RecognizedField(
                    name="budget_level",
                    value=standard,
                    source=FieldSource.ALIAS,
                    confidence=0.9,
                    raw_text=alias,
                )
        if budget and isinstance(budget.value, int):
            amount = budget.value
            if amount < 100000:
                level = "low"
            elif amount > 300000:
                level = "high"
            else:
                level = "medium"
            return RecognizedField(
                name="budget_level",
                value=level,
                source=FieldSource.DEFAULT,
                confidence=0.8,
                raw_text=str(amount),
            )
        return None

    def _extract_regex_field(self, text: str, pattern: str) -> RecognizedField | None:
        match = re.search(pattern, text)
        if match:
            return RecognizedField(
                name="theme",
                value=match.group(1).strip(),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
            )
        return None

    async def _match_multi(
        self,
        tokens: list[str],
        field_type: str,
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> list[RecognizedField]:
        results: list[RecognizedField] = []
        seen: set[str] = set()
        for token in tokens:
            if token in exact_names and token not in seen:
                results.append(
                    RecognizedField(
                        name=field_type,
                        value=token,
                        source=FieldSource.EXACT,
                        confidence=1.0,
                        raw_text=token,
                    )
                )
                seen.add(token)
            key = token.lower()
            if key in alias_map:
                standard = alias_map[key]
                if standard not in seen:
                    results.append(
                        RecognizedField(
                            name=field_type,
                            value=standard,
                            source=FieldSource.ALIAS,
                            confidence=0.95,
                            raw_text=token,
                        )
                    )
                    seen.add(standard)
        return results

    async def _llm_fallback(self, result: IntentRecognitionResult, text: str) -> IntentRecognitionResult:
        missing_fields: dict[str, list[str]] = {}
        if result.space_type is None:
            missing_fields["space_type"] = ["空间类型"] + [
                s["name"] for s in self.taxonomy.space_types[:10]
            ]
        if result.budget is None:
            missing_fields["budget"] = ["预算金额，如 150000"]

        if not missing_fields:
            return result

        system = "你是一位美陈设计需求解析助手。请仅从候选值中选择，不要编造。"
        prompt = (
            f"用户输入：{text}\n"
            "请从以下候选值中补充缺失字段，输出 JSON 不要多余文字。\n"
            "如果无法确定，保持 null。\n"
            f"{json.dumps(missing_fields, ensure_ascii=False, indent=2)}\n"
            '输出格式：{"space_type": "购物中心中庭", "budget": 150000}'
        )
        raw = await self._llm_client.complete(system, prompt, json_mode=True)
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return result

        if result.space_type is None and data.get("space_type"):
            value = data["space_type"]
            if value in self.taxonomy.space_type_names:
                result.space_type = RecognizedField(
                    name="space_type",
                    value=value,
                    source=FieldSource.LLM,
                    confidence=0.7,
                    raw_text=text,
                )

        if result.budget is None and data.get("budget"):
            value = data["budget"]
            with contextlib.suppress(ValueError, TypeError):
                result.budget = RecognizedField(
                    name="budget",
                    value=int(value),
                    source=FieldSource.LLM,
                    confidence=0.7,
                    raw_text=text,
                )

        return result

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

    def apply_defaults(self, result: IntentRecognitionResult) -> IntentRecognitionResult:
        defaults = self.taxonomy.field_defaults
        space_type_value = result.space_type.value if result.space_type else None

        points_default = (
            defaults.get("points", {})
            .get("default_by_space_type", {})
            .get(space_type_value)
        )
        if points_default and not result.points:
            result.points = [
                RecognizedField(
                    name="point",
                    value={"name": point, "count": 1},
                    source=FieldSource.DEFAULT,
                    confidence=0.6,
                )
                for point in points_default
            ]

        if result.timeline is None and defaults.get("timeline", {}).get("default_value"):
            result.timeline = RecognizedField(
                name="timeline",
                value=defaults["timeline"]["default_value"],
                source=FieldSource.DEFAULT,
                confidence=0.5,
            )

        return result


_intent_service: IntentRecognitionService | None = None


def get_intent_service() -> IntentRecognitionService:
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentRecognitionService()
    return _intent_service
