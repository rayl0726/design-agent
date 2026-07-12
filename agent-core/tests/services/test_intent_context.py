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
