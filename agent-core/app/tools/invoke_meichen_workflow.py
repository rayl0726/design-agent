from app.runtime.tool import BaseTool, ToolResult
from app.agents.meichen import workflow as meichen_workflow


class InvokeMeichenWorkflowTool(BaseTool):
    name = "invoke_meichen_workflow"
    description = "当用户需要美陈设计方案时调用，启动完整的美陈设计工作流"
    parameters = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "space_type": {"type": "string"},
            "budget": {"type": "string"},
            "target_level": {"type": "string", "default": "L2"},
            "style": {"type": "string"},
            "material_restrictions": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["theme", "space_type", "budget"]
    }

    async def execute(self, inputs, context):
        result = await meichen_workflow.run_meichen_workflow(inputs)
        return ToolResult(
            observation="美陈工作流已完成",
            data=result
        )
