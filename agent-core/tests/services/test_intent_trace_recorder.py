import pytest

from app.services.intent_trace_recorder import IntentTraceRecorder


@pytest.mark.asyncio
async def test_record_and_retrieve(tmp_path):
    recorder = IntentTraceRecorder(base_dir=tmp_path)
    await recorder.record(
        trace_id="t1",
        project_id="p1",
        input_text="情人节",
        llm_output=None,
        rule_output=None,
        merged_output=None,
        validated={"theme": "情人节"},
    )
    traces = await recorder.list_by_project("p1")
    assert len(traces) == 1
    assert traces[0]["input_text"] == "情人节"
