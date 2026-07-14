import asyncio

import pytest
from unittest.mock import AsyncMock, patch
from app.tools.knowledge_retrieval import KnowledgeRetrievalTool
from app.tools.image_generation import ImageGenerationTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_knowledge_retrieval_tool():
    tool = KnowledgeRetrievalTool()
    ctx = ToolContext(conversation_id="c1", agent_type="meichen", working_memory={})
    with patch("app.services.knowledge_base.search", new_callable=AsyncMock) as mock:
        mock.return_value = [{"title": "case"}]
        result = await tool.execute({"query": "海洋主题美陈"}, ctx)
        assert len(result.data["results"]) == 1


@pytest.mark.asyncio
async def test_knowledge_retrieval_tool_timeout():
    tool = KnowledgeRetrievalTool()
    ctx = ToolContext(conversation_id="c1", agent_type="meichen", working_memory={})
    with patch("app.services.knowledge_base.search", new_callable=AsyncMock) as mock:
        mock.side_effect = asyncio.TimeoutError
        result = await tool.execute({"query": "海洋主题美陈"}, ctx)
        assert result.data["results"] == []


@pytest.mark.asyncio
async def test_image_generation_tool():
    tool = ImageGenerationTool()
    ctx = ToolContext(conversation_id="c1", agent_type="meichen", working_memory={})
    with patch("app.services.image_generation.generate_image", new_callable=AsyncMock) as mock:
        mock.return_value = {"url": "http://example.com/img.png"}
        result = await tool.execute({"theme": "海洋", "space_type": "购物中心中庭"}, ctx)
        assert "url" in result.data
