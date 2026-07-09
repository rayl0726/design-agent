from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_alias_proposals():
    response = client.get("/api/v1/learning/alias-proposals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
