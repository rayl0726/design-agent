from app.runtime.tool import BaseTool, ToolResult
from app.services import image_generation as image_generation_service


class ImageGenerationTool(BaseTool):
    name = "image_generation"
    description = "根据设计概念生成效果图"
    parameters = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "space_type": {"type": "string"},
            "design_point": {"type": "string"},
            "camera_angle": {"type": "string"},
            "style": {"type": "string"},
            "negative_prompts": {"type": "array", "items": {"type": "string"}}
        }
    }

    async def execute(self, inputs, context):
        result = await image_generation_service.generate_image(inputs)
        return ToolResult(
            observation="图片生成完成",
            data=result
        )
