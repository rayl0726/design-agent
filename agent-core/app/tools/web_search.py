from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.runtime.tool import BaseTool, ToolContext, ToolResult
from app.services.llm_client import LLMClient
from app.tools.search_clients import BingSearchClient, BaiduSearchClient, deduplicate_results
from app.tools.web_fetcher import fetch_pages
from app.tools.web_summarizer import summarize

logger = logging.getLogger(__name__)

_MAX_RESULTS = 3


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web (Bing + Baidu) for up-to-date information. "
        "Fetches top pages and summarizes them in Chinese."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query in Chinese or English.",
            }
        },
        "required": ["query"],
    }

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        bing_client: BingSearchClient | None = None,
        baidu_client: BaiduSearchClient | None = None,
    ):
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        self.bing_client = bing_client or BingSearchClient(self.client)
        self.baidu_client = baidu_client or BaiduSearchClient(self.client)
        self.fetcher = fetch_pages
        self.summarizer = summarize

    async def execute(self, inputs: dict[str, Any], context: ToolContext) -> ToolResult:
        query = inputs.get("query", "").strip()
        if not query:
            return ToolResult(observation="Empty query", data={"results": []})

        logger.info("Web search start: query=%s", query)

        # 1. 并行搜索 Bing + Baidu
        bing_task = self.bing_client.search(query, limit=5)
        baidu_task = self.baidu_client.search(query, limit=5)
        bing_results, baidu_results = await self._safe_gather(bing_task, baidu_task)

        raw_results = bing_results + baidu_results
        logger.info("Raw results: bing=%d, baidu=%d", len(bing_results), len(baidu_results))

        # 2. 去重 + 取 Top N
        deduped = deduplicate_results(raw_results)[:_MAX_RESULTS]
        logger.info("Deduped results: %d", len(deduped))

        if not deduped:
            return ToolResult(
                observation="未找到有效搜索结果。",
                data={"query": query, "results": []},
            )

        # 3. 发送总结中状态
        await self._emit(
            context,
            "tool_progress",
            {"status": "summarizing", "detail": f"正在分析 {len(deduped)} 个网页"},
        )

        # 4. 抓取正文
        fetched = await self.fetcher(deduped, client=self.client, max_pages=_MAX_RESULTS)

        # 5. LLM 摘要
        llm_client = LLMClient()
        summary = await self.summarizer(query, fetched, llm_client)

        logger.info("Web search done: query=%s, summary_len=%d", query, len(summary))

        return ToolResult(
            observation=summary,
            data={
                "query": query,
                "results": [
                    {"title": r.get("title"), "link": r.get("link"), "source": r.get("source")}
                    for r in deduped
                ],
            },
        )

    async def _safe_gather(self, *awaitables):
        results = await asyncio.gather(*awaitables, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Search source failed: %s", r)
                out.append([])
            else:
                out.append(r)
        return out

    async def _emit(self, context: ToolContext, event: str, payload: dict[str, Any]) -> None:
        if context.emit is not None:
            if event == "tool_progress" and context.tool_call_id is not None:
                payload = {"id": context.tool_call_id, **payload}
            await context.emit(event, payload)
