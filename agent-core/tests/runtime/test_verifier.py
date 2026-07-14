import pytest
from app.runtime.verifier import Verifier
from app.runtime.models import Task


@pytest.mark.asyncio
async def test_information_gathering_verifier():
    v = Verifier()
    task = Task(id="t1", goal="gather", required_fields=["theme", "space_type", "budget"])
    result = {"theme": "海洋", "space_type": "购物中心中庭", "budget": "15万"}
    ev = await v.evaluate(task, result)
    assert ev.confidence == 1.0
    assert ev.suggested_action == "accept"


@pytest.mark.asyncio
async def test_missing_field_verifier():
    v = Verifier()
    task = Task(id="t1", goal="gather", required_fields=["theme", "space_type", "budget"])
    result = {"theme": "海洋"}
    ev = await v.evaluate(task, result)
    assert ev.confidence < 1.0
    assert ev.suggested_action == "ask_user"
