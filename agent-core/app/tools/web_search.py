from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.runtime.tool import BaseTool, ToolContext, ToolResult
from app.services.llm_client import LLMClient
from app.tools.search_clients import (
    BingSearchClient,
    BaiduSearchClient,
    deduplicate_results,
    is_ad_result,
    _normalize_url,
)
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
            return ToolResult(observation="查询词为空", data={"results": []})

        logger.info("Web search start: query=%s", query)

        # 1. 并行搜索 Bing + Baidu，使用更大的 limit 以提高过滤后仍保留至少 3 条结果的概率
        search_limit = max(_MAX_RESULTS * 3, 10)
        source_results, failed_sources = await self._safe_gather(
            {
                "bing": self.bing_client.search(query, limit=search_limit),
                "baidu": self.baidu_client.search(query, limit=search_limit),
            }
        )

        bing_results = source_results.get("bing", [])
        baidu_results = source_results.get("baidu", [])
        raw_results = bing_results + baidu_results
        logger.info(
            "Raw results: bing=%d, baidu=%d, failed=%s",
            len(bing_results),
            len(baidu_results),
            failed_sources,
        )

        # 2. 去重 + 取 Top N；如果去重后不足 _MAX_RESULTS，尝试从原始结果中补充非广告、不重复的条目
        deduped = deduplicate_results(raw_results)
        if len(deduped) < _MAX_RESULTS:
            seen_links = {_normalize_url(r.get("link", "")) for r in deduped}
            for r in raw_results:
                if len(deduped) >= _MAX_RESULTS:
                    break
                link = r.get("link", "")
                norm = _normalize_url(link)
                if not norm or norm in seen_links:
                    continue
                if is_ad_result(r):
                    continue
                seen_links.add(norm)
                deduped.append(r)
        deduped = deduped[:_MAX_RESULTS]
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

        # 4. 抓取正文（使用 10s 超时）
        fetched = await self.fetcher(
            deduped,
            client=self.client,
            max_pages=_MAX_RESULTS,
            timeout=10.0,
        )

        # 5. LLM 摘要
        llm_client = LLMClient()
        summary = await self.summarizer(query, fetched, llm_client)

        # 6. 若某个搜索源失败，在摘要中说明结果仅来自可用源
        if failed_sources:
            summary = self._prepend_source_note(failed_sources, summary)

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

    async def _safe_gather(
        self, sources: dict[str, Any]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
        """并发执行多个搜索源，分别捕获异常并记录失败的源。"""
        results = await asyncio.gather(*sources.values(), return_exceptions=True)
        out: dict[str, list[dict[str, Any]]] = {}
        failed: list[str] = []
        for (name, _), r in zip(sources.items(), results):
            if isinstance(r, Exception):
                logger.warning("Search source failed: %s - %s", name, r)
                failed.append(name)
                out[name] = []
            else:
                out[name] = r
        return out, failed

    def _prepend_source_note(self, failed_sources: list[str], summary: str) -> str:
        names = {"bing": "Bing", "baidu": "Baidu"}
        failed_names = [names.get(s, s) for s in failed_sources]
        available_names = [n for n in names.values() if n not in failed_names]
        if available_names:
            note = f"注：{'、'.join(failed_names)} 搜索源暂时不可用，本次结果仅来自 {available_names[0]}。"
        else:
            note = f"注：{'、'.join(failed_names)} 搜索源均不可用。"
        return note + "\n\n" + summary

    async def _emit(self, context: ToolContext, event: str, payload: dict[str, Any]) -> None:
        if context.emit is not None:
            if event == "tool_progress" and context.tool_call_id is not None:
                payload = {"id": context.tool_call_id, **payload}
            await context.emit(event, payload)
