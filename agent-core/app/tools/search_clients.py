from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 已知广告域名黑名单（可扩展）
_AD_DOMAINS = {
    "e.baidu.com",
    "mingxuan.net",
    "tuiguang.baidu.com",
}


def _normalize_url(url: str) -> str:
    """去掉 scheme、www、尾部斜杠、查询参数，用于去重比较。"""
    url = url.strip().lower()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    url = url.split("?", 1)[0].split("#", 1)[0]
    return url.rstrip("/")


def _jaccard_similarity(a: str, b: str) -> float:
    """基于 2-gram 的 Jaccard 相似度。"""

    def _bigrams(text: str) -> set[str]:
        text = re.sub(r"\s+", "", text)
        return {text[i : i + 2] for i in range(max(0, len(text) - 1))}

    set_a = _bigrams(a)
    set_b = _bigrams(b)
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def is_ad_result(result: dict[str, Any]) -> bool:
    """判断一条结果是否为广告。"""
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    link = result.get("link", "").lower()

    # 文本标记
    if "广告" in title or "推广" in title or "广告" in snippet or "推广" in snippet:
        return True

    # 域名黑名单
    try:
        parsed = urllib.parse.urlparse(link)
        if parsed.netloc in _AD_DOMAINS:
            return True
    except Exception:
        pass

    return False


def deduplicate_results(results: list[dict[str, Any]], title_threshold: float = 0.6) -> list[dict[str, Any]]:
    """URL 去重 + 标题相似度去重，保留原始顺序。"""
    out: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for r in results:
        if is_ad_result(r):
            continue
        norm = _normalize_url(r.get("link", ""))
        if not norm or norm in seen_urls:
            continue
        title = r.get("title", "")
        if any(_jaccard_similarity(title, seen_title) > title_threshold for seen_title in seen_titles):
            continue
        seen_urls.add(norm)
        seen_titles.append(title)
        out.append(r)

    return out


class BingSearchClient:
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

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(query)
        url = f"https://cn.bing.com/search?q={encoded}"
        resp = await self.client.get(url, follow_redirects=True)
        resp.raise_for_status()
        results = self._parse(resp.text)[:limit]
        for r in results:
            r["source"] = "bing"
        return results

    def _parse(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select(".b_algo"):
            title_tag = item.select_one("h2 a")
            snippet_tag = item.select_one(".b_caption p") or item.select_one("p")
            if not title_tag:
                continue
            results.append({
                "title": title_tag.get_text(strip=True),
                "link": title_tag.get("href", ""),
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
            })
        return results


class BaiduSearchClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Cookie": "BAIDUID=BAIDUID=1234567890ABCDEF:FG=1",
            },
        )

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(query)
        url = f"https://www.baidu.com/s?wd={encoded}"
        resp = await self.client.get(url, follow_redirects=True)
        resp.raise_for_status()
        results = self._parse(resp.text)[:limit]
        for r in results:
            r["source"] = "baidu"
        return results

    def _parse(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        # 百度结果常见容器：.result、.c-container
        for item in soup.select(".result, .c-container"):
            # 跳过广告节点
            if item.get("data-tuiguang") or "ec_" in " ".join(item.get("class", [])):
                continue
            title_tag = item.select_one("h3 a, .t a")
            if not title_tag:
                continue
            link = title_tag.get("href", "")
            if link.startswith("http://www.baidu.com/link?") or link.startswith("/link?"):
                # 需要后续解析真实地址；为简化先尝试取 text 中的显式链接
                link = self._extract_real_link(item) or link
            snippet_tag = item.select_one(".content-right_8ZsVx, .c-abstract, .content-right")
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            candidate = {"title": title, "link": link, "snippet": snippet}
            if is_ad_result(candidate):
                continue
            results.append(candidate)
        return results

    def _extract_real_link(self, item) -> str | None:
        # 有些百度结果在摘要里直接写了真实链接
        text = item.get_text(" ", strip=True)
        match = re.search(r"https?://[^\s<>\"']+", text)
        if match:
            return match.group(0)
        return None
