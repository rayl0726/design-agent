from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.intent_recognition_result import ValidatedIntent
from app.services.intent_schemas import IntentOutput


class IntentTraceRecorder:
    def __init__(self, base_dir: str | Path = "agent-core/data/intent_traces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.base_dir / f"{date_str}.jsonl"

    def _serialize_output(self, output: IntentOutput | None) -> dict[str, Any] | None:
        if output is None:
            return None
        return output.model_dump()

    def _dump_validated(
        self, validated: ValidatedIntent | dict[str, Any]
    ) -> dict[str, Any]:
        if hasattr(validated, "model_dump"):
            return validated.model_dump()
        return validated

    async def record(
        self,
        *,
        trace_id: str | None = None,
        project_id: str | None,
        input_text: str,
        llm_output: IntentOutput | None,
        rule_output: IntentOutput | None,
        merged_output: IntentOutput | None,
        validated: ValidatedIntent | dict[str, Any],
    ) -> str:
        trace_id = trace_id or str(uuid.uuid4())
        record = {
            "trace_id": trace_id,
            "project_id": project_id,
            "input_text": input_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "llm_output": self._serialize_output(llm_output),
            "rule_output": self._serialize_output(rule_output),
            "merged_output": self._serialize_output(merged_output),
            "validated": self._dump_validated(validated),
        }
        path = self._file_path()

        def _append() -> None:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        await asyncio.to_thread(_append)
        return trace_id

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict[str, Any]]:
        paths = sorted(self.base_dir.glob("*.jsonl"), reverse=True)

        def _read() -> list[dict[str, Any]]:
            local: list[dict[str, Any]] = []
            for path in paths:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        if record.get("project_id") == project_id:
                            local.append(record)
                if len(local) >= limit:
                    break
            return local[:limit]

        return await asyncio.to_thread(_read)

    async def get_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        paths = sorted(self.base_dir.glob("*.jsonl"), reverse=True)

        def _find() -> dict[str, Any] | None:
            for path in paths:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        if record.get("trace_id") == trace_id:
                            return record
            return None

        return await asyncio.to_thread(_find)
