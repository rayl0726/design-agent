from __future__ import annotations

import re
from typing import Protocol

import jieba  # type: ignore[import-untyped]
from rapidfuzz import fuzz

from app.services.intent_llm_extractor import IntentLLMExtractor
from app.services.intent_recognition_result import (
    FieldSource,
    IntentRecognitionResult,
    RecognizedField,
    ValidatedIntent,
)
from app.services.intent_schemas import IntentOutput
from app.services.intent_validator import IntentValidator
from app.services.llm_client import llm_client as _default_llm_client
from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import Taxonomy, load_taxonomy

FUZZY_THRESHOLD = 0.75
FUZZY_THRESHOLD_CRITICAL = 0.85
SEMANTIC_THRESHOLD = 0.82


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        ...


class _RuleBasedExtractor:
    """规则提取器，作为 LLM 失败时的降级方案。"""

    def __init__(self, taxonomy: Taxonomy):
        self.taxonomy = taxonomy
        self._semantic_matcher = SemanticMatcher(taxonomy, threshold=SEMANTIC_THRESHOLD)
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

    async def extract(self, text: str) -> IntentOutput:
        tokens = [t for t in jieba.lcut(text) if t.strip()]
        output = IntentOutput()

        space_type = await self._match_field(
            tokens, self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type
        )
        output.space_type = space_type

        output.points = self._match_points(tokens)

        budget_field = self._extract_budget(text)
        if budget_field:
            output.budget = str(budget_field.value)

        style = await self._match_field(
            tokens, self.taxonomy.style_names, self.taxonomy.alias_to_style
        )
        output.style = style

        materials = await self._match_multi(
            tokens, self.taxonomy.material_names, self.taxonomy.alias_to_material
        )
        output.material_restrictions = materials

        restrictions = self._extract_material_restrictions(text)
        if restrictions:
            output.material_restrictions.extend(restrictions)

        allowed = self._extract_allowed_materials(text)
        if allowed:
            output.allowed_materials = allowed

        theme_field = self._extract_theme(text)
        if theme_field:
            output.theme = str(theme_field.value)

        timeline_field = self._extract_regex_field(text, r"(?:工期|时间|timeline)\s*(?:为|是|：|:)?\s*([^\n，。]+)")
        if timeline_field:
            output.timeline = str(timeline_field.value)

        color_field = self._extract_regex_field(text, r"(?:颜色|色彩|color)\s*(?:为|是|：|:)?\s*([^\n，。]+)")
        if color_field:
            output.color_preference = str(color_field.value)

        return output

    def _extract_material_restrictions(self, text: str) -> list[str]:
        """识别 '不要真植物'、'禁用亚克力' 等否定材质表达。"""
        results: list[str] = []
        # 不要/不用/禁用/避免 + 材质词
        stop_chars = "，。；;"
        patterns = [
            rf"(?:不要|不用|禁用|避免|不想用|别用)\s*([^{stop_chars}]+)",
            rf"(?:排除|去除|不要出现)\s*([^{stop_chars}]+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip()
                terms = self._extract_material_terms(fragment)
                if terms:
                    results.extend(terms)
                else:
                    # 保留原始否定对象，即使不在 taxonomy 中
                    results.append(fragment)
        return results

    def _extract_allowed_materials(self, text: str) -> list[str]:
        """识别 '亚克力可以'、'可用金属' 等肯定材质表达。"""
        results: list[str] = []
        stop_chars = "，。；;"
        patterns = [
            rf"([^{stop_chars}]+?)\s*(?:可以|可用|能用|允许使用)",
            rf"(?:可用|能用|允许使用)\s*([^{stop_chars}]+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip()
                results.extend(self._extract_material_terms(fragment))
        return results

    def _extract_material_terms(self, text: str) -> list[str]:
        """从片段中提取已知的材质词。"""
        terms: list[str] = []
        all_targets: dict[str, str] = {}
        for name in self.taxonomy.material_names:
            all_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_material.items():
            all_targets[alias] = standard

        lowered = text.lower()
        for target, standard in all_targets.items():
            if target in lowered and standard not in terms:
                terms.append(standard)
        return terms

    async def _match_field(
        self,
        tokens: list[str],
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> str | None:
        for token in tokens:
            if token in exact_names:
                return token

        for token in tokens:
            key = token.lower()
            if key in alias_map:
                return alias_map[key]

        # 子串匹配：处理 "中庭吊饰" 包含 "中庭" 别名的情况
        all_targets: dict[str, str] = {}
        for name in exact_names:
            all_targets[name] = name
        for alias, standard in alias_map.items():
            all_targets[alias] = standard

        for token in tokens:
            token_lower = token.lower()
            for target, standard in all_targets.items():
                if len(target) >= 2 and target in token_lower:
                    return standard

        best: tuple[str, float] | None = None
        for token in tokens:
            for target, standard in all_targets.items():
                score = fuzz.ratio(token, target) / 100.0
                if score >= FUZZY_THRESHOLD and (best is None or score > best[1]):
                    best = (standard, score)

        if best and best[1] >= FUZZY_THRESHOLD_CRITICAL:
            return best[0]

        semantic_name, _ = await self._semantic_matcher.match(" ".join(tokens), "space_type")
        return semantic_name

    def _match_points(self, tokens: list[str]) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        all_point_targets: dict[str, str] = {}
        for name in self.taxonomy.point_names:
            all_point_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_point.items():
            all_point_targets[alias] = standard

        for token in tokens:
            token_lower = token.lower()
            if token in self.taxonomy.point_names and token not in seen:
                found.append(token)
                seen.add(token)
                continue
            if token_lower in self.taxonomy.alias_to_point:
                standard = self.taxonomy.alias_to_point[token_lower]
                if standard not in seen:
                    found.append(standard)
                    seen.add(standard)
                continue
            # 子串匹配
            for target, standard in all_point_targets.items():
                if len(target) >= 2 and target in token_lower and standard not in seen:
                    found.append(standard)
                    seen.add(standard)
                    break
        return found

    def _extract_budget(self, text: str) -> RecognizedField | None:
        # 支持范围表达：20万-30万、二十万到三十万、20万~30万
        range_pattern = r"([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[~\-到至]\s*([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[万w千k元]?"
        match = re.search(range_pattern, text)
        if match:
            return RecognizedField(
                name="budget",
                value=match.group(0).strip(),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
            )

        # 支持单个数字+单位：30万、300k、5千
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|w|千|k|元)", text, re.IGNORECASE)
        if match:
            return RecognizedField(
                name="budget",
                value=match.group(0).strip(),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
            )

        # 支持中文数字+单位：三十万、五千
        match = re.search(r"([零一二两三四五六七八九十百千万亿]+)\s*[万w千k元]?", text)
        if match:
            return RecognizedField(
                name="budget",
                value=match.group(0).strip(),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
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

    def _extract_theme(self, text: str) -> RecognizedField | None:
        # 优先支持 "X主题" 格式
        match = re.search(r"([^\n，。]+?)(?:主题|概念|theme)", text)
        if match:
            return RecognizedField(
                name="theme",
                value=match.group(1).strip(),
                source=FieldSource.EXACT,
                confidence=1.0,
                raw_text=match.group(0),
            )
        # 其次支持 "主题为X"、"主题：X" 格式
        match = re.search(r"(?:主题|概念|theme)\s*(?:为|是|：|:)\s*([^\n，。]+)", text)
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
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token in exact_names and token not in seen:
                results.append(token)
                seen.add(token)
            key = token.lower()
            if key in alias_map:
                standard = alias_map[key]
                if standard not in seen:
                    results.append(standard)
                    seen.add(standard)
        return results


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
        self._rule_extractor = _RuleBasedExtractor(self.taxonomy)
        self._validator = IntentValidator(self.taxonomy)

    async def recognize(
        self,
        text: str,
        previous_intent: ValidatedIntent | None = None,
    ) -> ValidatedIntent:
        # 1. LLM 结构化输出优先
        llm_output = await self._llm_extractor.extract(text)

        # 2. LLM 失败时使用规则 fallback
        if llm_output is None:
            llm_output = await self._rule_extractor.extract(text)

        # 3. 后校验
        validated = self._validator.validate(llm_output, text)

        # 4. 上下文继承
        validated = self._validator.merge_context(validated, previous_intent)

        # 5. 应用默认值
        validated = self._validator.apply_defaults(validated)

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
