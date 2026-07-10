from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    async def record(
        self,
        *,
        trace_id: str | None = None,
        project_id: str | None,
        input_text: str,
        llm_output: IntentOutput | None,
        rule_output: IntentOutput | None,
        merged_output: IntentOutput | None,
        validated: Any,
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
            "validated": validated.model_dump() if hasattr(validated, "model_dump") else validated,
        }
        path = self._file_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return trace_id

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob("*.jsonl"), reverse=True):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("project_id") == project_id:
                        results.append(record)
            if len(results) >= limit:
                break
        return results[:limit]

    async def get_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        for path in sorted(self.base_dir.glob("*.jsonl"), reverse=True):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("trace_id") == trace_id:
                        return record
        return None
