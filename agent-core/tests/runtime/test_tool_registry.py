from app.runtime.tool import BaseTool, ToolContext, ToolResult
from app.runtime.tool_registry import ToolRegistry


class EchoTool(BaseTool):
    name = "echo"
    description = "Echoes input"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, inputs, context):
        return ToolResult(observation=inputs["text"], data=inputs)


def test_registry_descriptions():
    registry = ToolRegistry()
    registry.register(EchoTool())
    desc = registry.descriptions()
    assert "echo" in desc
    assert "Echoes input" in desc
