from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.runtime.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for up-to-date information when the user's question "
        "involves current events, real-time data, or facts that may change over time."
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

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    async def execute(self, inputs: dict[str, Any], context: ToolContext) -> ToolResult:
        query = inputs.get("query", "").strip()
        if not query:
            return ToolResult(observation="Empty query", data={"results": []})

        logger.info("Web search start: query=%s", query)
        encoded = urllib.parse.quote(query)
        url = f"https://cn.bing.com/search?q={encoded}"

        try:
            resp = await self.client.get(url, follow_redirects=True)
            resp.raise_for_status()
            results = self._parse_results(resp.text)
            logger.info("Web search done: query=%s, results=%d", query, len(results))
            summary = self._format_summary(results)
            return ToolResult(
                observation=summary,
                data={"query": query, "results": results},
            )
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return ToolResult(
                observation=f"搜索失败：{type(e).__name__}: {e}",
                data={"query": query, "results": [], "error": str(e)},
            )

    def _parse_results(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select(".b_algo"):
            title_tag = item.select_one("h2 a")
            snippet_tag = item.select_one(".b_caption p") or item.select_one("p")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            results.append({"title": title, "link": link, "snippet": snippet})
        return results[:5]

    def _format_summary(self, results: list[dict[str, str]]) -> str:
        if not results:
            return "未找到相关网页结果。"
        lines = ["搜索结果："]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   链接：{r['link']}")
        return "\n".join(lines)
