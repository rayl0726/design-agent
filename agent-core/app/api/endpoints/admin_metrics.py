"""Admin metrics endpoints for intent trace aggregation."""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-metrics"])

_TRACE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "intent_traces"

_CONFIDENCE_BUCKETS = [
    (0.0, 0.3, "0-0.3"),
    (0.3, 0.5, "0.3-0.5"),
    (0.5, 0.7, "0.5-0.7"),
    (0.7, 0.85, "0.7-0.85"),
    (0.85, 1.01, "0.85-1.0"),
]

_INTENT_FIELDS = ["space_type", "points", "budget", "style", "material_restrictions"]


def _get_trace_dir() -> Path:
    return _TRACE_DIR


def _read_traces(days: int) -> list[dict[str, Any]]:
    """Read JSONL trace files from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    trace_dir = _get_trace_dir()
    if not trace_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(trace_dir.glob("*.jsonl"), reverse=True):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ts = datetime.fromisoformat(record.get("timestamp", ""))
                    if ts >= cutoff:
                        records.append(record)
                except (json.JSONDecodeError, ValueError):
                    continue
    return records


def _extract_fields(validated: dict[str, Any]) -> list[tuple[str, str, float]]:
    """Extract (field_name, source, confidence) from validated intent."""
    result: list[tuple[str, str, float]] = []
    if not validated:
        return result
    for field_name in _INTENT_FIELDS:
        field_val = validated.get(field_name)
        if field_val is None:
            continue
        if isinstance(field_val, list):
            for item in field_val:
                if isinstance(item, dict):
                    result.append((
                        field_name,
                        item.get("source", "unknown"),
                        float(item.get("confidence", 0.0)),
                    ))
        elif isinstance(field_val, dict):
            result.append((
                field_name,
                field_val.get("source", "unknown"),
                float(field_val.get("confidence", 0.0)),
            ))
    return result


@router.get("/intent-traces/stats")
async def get_intent_trace_stats(days: int = Query(30, ge=1, le=365)):
    """Aggregate source distribution and confidence distribution from intent traces."""
    records = _read_traces(days)

    source_counter: Counter = Counter()
    confidence_counter: Counter = Counter()
    total_fields = 0
    low_confidence_count = 0

    for record in records:
        validated = record.get("validated", {})
        fields = _extract_fields(validated)
        for _field_name, source, confidence in fields:
            source_counter[source] += 1
            total_fields += 1
            if confidence < 0.7:
                low_confidence_count += 1
            for lo, hi, label in _CONFIDENCE_BUCKETS:
                if lo <= confidence < hi:
                    confidence_counter[label] += 1
                    break

    sources = [
        {"source": s, "count": c, "percentage": (c / total_fields * 100) if total_fields > 0 else 0.0}
        for s, c in source_counter.most_common()
    ]

    confidence = [
        {"bucket": label, "count": confidence_counter.get(label, 0),
         "percentage": (confidence_counter.get(label, 0) / total_fields * 100) if total_fields > 0 else 0.0}
        for _, _, label in _CONFIDENCE_BUCKETS
    ]

    return {
        "sources": sources,
        "confidence": confidence,
        "lowConfidenceRate": (low_confidence_count / total_fields) if total_fields > 0 else 0.0,
    }


@router.get("/intent-traces/correction-stats")
async def get_intent_trace_correction_stats(days: int = Query(30, ge=1, le=365)):
    """Aggregate per-field correction rates from intent traces."""
    records = _read_traces(days)

    field_stats: dict[str, dict[str, Any]] = {}

    for record in records:
        validated = record.get("validated", {}) or {}
        llm_output = record.get("llm_output", {}) or {}

        for field_name in _INTENT_FIELDS:
            if field_name not in field_stats:
                field_stats[field_name] = {
                    "total": 0,
                    "corrected": 0,
                    "corrections": Counter(),
                }

            field_val = validated.get(field_name)
            if field_val is None:
                continue

            field_stats[field_name]["total"] += 1

            # Get the validated value
            if isinstance(field_val, dict):
                validated_value = str(field_val.get("value", ""))
            elif isinstance(field_val, list):
                validated_value = str([item.get("value", "") if isinstance(item, dict) else str(item) for item in field_val])
            else:
                validated_value = str(field_val)

            # Get the LLM output value
            llm_value = str(llm_output.get(field_name, ""))

            # Check if corrected (LLM output differs from validated)
            if llm_value and llm_value != validated_value:
                field_stats[field_name]["corrected"] += 1
                field_stats[field_name]["corrections"][llm_value] += 1

    fields = []
    for field_name, stats in field_stats.items():
        total = stats["total"]
        corrected = stats["corrected"]
        top_corrected = [
            {"original": val, "count": cnt}
            for val, cnt in stats["corrections"].most_common(5)
        ]
        fields.append({
            "field": field_name,
            "totalRecognitions": total,
            "correctionCount": corrected,
            "correctionRate": (corrected / total * 100) if total > 0 else 0.0,
            "topCorrectedValues": top_corrected,
        })

    return {"fields": fields}
