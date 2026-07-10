from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.intent_trace_recorder import IntentTraceRecorder

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])
_recorder = IntentTraceRecorder()


@router.get("/intent-traces/{project_id}")
async def list_intent_traces(project_id: str, limit: int = Query(50, ge=1, le=200)):
    return {"project_id": project_id, "traces": await _recorder.list_by_project(project_id, limit=limit)}


@router.get("/intent-traces/{project_id}/{trace_id}")
async def get_intent_trace(project_id: str, trace_id: str):
    record = await _recorder.get_by_trace_id(trace_id)
    if record is None or record.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="not found")
    return record
