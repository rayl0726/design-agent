from __future__ import annotations

import pytest

from app.services.intent_recognition_result import FieldSource
from app.services.intent_schemas import IntentOutput
from app.services.intent_validator import (
    IntentValidator,
    normalize_budget,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (300000, 300000),
        (30, 300000),
        ("30万", 300000),
        ("300k", 300000),
        ("二十万到三十万", 250000),
        ("20万-30万", 250000),
        ("15万", 150000),
        ("5千", 5000),
        ("5000元", 5000),
    ],
)
def test_normalize_budget(value, expected: int) -> None:
    assert normalize_budget(value) == expected


def test_validator_maps_closed_fields() -> None:
    validator = IntentValidator()
    output = IntentOutput(space_type="商场中庭", style="国潮", points=["门头", "打卡点"])
    result = validator.validate(output, "商场中庭国潮风格，门头打卡点")

    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"
    assert result.space_type.source == FieldSource.VALIDATED

    assert result.style is not None
    assert result.style.value == "国潮"

    point_names = [str(p.value) for p in result.points]
    assert "门头" in point_names
    assert "DP点" in point_names


def test_validator_preserves_unknown_values() -> None:
    validator = IntentValidator()
    output = IntentOutput(space_type="火星商业空间站")
    result = validator.validate(output, "火星商业空间站")
    assert result.space_type is not None
    assert result.space_type.value == "火星商业空间站"
    assert result.space_type.confidence == 0.6


def test_validator_normalizes_budget() -> None:
    validator = IntentValidator()
    output = IntentOutput(budget="30万")
    result = validator.validate(output, "预算30万")
    assert result.budget is not None
    assert result.budget.value == 300000
    assert result.budget_level is not None
    assert result.budget_level.value == "high"


def test_validator_triggers_clarification() -> None:
    validator = IntentValidator()
    output = IntentOutput()
    result = validator.validate(output, "做个美陈")
    assert result.clarification is not None
    assert result.clarification.needs_clarification is True
    assert "space_type" in result.clarification.missing_fields
    assert "budget" in result.clarification.missing_fields
    assert "theme" in result.clarification.missing_fields


def test_validator_inherits_context() -> None:
    validator = IntentValidator()
    previous = validator.validate(
        IntentOutput(space_type="购物中心中庭", style="国潮", color_preference="红色"),
        "",
    )
    current = validator.validate(IntentOutput(budget="50万"), "预算加到50万")
    merged = validator.merge_context(current, previous)

    assert merged.space_type is not None
    assert merged.space_type.value == "购物中心中庭"
    assert merged.style is not None
    assert merged.style.value == "国潮"
    assert merged.budget is not None
    assert merged.budget.value == 500000
