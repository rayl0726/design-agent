from __future__ import annotations

from app.runtime.models import Task, Evaluation
from app.runtime.tool import ToolResult


class Verifier:
    async def evaluate(self, task: Task, result: dict | ToolResult) -> Evaluation:
        if isinstance(result, ToolResult):
            data = result.data
        else:
            data = result

        if task.type == "information_gathering" or task.required_fields:
            missing = [f for f in task.required_fields if f not in data or not data[f]]
            if not missing:
                return Evaluation(confidence=1.0, reason="All required fields present", suggested_action="accept")
            ratio = (len(task.required_fields) - len(missing)) / len(task.required_fields)
            return Evaluation(
                confidence=round(ratio, 2),
                reason=f"Missing fields: {missing}",
                suggested_action="ask_user" if ratio < 0.5 else "retry"
            )

        # Default: self-evaluation placeholder
        return Evaluation(confidence=0.90, reason="Default acceptable", suggested_action="accept")
