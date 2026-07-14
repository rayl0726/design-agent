import asyncio

from app.runtime.tool import BaseTool, ToolResult
from app.services import knowledge_base as kb


class KnowledgeRetrievalTool(BaseTool):
    name = "knowledge_retrieval"
    description = "从本地知识库检索相关案例或专业知识"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }

    async def execute(self, inputs, context):
        try:
            results = await kb.search(
                query=inputs["query"],
                agent_type=context.agent_type,
                top_k=inputs.get("top_k", 5),
            )
        except asyncio.TimeoutError:
            results = []
        return ToolResult(
            observation=f"检索到 {len(results)} 条结果",
            data={"results": results}
        )
