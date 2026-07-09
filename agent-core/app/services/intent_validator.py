from __future__ import annotations

import contextlib
import re
from typing import Any

from app.services.intent_recognition_result import (
    ClarificationRequest,
    FieldSource,
    RecognizedField,
    ValidatedIntent,
)
from app.services.intent_schemas import IntentOutput
from app.services.taxonomy_loader import Taxonomy, load_taxonomy


_CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "百": 100,
    "千": 1000,
    "万": 10000,
    "亿": 100000000,
}

_CLARIFICATION_QUESTIONS = {
    "space_type": "请问设计用在什么类型的商业空间？（如购物中心中庭、快闪店、百货入口等）",
    "budget": "项目预算大概是多少？",
    "theme": "您希望设计的主题或概念是什么？",
}

_REQUIRED_FIELDS = ["space_type", "budget", "theme"]


def _chinese_number_to_int(text: str) -> int | None:
    """将中文数字转换为整数。支持 "三十万"、"二十万" 等。"""
    text = text.replace(" ", "")
    if not text:
        return None

    # 尝试直接阿拉伯数字
    with contextlib.suppress(ValueError):
        return int(text)

    unit_multiplier = 1
    if "亿" in text:
        unit_multiplier = 100000000
        text = text.replace("亿", "")
    elif "万" in text:
        unit_multiplier = 10000
        text = text.replace("万", "")
    elif "千" in text:
        unit_multiplier = 1000
        text = text.replace("千", "")

    total = 0
    current = 0
    for char in text:
        if char in _CHINESE_DIGITS:
            value = _CHINESE_DIGITS[char]
            if value >= 10:
                current = (current or 1) * value
            else:
                current += value
        elif char.isdigit():
            current = current * 10 + int(char)
    total += current
    return total * unit_multiplier if total > 0 else None


def _apply_unit(amount: float, unit: str) -> int:
    unit = unit.strip().lower()
    if unit in ("万", "w"):
        return int(amount * 10000)
    if unit in ("千", "k"):
        return int(amount * 1000)
    if unit == "元":
        return int(amount)
    # 默认无单位时，若数值较小（<1000）按万元处理，否则按元处理
    if amount < 1000:
        return int(amount * 10000)
    return int(amount)


def _parse_number_with_unit(text: str) -> tuple[float, str] | None:
    """从文本中提取数字和单位。"""
    text = text.strip().lower().replace(",", "")

    # 阿拉伯数字 + 单位
    match = re.search(r"(\d+(?:\.\d+)?)\s*(万|w|k|千|元)?", text)
    if match:
        amount = float(match.group(1))
        unit = match.group(2) or ""
        return amount, unit

    # 中文数字 + 单位
    match = re.search(r"([零一二两三四五六七八九十百千万亿]+)\s*(万|w|k|千|元)?", text)
    if match:
        amount = _chinese_number_to_int(match.group(1))
        unit = match.group(2) or ""
        if amount is not None:
            return float(amount), unit

    return None


def normalize_budget(value: Any) -> int | None:
    """将各种预算表达统一转换为整数人民币（元）。"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        amount = int(value)
        if amount < 1000:
            return amount * 10000
        return amount

    if isinstance(value, str):
        text = value.strip().lower().replace(",", "")

        # 处理范围：取中间值（支持中文和阿拉伯数字）
        delimiter_match = re.search(r"(.+?)\s*[~\-到至]\s*(.+)", text)
        if delimiter_match:
            low_part = _parse_number_with_unit(delimiter_match.group(1))
            high_part = _parse_number_with_unit(delimiter_match.group(2))
            if low_part and high_part:
                low_amount = _apply_unit(low_part[0], low_part[1])
                high_amount = _apply_unit(high_part[0], high_part[1])
                return int((low_amount + high_amount) / 2)

        # 单个数字
        parsed = _parse_number_with_unit(text)
        if parsed:
            return _apply_unit(parsed[0], parsed[1])

    return None


def budget_level_from_amount(amount: int) -> str:
    if amount < 100000:
        return "low"
    if amount >= 300000:
        return "high"
    return "medium"


class IntentValidator:
    """意图后校验层：规范化值、映射别名、评分置信度、触发澄清。"""

    def __init__(
        self,
        taxonomy: Taxonomy | None = None,
        confidence_threshold: float = 0.75,
    ):
        self.taxonomy = taxonomy or load_taxonomy()
        self.confidence_threshold = confidence_threshold

    def _map_closed_field(
        self,
        value: str | None,
        field_type: str,
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> RecognizedField | None:
        if not value or not isinstance(value, str):
            return None

        stripped = value.strip()
        if stripped in exact_names:
            return RecognizedField(
                name=field_type,
                value=stripped,
                source=FieldSource.LLM,
                confidence=1.0,
                raw_text=stripped,
            )

        lowered = stripped.lower()
        if lowered in alias_map:
            return RecognizedField(
                name=field_type,
                value=alias_map[lowered],
                source=FieldSource.VALIDATED,
                confidence=0.95,
                raw_text=stripped,
            )

        # 未知值保留，但降低置信度
        return RecognizedField(
            name=field_type,
            value=stripped,
            source=FieldSource.LLM,
            confidence=0.6,
            raw_text=stripped,
        )

    def _map_materials(self, values: list[str]) -> list[RecognizedField]:
        results: list[RecognizedField] = []
        for value in values:
            field = self._map_closed_field(
                value, "material", self.taxonomy.material_names, self.taxonomy.alias_to_material
            )
            if field:
                results.append(field)
        return results

    def _map_points(self, values: list[str]) -> list[RecognizedField]:
        results: list[RecognizedField] = []
        seen: set[str] = set()
        for value in values:
            field = self._map_closed_field(
                value, "point", self.taxonomy.point_names, self.taxonomy.alias_to_point
            )
            if field and field.value not in seen:
                results.append(field)
                seen.add(str(field.value))
        return results

    def _validate_budget(self, output: IntentOutput) -> tuple[RecognizedField | None, RecognizedField | None]:
        if output.budget is None:
            return None, None

        normalized = normalize_budget(output.budget)
        if normalized is None:
            return None, None

        budget_field = RecognizedField(
            name="budget",
            value=normalized,
            source=FieldSource.VALIDATED,
            confidence=0.95,
            raw_text=str(output.budget),
        )

        if output.budget_level:
            level_field = self._map_closed_field(
                output.budget_level, "budget_level", self.taxonomy.budget_level_names, self.taxonomy.alias_to_budget_level
            )
        else:
            level_field = RecognizedField(
                name="budget_level",
                value=budget_level_from_amount(normalized),
                source=FieldSource.DEFAULT,
                confidence=0.7,
                raw_text=str(normalized),
            )

        return budget_field, level_field

    def _field_from_value(
        self,
        value: str | None,
        field_name: str,
        source: FieldSource = FieldSource.LLM,
        confidence: float = 0.85,
    ) -> RecognizedField | None:
        if not value or not isinstance(value, str):
            return None
        return RecognizedField(
            name=field_name,
            value=value.strip(),
            source=source,
            confidence=confidence,
            raw_text=value.strip(),
        )

    def validate(self, output: IntentOutput, raw_text: str) -> ValidatedIntent:
        validated = ValidatedIntent(raw_text=raw_text)

        validated.space_type = self._map_closed_field(
            output.space_type, "space_type", self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type
        )
        validated.points = self._map_points(output.points)
        validated.theme = self._field_from_value(output.theme, "theme")
        validated.budget, validated.budget_level = self._validate_budget(output)
        validated.style = self._map_closed_field(
            output.style, "style", self.taxonomy.style_names, self.taxonomy.alias_to_style
        )
        validated.material_restrictions = self._map_materials(output.material_restrictions)
        validated.allowed_materials = self._map_materials(output.allowed_materials)
        validated.color_preference = self._field_from_value(output.color_preference, "color_preference")
        validated.brand_positioning = self._field_from_value(output.brand_positioning, "brand_positioning")
        validated.target_audience = self._field_from_value(output.target_audience, "target_audience")
        validated.timeline = self._field_from_value(output.timeline, "timeline")
        validated.design_system_preference = self._field_from_value(
            output.design_system_preference, "design_system_preference"
        )
        validated.special_requirements = [
            self._field_from_value(req, "special_requirement")
            for req in output.special_requirements
            if req
        ]
        validated.special_requirements = [s for s in validated.special_requirements if s]

        validated.clarification = self._build_clarification(validated)
        return validated

    def _build_clarification(self, validated: ValidatedIntent) -> ClarificationRequest | None:
        missing_fields: list[str] = []
        low_confidence_fields: list[str] = []

        for field_name in _REQUIRED_FIELDS:
            field = getattr(validated, field_name)
            if field is None:
                missing_fields.append(field_name)
            elif isinstance(field, RecognizedField) and field.confidence < self.confidence_threshold:
                low_confidence_fields.append(field_name)

        if not missing_fields and not low_confidence_fields:
            return None

        question_parts: list[str] = []
        for field_name in missing_fields + low_confidence_fields:
            question = _CLARIFICATION_QUESTIONS.get(field_name)
            if question:
                question_parts.append(question)

        return ClarificationRequest(
            needs_clarification=True,
            missing_fields=missing_fields,
            low_confidence_fields=low_confidence_fields,
            clarification_question="\n".join(question_parts) if question_parts else "能否补充一下上述信息？",
        )

    def merge_context(
        self,
        validated: ValidatedIntent,
        previous: ValidatedIntent | None,
    ) -> ValidatedIntent:
        """用上一轮的意图补全当前轮缺失的字段。"""
        if previous is None:
            return validated

        inherit_fields = [
            "space_type",
            "style",
            "color_preference",
            "brand_positioning",
            "design_system_preference",
            "target_audience",
            "timeline",
        ]
        for field_name in inherit_fields:
            current = getattr(validated, field_name)
            prev = getattr(previous, field_name)
            if current is None and prev is not None:
                setattr(validated, field_name, prev)

        for field_name in ("material_restrictions", "allowed_materials", "special_requirements", "points"):
            current = getattr(validated, field_name)
            prev = getattr(previous, field_name)
            if not current and prev:
                setattr(validated, field_name, prev)

        # 重新评估澄清需求
        validated.clarification = self._build_clarification(validated)
        return validated

    def apply_defaults(self, validated: ValidatedIntent) -> ValidatedIntent:
        """根据空间类型应用默认点位等默认值。"""
        defaults = self.taxonomy.field_defaults
        space_type_value = validated.space_type.value if validated.space_type else None

        points_default = (
            defaults.get("points", {})
            .get("default_by_space_type", {})
            .get(space_type_value)
        )
        if points_default and not validated.points:
            validated.points = [
                RecognizedField(
                    name="point",
                    value=point,
                    source=FieldSource.DEFAULT,
                    confidence=0.6,
                    raw_text=str(point),
                )
                for point in points_default
            ]

        if validated.timeline is None and defaults.get("timeline", {}).get("default_value"):
            validated.timeline = RecognizedField(
                name="timeline",
                value=defaults["timeline"]["default_value"],
                source=FieldSource.DEFAULT,
                confidence=0.5,
                raw_text=str(defaults["timeline"]["default_value"]),
            )

        # 重新评估澄清需求
        validated.clarification = self._build_clarification(validated)
        return validated
