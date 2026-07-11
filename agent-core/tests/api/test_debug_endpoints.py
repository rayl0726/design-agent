from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_intent_traces_returns_empty_for_unknown_project():
    response = client.get("/api/v1/debug/intent-traces/nonexistent-project")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "nonexistent-project"
    assert data["traces"] == []


def test_get_intent_trace_returns_404_for_unknown_trace():
    response = client.get("/api/v1/debug/intent-traces/some-project/nonexistent-trace-id")
    assert response.status_code == 404
