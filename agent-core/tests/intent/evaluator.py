from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_recognition_result import IntentRecognitionResult

GOLDEN_CASES_PATH = Path(__file__).parent / "golden_cases.jsonl"


def load_cases(path: Path = GOLDEN_CASES_PATH) -> list[dict[str, Any]]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


async def evaluate(service: IntentRecognitionService | None = None) -> dict[str, Any]:
    service = service or IntentRecognitionService()
    cases = load_cases()
    total = len(cases)
    passed = 0
    failures: list[dict[str, Any]] = []

    for case in cases:
        result = await service.recognize(case["input"])
        ok, details = _check_case(case, result)
        if ok:
            passed += 1
        else:
            failures.append({"input": case["input"], "expected": case["expected"], "got": details})

    return {
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "failures": failures,
    }


def _check_case(case: dict[str, Any], result: IntentRecognitionResult) -> tuple[bool, dict[str, Any]]:
    expected = case["expected"]
    details: dict[str, Any] = {}
    all_ok = True

    if "space_type" in expected:
        got = result.space_type.value if result.space_type else None
        details["space_type"] = got
        if got != expected["space_type"]:
            all_ok = False

    if "budget" in expected:
        got = result.budget.value if result.budget else None
        details["budget"] = got
        if got != expected["budget"]:
            all_ok = False

    if "budget_level" in expected:
        got = result.budget_level.value if result.budget_level else None
        details["budget_level"] = got
        if got != expected["budget_level"]:
            all_ok = False

    if "style" in expected:
        got = result.style.value if result.style else None
        details["style"] = got
        if got != expected["style"]:
            all_ok = False

    if "points" in expected:
        got = sorted([p.value for p in result.points], key=lambda x: x.get("name", ""))
        details["points"] = got
        expected_sorted = sorted(expected["points"], key=lambda x: x.get("name", ""))
        if got != expected_sorted:
            all_ok = False

    return all_ok, details


if __name__ == "__main__":
    import asyncio

    report = asyncio.run(evaluate())
    print(json.dumps(report, ensure_ascii=False, indent=2))
