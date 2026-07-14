import pytest
from unittest.mock import AsyncMock, patch
from app.tools.invoke_meichen_workflow import InvokeMeichenWorkflowTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_invoke_meichen_workflow():
    tool = InvokeMeichenWorkflowTool()
    ctx = ToolContext(conversation_id="c1", agent_type="meichen", working_memory={})
    with patch("app.agents.meichen.workflow.run_meichen_workflow", new_callable=AsyncMock) as mock:
        mock.return_value = {"l2_output": {"ideas": []}}
        result = await tool.execute({"theme": "海洋", "space_type": "购物中心中庭", "budget": "15万"}, ctx)
        assert "l2_output" in result.data
