"""Tests for admin metrics endpoints."""
import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def trace_data(tmp_path):
    """Create temporary trace files for testing."""
    trace_file = tmp_path / "2026-07-12.jsonl"
    records = [
        {
            "trace_id": "t1",
            "project_id": "p1",
            "timestamp": "2026-07-12T10:00:00+00:00",
            "validated": {
                "space_type": {"name": "space_type", "value": "office", "source": "llm", "confidence": 0.9},
                "style": {"name": "style", "value": "modern", "source": "exact", "confidence": 0.95},
            },
            "llm_output": {"space_type": "office"},
            "merged_output": {"space_type": "office"},
        },
        {
            "trace_id": "t2",
            "project_id": "p2",
            "timestamp": "2026-07-12T11:00:00+00:00",
            "validated": {
                "space_type": {"name": "space_type", "value": "retail", "source": "alias", "confidence": 0.5},
                "style": {"name": "style", "value": "minimalist", "source": "fuzzy", "confidence": 0.6},
            },
            "llm_output": {"space_type": "shop"},
            "merged_output": {"space_type": "retail"},
        },
    ]
    with trace_file.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return tmp_path


def test_intent_traces_stats(trace_data):
    from app.api.endpoints.admin_metrics import router

    app = FastAPI()
    app.include_router(router)

    with patch("app.api.endpoints.admin_metrics._get_trace_dir", return_value=trace_data):
        client = TestClient(app)
        response = client.get("/api/v1/admin/intent-traces/stats?days=30")

    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "confidence" in data
    assert "lowConfidenceRate" in data
    # 4 field sources across 2 traces
    total_sources = sum(s["count"] for s in data["sources"])
    assert total_sources == 4


def test_intent_traces_correction_stats(trace_data):
    from app.api.endpoints.admin_metrics import router

    app = FastAPI()
    app.include_router(router)

    with patch("app.api.endpoints.admin_metrics._get_trace_dir", return_value=trace_data):
        client = TestClient(app)
        response = client.get("/api/v1/admin/intent-traces/correction-stats?days=30")

    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    # space_type was corrected in trace t2 (llm_output: "shop" -> validated: "retail")
    space_type_field = next(f for f in data["fields"] if f["field"] == "space_type")
    assert space_type_field["correctionCount"] >= 1


def test_intent_traces_handles_null_llm_output(tmp_path):
    """Real traces may have llm_output=null when LLM was not called."""
    trace_file = tmp_path / "2026-07-12.jsonl"
    record = {
        "trace_id": "t-null",
        "project_id": "p1",
        "timestamp": "2026-07-12T10:00:00+00:00",
        "validated": {
            "space_type": {"name": "space_type", "value": "office", "source": "llm", "confidence": 0.9},
        },
        "llm_output": None,
        "merged_output": None,
    }
    with trace_file.open("w") as f:
        f.write(json.dumps(record) + "\n")

    from app.api.endpoints.admin_metrics import router

    app = FastAPI()
    app.include_router(router)

    with patch("app.api.endpoints.admin_metrics._get_trace_dir", return_value=tmp_path):
        client = TestClient(app)
        # Both endpoints must not crash on null llm_output
        r_stats = client.get("/api/v1/admin/intent-traces/stats?days=30")
        r_corr = client.get("/api/v1/admin/intent-traces/correction-stats?days=30")

    assert r_stats.status_code == 200
    assert r_corr.status_code == 200
    # No correction recorded when llm_output is null
    corr_data = r_corr.json()
    space_type_field = next(f for f in corr_data["fields"] if f["field"] == "space_type")
    assert space_type_field["correctionCount"] == 0
    assert space_type_field["totalRecognitions"] == 1
