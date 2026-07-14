from app.runtime.tool import BaseTool, ToolResult


class RespondToUserTool(BaseTool):
    name = "respond_to_user"
    description = "任务完成，向用户返回最终答案"
    parameters = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "payload": {"type": "object"}
        }
    }

    async def execute(self, inputs, context):
        return ToolResult(
            observation="返回最终答案",
            data={"answer": inputs.get("answer", ""), "payload": inputs.get("payload", {})}
        )
