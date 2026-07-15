import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import router
from app.runtime.tool import ToolResult
from app.services.llm_client import LLMResponse


app = FastAPI()
app.include_router(router)


def test_generic_run_sse_includes_tool_progress(monkeypatch):
    """路由层 SSE 应包含 tool_progress 事件，且 id 与 tool_start 一致。"""
    import app.api.routers as routers

    captured = {}

    class FakeProvider:
        model = "fake"
        base_url = "http://test"
        api_key = "key"

        def __init__(self):
            self.client = self

        async def post(self, url, json, headers, timeout):
            class Resp:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"choices": [{"message": {"content": "ok"}}]}

            return Resp()

    class FakeLLMClient:
        primary_provider = FakeProvider()

        async def chat(self, system_prompt, user_prompt, tools=None, temperature=0.7):
            return LLMResponse(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query":"x"}',
                        },
                    }
                ],
            )

    class FakeWebSearch:
        async def execute(self, arguments, context):
            captured["emit"] = context.emit
            captured["tool_call_id"] = context.tool_call_id
            await context.emit("tool_progress", {"status": "summarizing"})
            return ToolResult(observation="summary")

    monkeypatch.setattr(routers, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(routers, "WebSearchTool", FakeWebSearch)

    client = TestClient(app)
    resp = client.post(
        "/agents/generic/run",
        json={"conversationId": "c1", "userInput": "x"},
    )

    assert resp.status_code == 200
    body = resp.text
    assert "event: tool_progress" in body
    assert '"status": "summarizing"' in body
    assert '"id": "call-1"' in body
    assert captured["emit"] is not None
    assert captured["tool_call_id"] == "call-1"


def test_generic_run_sse_emits_tool_result_on_tool_exception(monkeypatch):
    """web_search.execute 抛异常时，SSE 仍应发送 tool_result 事件并携带相同 id。"""
    import app.api.routers as routers

    class FakeProvider:
        model = "fake"
        base_url = "http://test"
        api_key = "key"

        def __init__(self):
            self.client = self

        async def post(self, url, json, headers, timeout):
            class Resp:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"choices": [{"message": {"content": "ok"}}]}

            return Resp()

    class FakeLLMClient:
        primary_provider = FakeProvider()

        async def chat(self, system_prompt, user_prompt, tools=None, temperature=0.7):
            return LLMResponse(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query":"x"}',
                        },
                    }
                ],
            )

    class FakeWebSearch:
        async def execute(self, arguments, context):
            raise RuntimeError("search failed")

    monkeypatch.setattr(routers, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(routers, "WebSearchTool", FakeWebSearch)

    client = TestClient(app)
    resp = client.post(
        "/agents/generic/run",
        json={"conversationId": "c1", "userInput": "x"},
    )

    assert resp.status_code == 200
    body = resp.text
    assert "event: tool_result" in body
    assert '"id": "call-1"' in body
    assert "工具调用失败" in body
