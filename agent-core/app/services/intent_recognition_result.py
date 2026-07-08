from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldSource(str, Enum):
    EXACT = "exact"
    ALIAS = "alias"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    LLM = "llm"
    DEFAULT = "default"
    UNKNOWN = "unknown"


class RecognizedField(BaseModel):
    name: str
    value: Any
    source: FieldSource = FieldSource.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    candidates: list[tuple[str, float]] = Field(default_factory=list)
    raw_text: str = ""

    def is_confident(self, threshold: float = 0.75) -> bool:
        return self.confidence >= threshold


class IntentRecognitionResult(BaseModel):
    space_type: RecognizedField | None = None
    budget: RecognizedField | None = None
    budget_level: RecognizedField | None = None
    theme: RecognizedField | None = None
    style: RecognizedField | None = None
    target_audience: RecognizedField | None = None
    timeline: RecognizedField | None = None
    material_restrictions: list[RecognizedField] = Field(default_factory=list)
    special_requirements: list[RecognizedField] = Field(default_factory=list)
    color_preference: RecognizedField | None = None
    brand_positioning: RecognizedField | None = None
    design_system_preference: RecognizedField | None = None
    points: list[RecognizedField] = Field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ClarificationRequest(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    low_confidence_fields: list[str] = Field(default_factory=list)
    message: str = ""
