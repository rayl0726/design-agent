from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_preview_prompt():
    response = client.post("/api/v1/prompt-preview", json={
        "theme": "圣诞节",
        "space_type": "购物中心中庭",
        "budget_level": "high",
        "style": "现代简约",
    })
    assert response.status_code == 200
    data = response.json()
    assert "positive" in data
    assert "negative" in data
    assert "shopping_mall_atrium" in data["template_version"]
