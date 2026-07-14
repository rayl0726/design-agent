from app.runtime.tool import BaseTool, ToolResult


class AskUserTool(BaseTool):
    name = "ask_user"
    description = "当信息不足时向用户提出澄清问题"
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "要问用户的问题"}
        },
        "required": ["question"]
    }

    async def execute(self, inputs, context):
        return ToolResult(
            observation="向用户提问",
            data={"question": inputs["question"], "requires_user_input": True}
        )
