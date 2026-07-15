from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_MAX_CONTENT_LENGTH = 3000


async def fetch_pages(
    results: list[dict[str, Any]],
    client: httpx.AsyncClient | None = None,
    max_pages: int = 3,
    max_concurrent: int = 3,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """并发抓取搜索结果正文，失败时 fallback 到摘要。"""
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout))
    semaphore = asyncio.Semaphore(max_concurrent)
    targets = results[:max_pages]

    async def _fetch_one(result: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            title = result.get("title", "")
            link = result.get("link", "")
            snippet = result.get("snippet", "")
            try:
                resp = await client.get(link, follow_redirects=True, timeout=timeout)
                resp.raise_for_status()
                text = _extract_main_text(resp.text)
                if not text:
                    text = snippet
                return {
                    "title": title,
                    "link": link,
                    "text": text[:_MAX_CONTENT_LENGTH],
                    "used_snippet_fallback": False,
                }
            except Exception as e:
                logger.warning("Fetch failed for %s: %s", link, e)
                return {
                    "title": title,
                    "link": link,
                    "text": snippet[:_MAX_CONTENT_LENGTH],
                    "used_snippet_fallback": True,
                }

    return await asyncio.gather(*[_fetch_one(r) for r in targets])


def _extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 移除脚本、样式、导航、页脚、侧边栏
    for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
        tag.decompose()

    selectors = [
        "article",
        "main",
        '[role="main"]',
        ".post-content",
        ".article-content",
        ".content",
        "#content",
        ".detail",
        ".body",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text("\n", strip=True)
            if len(text) > 80:
                return text
    # fallback：取 body 内最长段落
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    if paragraphs:
        long_paragraphs = [p for p in paragraphs if len(p) > 20]
        if long_paragraphs:
            return "\n".join(long_paragraphs)
        return "\n".join(paragraphs)
    return soup.get_text("\n", strip=True)
