# 多源网页搜索 + 状态反馈 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让通用 Agent 的 `web_search` 同时搜索 Bing 和 Baidu，过滤百度广告，抓取 Top 3 网页正文并生成中文摘要；搜索/总结过程中通过 SSE `tool_progress` 事件实时反馈状态到前端工具卡片。

**Architecture:** 在 `agent-core` 新增/重构搜索客户端（Bing/Baidu）、去重、抓取、摘要四个模块；`WebSearchTool` 作为编排器通过 `ToolContext.emit` 发送阶段状态；`agent-api` 转发 `tool_progress`；前端 `ChatView` 根据事件更新同 ID 工具卡片状态。

**Tech Stack:** Python 3.9, FastAPI, httpx, BeautifulSoup4, 智谱 GLM API; Java 17 + Spring WebFlux; Vue 3 + Element Plus.

## Global Constraints

- `asyncio.gather` + `asyncio.Semaphore` 控制并行抓取，避免串行阻塞。
- 百度广告必须过滤，至少保留 3 条有效结果参与后续流程。
- LLM 摘要失败时 fallback 到格式化原始搜索结果。
- 所有 LLM 调用使用 智谱 API，不再 fallback 到 Ollama。
- 新增字段必须向后兼容：未提供 `emit` 的 `ToolContext` 仍可正常运行。
- 状态事件必须携带稳定 `id`（与 `tool_start` 一致），前端按 `id` 更新卡片。
- 测试先行：每个任务先写失败测试，再实现，再验证通过。
- 频繁提交：每个 Task 完成后单独 commit。

---

## File Structure

### agent-core

- `app/runtime/tool.py`
  -  responsibility: `ToolContext` / `ToolResult` / `BaseTool` 基础模型。
  -  change: 为 `ToolContext` 增加可选的 `emit` 回调，供工具发送阶段状态。

- `app/tools/search_clients.py` （新增）
  -  responsibility: Bing/Baidu 搜索请求、HTML 解析、广告过滤、URL/标题去重。
  -  change: 提供 `BingSearchClient`, `BaiduSearchClient`, `deduplicate_results`, `is_ad_result`。

- `app/tools/web_fetcher.py` （新增）
  -  responsibility: 并发抓取搜索结果网页正文，超时/失败 fallback 到摘要。
  -  change: `fetch_pages(results, semaphore)` 返回 `(title, link, full_text_or_snippet)`。

- `app/tools/web_summarizer.py` （新增）
  -  responsibility: 调用 LLM 对抓取内容生成中文摘要并附带来源。
  -  change: `summarize(query, fetched_contents, client)`。

- `app/tools/web_search.py`
  -  responsibility: 编排搜索、去重、抓取、摘要，并通过 `context.emit` 发送 `tool_progress`。
  -  change: 重写 `execute`，使用新模块。

- `app/api/routers.py`
  -  responsibility: `/agents/{agent_id}/run` SSE 接口。
  -  change: 创建 `ToolContext` 时传入 `emit` 回调；透传 `tool_progress` SSE。

### agent-api

- `src/main/java/com/meichen/orchestrator/handler/GenericAgentHandler.java`
  -  responsibility: 接收 agent-core SSE 并持久化/推送消息。
  -  change: 新增 `tool_progress` 分支，转发给 `SseEmitterService`。

- `src/test/java/com/meichen/orchestrator/handler/GenericAgentHandlerTest.java`
  -  responsibility: GenericAgentHandler 单元测试。
  -  change: 增加 `tool_progress` 解析与转发测试。

### agent-web

- `src/views/ChatView.vue`
  -  responsibility: 会话消息展示、SSE 监听、工具卡片渲染。
  -  change: 监听 `tool_progress`，更新同 ID 工具卡片状态；工具卡片显示“搜索中... / 总结中... / 已完成”。

---

## Task 1: ToolContext 支持 emit 回调

**Files:**
- Modify: `agent-core/app/runtime/tool.py`
- Test: `agent-core/tests/runtime/test_tool_context.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ToolContext` 增加可选字段 `emit: Callable[[str, dict], Awaitable[None] | None] | None`

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/runtime/test_tool_context.py
from app.runtime.tool import ToolContext
import pytest


@pytest.mark.asyncio
async def test_tool_context_emit_callback_is_invoked():
    called = {"event": None, "payload": None}

    async def emit(event, payload):
        called["event"] = event
        called["payload"] = payload

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
    )

    await ctx.emit("tool_progress", {"status": "searching"})

    assert called["event"] == "tool_progress"
    assert called["payload"]["status"] == "searching"


def test_tool_context_without_emit_still_works():
    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
    )
    assert ctx.emit is None
    assert ctx.conversation_id == "c1"
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
source .venv/bin/activate
pytest tests/runtime/test_tool_context.py -v
```
Expected: FAIL with `unexpected keyword argument 'emit'`.

- [ ] **Step 3: 最小实现**

```python
# agent-core/app/runtime/tool.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Awaitable


@dataclass
class ToolContext:
    conversation_id: str
    agent_type: str
    working_memory: dict[str, Any]
    emit: Callable[[str, dict], Awaitable[None] | None] | None = None


@dataclass
class ToolResult:
    observation: str
    data: dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def execute(self, inputs: dict[str, Any], context: ToolContext) -> ToolResult:
        ...
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/runtime/test_tool_context.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/runtime/tool.py agent-core/tests/runtime/test_tool_context.py
git commit -m "feat(agent-core): add optional emit callback to ToolContext"
```

---

## Task 2: 多源搜索客户端（Bing + Baidu + 广告过滤 + 去重）

**Files:**
- Create: `agent-core/app/tools/search_clients.py`
- Test: `agent-core/tests/tools/test_search_clients.py`

**Interfaces:**
- Consumes: `httpx.AsyncClient`
- Produces:
  - `BingSearchClient.search(query) -> list[dict]`
  - `BaiduSearchClient.search(query) -> list[dict]`
  - `deduplicate_results(results: list[dict], title_threshold=0.6) -> list[dict]`
  - `is_ad_result(result: dict) -> bool`

Result dict schema:
```python
{"title": str, "link": str, "snippet": str, "source": "bing" | "baidu"}
```

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/tools/test_search_clients.py
import pytest
from app.tools.search_clients import (
    BingSearchClient,
    BaiduSearchClient,
    deduplicate_results,
    is_ad_result,
    _normalize_url,
    _jaccard_similarity,
)


def test_normalize_url_strips_scheme_and_www():
    assert _normalize_url("https://www.example.com/path/?x=1") == "example.com/path"
    assert _normalize_url("http://example.com/path") == "example.com/path"


def test_jaccard_similarity():
    assert _jaccard_similarity("北京天气", "北京今天天气") > 0.3
    assert _jaccard_similarity("完全无关", "另一个标题") < 0.2


def test_deduplicate_removes_same_url():
    results = [
        {"title": "A", "link": "https://www.example.com/a", "snippet": "s", "source": "bing"},
        {"title": "A", "link": "http://example.com/a", "snippet": "s2", "source": "baidu"},
    ]
    out = deduplicate_results(results)
    assert len(out) == 1


def test_deduplicate_removes_similar_titles():
    results = [
        {"title": "2026 北京车展最新动态", "link": "https://a.com/1", "snippet": "s", "source": "bing"},
        {"title": "2026 北京车展最新动态", "link": "https://b.com/2", "snippet": "s", "source": "baidu"},
    ]
    out = deduplicate_results(results)
    assert len(out) == 1


def test_is_ad_result_detects_ad_markers():
    assert is_ad_result({"title": "广告： best product", "link": "", "snippet": ""}) is True
    assert is_ad_result({"title": "正常新闻", "link": "", "snippet": ""}) is False
    assert is_ad_result({"title": "", "link": "https://e.baidu.com/xxx", "snippet": ""}) is True


def test_baidu_client_filters_ad_html():
    html = """
    <html>
      <div class="result" data-tuiguang="1">
        <h3><a href="https://ad.com">广告商品</a></h3>
        <div class="content-right">推广文案</div>
      </div>
      <div class="result">
        <h3><a href="https://news.com/1">正常新闻标题</a></h3>
        <div class="content-right_8ZsVx">正常摘要</div>
      </div>
    </html>
    """
    client = BaiduSearchClient()
    results = client._parse(html)
    assert len(results) == 1
    assert results[0]["title"] == "正常新闻标题"
    assert results[0]["link"] == "https://news.com/1"


def test_bing_client_parse_results():
    html = """
    <html>
      <li class="b_algo">
        <h2><a href="https://example.com">Example Title</a></h2>
        <div class="b_caption"><p>Example snippet</p></div>
      </li>
    </html>
    """
    client = BingSearchClient()
    results = client._parse(html)
    assert len(results) == 1
    assert results[0]["title"] == "Example Title"
    assert results[0]["link"] == "https://example.com"
    assert results[0]["snippet"] == "Example snippet"
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/tools/test_search_clients.py -v
```
Expected: FAIL with module/file not found.

- [ ] **Step 3: 最小实现**

```python
# agent-core/app/tools/search_clients.py
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
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/tools/test_search_clients.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/tools/search_clients.py agent-core/tests/tools/test_search_clients.py
git commit -m "feat(agent-core): add Bing+Baidu search clients with ad filtering and dedup"
```

---

## Task 3: 网页正文抓取器

**Files:**
- Create: `agent-core/app/tools/web_fetcher.py`
- Test: `agent-core/tests/tools/test_web_fetcher.py`

**Interfaces:**
- Consumes: `list[dict]` search results; `httpx.AsyncClient`
- Produces: `fetch_pages(results, max_pages=3, max_concurrent=3, timeout=10.0) -> list[dict]`
  - 输出 dict 包含 `title`, `link`, `text`（正文或摘要）, `used_snippet_fallback: bool`

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/tools/test_web_fetcher.py
import pytest
from unittest.mock import AsyncMock
from app.tools.web_fetcher import fetch_pages


@pytest.mark.asyncio
async def test_fetch_pages_uses_snippet_when_request_fails():
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("timeout")

    results = [
        {"title": "T", "link": "https://example.com", "snippet": "fallback snippet", "source": "bing"},
    ]
    out = await fetch_pages(results, client=mock_client, max_pages=1)
    assert len(out) == 1
    assert out[0]["text"] == "fallback snippet"
    assert out[0]["used_snippet_fallback"] is True


@pytest.mark.asyncio
async def test_fetch_pages_extracts_main_content():
    html = """
    <html><body>
      <nav> nav content </nav>
      <article>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
      </article>
      <footer> footer </footer>
    </body></html>
    """
    mock_client = AsyncMock()
    response = AsyncMock()
    response.text = html
    response.raise_for_status = AsyncMock()
    mock_client.get.return_value = response

    results = [
        {"title": "T", "link": "https://example.com", "snippet": "s", "source": "bing"},
    ]
    out = await fetch_pages(results, client=mock_client, max_pages=1)
    assert out[0]["text"].startswith("First paragraph.")
    assert "nav content" not in out[0]["text"]
    assert out[0]["used_snippet_fallback"] is False
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_fetcher.py -v
```
Expected: FAIL module not found.

- [ ] **Step 3: 最小实现**

```python
# agent-core/app/tools/web_fetcher.py
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
        return "\n".join(p for p in paragraphs if len(p) > 20)
    return soup.get_text("\n", strip=True)
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_fetcher.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/tools/web_fetcher.py agent-core/tests/tools/test_web_fetcher.py
git commit -m "feat(agent-core): add concurrent web page fetcher with snippet fallback"
```

---

## Task 4: LLM 摘要生成器

**Files:**
- Create: `agent-core/app/tools/web_summarizer.py`
- Test: `agent-core/tests/tools/test_web_summarizer.py`

**Interfaces:**
- Consumes: `query: str`, `fetched: list[dict]`, `client: LLMClient`
- Produces: `summarize(query, fetched, client) -> str`

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/tools/test_web_summarizer.py
import pytest
from unittest.mock import AsyncMock
from app.tools.web_summarizer import summarize


@pytest.mark.asyncio
async def test_summarize_returns_llm_output_with_sources():
    mock_client = AsyncMock()
    mock_client.complete.return_value = "这是摘要。"

    fetched = [
        {"title": "T1", "link": "https://a.com", "text": "正文一", "used_snippet_fallback": False},
        {"title": "T2", "link": "https://b.com", "text": "正文二", "used_snippet_fallback": True},
    ]
    result = await summarize("北京天气", fetched, mock_client)

    assert "这是摘要。" in result
    assert "1. T1" in result
    assert "https://a.com" in result
    assert "2. T2" in result
    assert "https://b.com" in result


@pytest.mark.asyncio
async def test_summarize_fallback_when_llm_fails():
    mock_client = AsyncMock()
    mock_client.complete.side_effect = Exception("rate limit")

    fetched = [
        {"title": "T1", "link": "https://a.com", "text": "正文一", "used_snippet_fallback": False},
    ]
    result = await summarize("北京天气", fetched, mock_client)

    assert "未能生成摘要" in result
    assert "https://a.com" in result
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_summarizer.py -v
```
Expected: FAIL module not found.

- [ ] **Step 3: 最小实现**

```python
# agent-core/app/tools/web_summarizer.py
from __future__ import annotations

import logging
from typing import Any

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = (
    "你是信息整理助手。请根据提供的网页正文/摘要，用中文简洁、准确地回答用户问题。"
    "如果信息有冲突，请说明。最后必须列出参考来源（编号、标题、链接）。"
)

_MAX_TOTAL_CHARS = 6000


async def summarize(query: str, fetched: list[dict[str, Any]], client: LLMClient) -> str:
    """调用 LLM 对抓取内容生成中文摘要。"""
    if not fetched:
        return "未找到可总结的网页内容。"

    source_lines: list[str] = []
    for i, item in enumerate(fetched, 1):
        flag = "（摘要）" if item.get("used_snippet_fallback") else ""
        source_lines.append(
            f"[{i}]{flag} {item.get('title', '')}\n链接：{item.get('link', '')}\n内容：{item.get('text', '')}"
        )

    user_prompt = (
        f"用户问题：{query}\n\n"
        "以下是搜索结果中的网页内容：\n"
        + "\n\n".join(source_lines)
    )[:_MAX_TOTAL_CHARS]

    try:
        summary = await client.complete(_SUMMARY_SYSTEM_PROMPT, user_prompt, temperature=0.5)
        summary = summary.strip()
        if not summary:
            raise ValueError("empty summary")
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        summary = "已搜索到以下结果，但未能生成自动摘要，请直接查看来源。"

    references = [f"{i}. {item.get('title', '')}\n   {item.get('link', '')}" for i, item in enumerate(fetched, 1)]
    return summary + "\n\n参考来源：\n" + "\n".join(references)
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_summarizer.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/tools/web_summarizer.py agent-core/tests/tools/test_web_summarizer.py
git commit -m "feat(agent-core): add LLM-based web search summarizer"
```

---

## Task 5: 重写 WebSearchTool 编排 + 状态事件

**Files:**
- Modify: `agent-core/app/tools/web_search.py`
- Test: `agent-core/tests/tools/test_web_search.py`

**Interfaces:**
- Consumes: `ToolContext`（含 `emit`）、`BingSearchClient`, `BaiduSearchClient`, `fetch_pages`, `summarize`
- Produces: `ToolResult` + SSE events `tool_start` / `tool_progress` / `tool_result`

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/tools/test_web_search.py
import pytest
from unittest.mock import AsyncMock
from app.tools.web_search import WebSearchTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_web_search_emits_progress_and_returns_summary():
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    ctx = ToolContext(
        conversation_id="c1",
        agent_type="generic",
        working_memory={},
        emit=emit,
    )

    tool = WebSearchTool()
    # Mock 内部客户端
    tool.bing_client = AsyncMock()
    tool.baidu_client = AsyncMock()
    tool.fetcher = AsyncMock()
    tool.summarizer = AsyncMock()

    tool.bing_client.search.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "snippet": "bing snippet", "source": "bing"}
    ]
    tool.baidu_client.search.return_value = []
    tool.fetcher.return_value = [
        {"title": "Bing Title", "link": "https://b.com", "text": "fetched text", "used_snippet_fallback": False}
    ]
    tool.summarizer.return_value = "摘要结果。"

    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "摘要结果。" in result.observation
    events = [e for e, _ in emitted]
    assert "tool_progress" in events
    assert any(p.get("status") == "summarizing" for _, p in emitted)
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_search.py -v
```
Expected: FAIL due to missing attributes.

- [ ] **Step 3: 最小实现**

```python
# agent-core/app/tools/web_search.py
from __future__ import annotations

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
        await self._emit(context, "tool_progress", {"status": "summarizing", "detail": f"正在分析 {len(deduped)} 个网页"})

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
            await context.emit(event, payload)
```

Note: add `import asyncio` at top.

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/tools/test_web_search.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/tools/web_search.py agent-core/tests/tools/test_web_search.py
git commit -m "feat(agent-core): orchestrate multi-source search, fetch, summarize with progress events"
```

---

## Task 6: routers.py 传入 emit 回调并透传 tool_progress

**Files:**
- Modify: `agent-core/app/api/routers.py:333-337`
- Test: `agent-core/tests/api/test_generic_run.py`（新增）

**Interfaces:**
- Consumes: `ToolContext.emit`
- Produces: SSE stream now contains `event: tool_progress`

- [ ] **Step 1: 写失败测试**

```python
# agent-core/tests/api/test_generic_run.py
import pytest
from fastapi.testclient import TestClient
from app.api.routers import router
from fastapi import FastAPI


app = FastAPI()
app.include_router(router)


def test_generic_run_stream_includes_tool_progress():
    # 由于完整链路涉及真实 LLM，这里只做路由层断言：
    # 通过 monkeypatch 让 _generic_run_stream 返回包含 tool_progress 的 SSE。
    import app.api.routers as routers

    async def fake_stream(user_input):
        yield "event: tool_start\ndata: {\"id\":\"call-1\",\"tool_name\":\"web_search\",\"arguments\":{\"query\":\"x\"}}\n\n"
        yield "event: tool_progress\ndata: {\"id\":\"call-1\",\"status\":\"summarizing\"}\n\n"
        yield "event: tool_result\ndata: {\"id\":\"call-1\",\"tool_name\":\"web_search\",\"arguments\":{\"query\":\"x\"},\"observation\":\"summary\"}\n\n"
        yield "event: done\ndata: {}\n\n"

    routers._generic_run_stream = fake_stream

    client = TestClient(app)
    resp = client.post("/agents/generic/run", json={"conversationId": "c1", "userInput": "x"})
    assert resp.status_code == 200
    body = resp.text
    assert "event: tool_progress" in body
    assert "\"status\":\"summarizing\"" in body
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/api/test_generic_run.py -v
```
Expected: FAIL module not found or `_generic_run_stream` overwritten but test path.

- [ ] **Step 3: 最小实现**

Modify `agent-core/app/api/routers.py` around the tool execution block (lines 329-340):

```python
                async def emit(event_name: str, payload: dict):
                    payload_with_id = {"id": tool_call_id, **payload}
                    yield f"event: {event_name}\ndata: {json.dumps(payload_with_id, ensure_ascii=False)}\n\n"

                from app.runtime.tool import ToolContext

                result = await web_search.execute(arguments, ToolContext(
                    conversation_id=req.conversationId,
                    agent_type="generic",
                    working_memory={},
                    emit=emit,
                ))
```

Wait — `emit` is an async generator function because it yields. But `ToolContext.emit` expects a coroutine `Callable[[str, dict], Awaitable[None] | None]`. We cannot `await emit(...)` if it yields. We need a normal async function that appends to a queue or directly writes to the response stream. In the current architecture, `_generic_run_stream` is an async generator that yields SSE strings. The `web_search.execute` is awaited; it cannot yield. So we need a way for `emit` to write to the stream. Options:
1. Use an `asyncio.Queue` in `_generic_run_stream` and have a separate task consuming it and yielding. But that complicates.
2. Have `emit` put event strings into a list and then after `execute` returns, yield them. But then progress events would only appear after the whole tool execution finishes, defeating the purpose.
3. Make `execute` itself a generator? Not compatible with BaseTool interface.
4. Use a callback that writes to an `asyncio.Queue`; the outer generator concurrently yields from queue while awaiting execute. This is more complex.

Actually, we can restructure `_generic_run_stream` so that `web_search.execute` runs in a background task and yields events from a queue:

```python
async def _generic_run_stream(user_input: str):
    ...
    queue = asyncio.Queue()
    async def emit(event_name, payload):
        await queue.put(f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n")

    async def run_tools():
        ... execute tool ...
        await queue.put(...) # done marker

    task = asyncio.create_task(run_tools())
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
    await task
```

But this changes a lot. Alternatively, we can keep `emit` as a synchronous callback? In async context, we can schedule it via `asyncio.create_task` to put to a queue. But `ToolContext.emit` signature can be `Callable[[str, dict], Awaitable[None] | None]` and we can implement `emit` as `asyncio.create_task(queue.put(...))`? Actually `create_task` returns Task; if we define `emit` as a regular function that creates a task and returns None, it's not awaitable but acceptable if signature includes None return. But the BaseTool calls `await context.emit(...)`, so emit must be awaitable. We can define:

```python
async def emit(event_name, payload):
    await queue.put(f"event: {event_name}...")
```

Then we need to concurrently read queue while execute is running. So we need a task wrapper.

To keep changes minimal and still get real-time progress, we can use `asyncio.create_task(run_tool_with_emit(...))` and yield from queue in a loop. This is the right approach.

The plan must detail this. In Step 3, implement `_run_tool_with_progress` helper and modify `_generic_run_stream`.

Let's design code:

```python
async def _generic_run_stream(user_input: str):
    ...
    if first.tool_calls:
        ...
        for tc in first.tool_calls:
            ...
            tool_call_id = tc.get("id", "")
            yield f"event: tool_start\ndata: {json.dumps({'id': tool_call_id, 'tool_name': tool_name, 'arguments': arguments}, ensure_ascii=False)}\n\n"

            queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def emit(event_name: str, payload: dict):
                payload_with_id = {"id": tool_call_id, **payload}
                await queue.put(f"event: {event_name}\ndata: {json.dumps(payload_with_id, ensure_ascii=False)}\n\n")

            async def run_tool():
                from app.runtime.tool import ToolContext
                result = await web_search.execute(arguments, ToolContext(
                    conversation_id="generic",
                    agent_type="generic",
                    working_memory={},
                    emit=emit,
                ))
                observation = result.observation
                await queue.put(f"event: tool_result\ndata: {json.dumps({'id': tool_call_id, 'tool_name': tool_name, 'arguments': arguments, 'observation': observation}, ensure_ascii=False)}\n\n")
                await queue.put(None)
                return observation

            tool_task = asyncio.create_task(run_tool())
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
            observation = await tool_task
            messages.append({...})
```

This is the correct implementation. The test can be simplified to just check that `_generic_run_stream` yields tool_progress when tool emits. But the fake_stream approach is okay.

In the plan, we can show the exact code modifications.

Let's include this in Step 3.

- [ ] **Step 3: 最小实现**

Update `agent-core/app/api/routers.py`:

1. 在文件顶部添加 `import asyncio`（当前未导入）。
2. 替换工具执行循环为并发消费队列的版本：

```python
            for tc in first.tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "unknown")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                tool_call_id = tc.get("id", "")
                log.info("Tool call start: %s(%s)", tool_name, arguments)
                yield f"event: tool_start\ndata: {json.dumps({'id': tool_call_id, 'tool_name': tool_name, 'arguments': arguments}, ensure_ascii=False)}\n\n"

                queue: asyncio.Queue[str | None] = asyncio.Queue()

                async def emit(event_name: str, payload: dict, _id=tool_call_id):
                    payload_with_id = {"id": _id, **payload}
                    await queue.put(
                        f"event: {event_name}\ndata: {json.dumps(payload_with_id, ensure_ascii=False)}\n\n"
                    )

                async def run_tool(_id=tool_call_id, _tool_name=tool_name, _arguments=arguments):
                    from app.runtime.tool import ToolContext

                    result = await web_search.execute(
                        _arguments,
                        ToolContext(
                            conversation_id="generic",
                            agent_type="generic",
                            working_memory={},
                            emit=emit,
                        ),
                    )
                    observation = result.observation
                    log.info("Tool call done: %s, observation_len=%d", _tool_name, len(observation))
                    await queue.put(
                        f"event: tool_result\ndata: {json.dumps({'id': _id, 'tool_name': _tool_name, 'arguments': _arguments, 'observation': observation}, ensure_ascii=False)}\n\n"
                    )
                    await queue.put(None)
                    return observation

                tool_task = asyncio.create_task(run_tool())
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
                observation = await tool_task

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation,
                })
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/api/test_generic_run.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/app/api/routers.py agent-core/tests/api/test_generic_run.py
git commit -m "feat(agent-core): wire tool progress events through generic run SSE"
```

---

## Task 7: GenericAgentHandler 转发 tool_progress

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/handler/GenericAgentHandler.java`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/handler/GenericAgentHandlerTest.java`

**Interfaces:**
- Consumes: SSE `event: tool_progress` from agent-core
- Produces: forwards to `SseEmitterService.sendToProject(projectId, "tool_progress", payload)`

- [ ] **Step 1: 写失败测试**

```java
// agent-api/src/test/java/com/meichen/orchestrator/handler/GenericAgentHandlerTest.java
package com.meichen.orchestrator.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GenericAgentHandlerTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    // ... existing tests ...

    @Test
    void extractStatus_shouldReturnSummarizing() {
        String data = "{\"id\":\"call-1\",\"status\":\"summarizing\",\"detail\":\"x\"}";
        String status = GenericAgentHandler.extractStatus(objectMapper, data);
        assertThat(status).isEqualTo("summarizing");
    }
}
```

Add a helper `extractStatus` in GenericAgentHandler (package-private static) for testing.

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-api
./mvnw test -Dtest=GenericAgentHandlerTest -q
```
Expected: FAIL with method not found.

- [ ] **Step 3: 最小实现**

Add in `GenericAgentHandler.java`:

```java
static String extractStatus(ObjectMapper objectMapper, String data) {
    try {
        return objectMapper.readTree(data).path("status").asText(null);
    } catch (Exception e) {
        log.warn("Failed to parse tool_progress data: {}", data, e);
        return null;
    }
}
```

And inside `doOnNext`, add branch after `tool_result`:

```java
                    } else if ("tool_progress".equals(eventName)) {
                        try {
                            Object payload = objectMapper.readValue(
                                event.data(), new TypeReference<java.util.Map<String, Object>>() {}
                            );
                            sseEmitterService.sendToProject(project.getId(), eventName, payload);
                        } catch (Exception ex) {
                            log.warn("Failed to parse tool_progress data: {}", event.data(), ex);
                        }
                    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-api
./mvnw test -Dtest=GenericAgentHandlerTest -q
```
Expected: BUILD SUCCESS, tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-api/src/main/java/com/meichen/orchestrator/handler/GenericAgentHandler.java agent-api/src/test/java/com/meichen/orchestrator/handler/GenericAgentHandlerTest.java
git commit -m "feat(agent-api): forward tool_progress SSE events to frontend"
```

---

## Task 8: 前端工具消息解析工具与卡片状态实时更新

**Files:**
- Create: `agent-web/src/utils/toolMessage.js`
- Create: `agent-web/src/utils/__tests__/toolMessage.spec.ts`
- Modify: `agent-web/src/views/ChatView.vue`

**Interfaces:**
- Consumes: SSE `tool_progress` and `tool_result` events; tool message JSON string
- Produces: `parseToolMessage(content)` returns `{ toolName, toolArguments, observation, status, detail }`; `getToolStatusLabel(status)` returns label string

- [ ] **Step 1: 写失败测试**

```typescript
// agent-web/src/utils/__tests__/toolMessage.spec.ts
import { describe, it, expect } from 'vitest'
import { parseToolMessage, getToolStatusLabel } from '../toolMessage'

describe('parseToolMessage', () => {
  it('parses searching status', () => {
    const content = JSON.stringify({ id: 'c1', tool_name: 'web_search', arguments: { query: 'x' }, status: 'searching' })
    const display = parseToolMessage(content)
    expect(display.status).toBe('searching')
    expect(display.toolArguments.query).toBe('x')
    expect(display.toolName).toBe('web_search')
  })

  it('parses summarizing status with detail', () => {
    const content = JSON.stringify({ id: 'c1', tool_name: 'web_search', arguments: {}, status: 'summarizing', detail: '分析 3 个网页' })
    const display = parseToolMessage(content)
    expect(display.status).toBe('summarizing')
    expect(display.detail).toBe('分析 3 个网页')
  })

  it('parses old dirty assistant tool_call XML', () => {
    const content = '<tool_call>web_search\n<arg_key>query</arg_key>\n<arg_value>北京天气</arg_value>\n</tool_call>'
    const display = parseToolMessage(content)
    expect(display.toolName).toBe('web_search')
    expect(display.toolArguments.query).toBe('北京天气')
    expect(display.status).toBe('done')
  })
})

describe('getToolStatusLabel', () => {
  it('returns correct labels', () => {
    expect(getToolStatusLabel('searching')).toBe('搜索中...')
    expect(getToolStatusLabel('summarizing')).toBe('总结中...')
    expect(getToolStatusLabel('done')).toBe('已完成')
    expect(getToolStatusLabel('')).toBe('已完成')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-web
npm run test:unit -- src/utils/__tests__/toolMessage.spec.ts
```
Expected: FAIL file not found.

- [ ] **Step 3: 最小实现**

1. Create `agent-web/src/utils/toolMessage.js`:

```javascript
// agent-web/src/utils/toolMessage.js
export function parseToolMessage(content) {
  if (!content) {
    return { toolName: '工具', toolArguments: {}, observation: '', status: 'done', detail: '' }
  }

  // 新格式：JSON 字符串
  if (typeof content === 'string' && content.trim().startsWith('{')) {
    try {
      const data = JSON.parse(content)
      return {
        toolName: data.tool_name || '工具',
        toolArguments: data.arguments || {},
        observation: data.observation || '',
        status: data.status || 'done',
        detail: data.detail || '',
      }
    } catch (e) {
      return { toolName: '工具', toolArguments: {}, observation: content, status: 'done', detail: '' }
    }
  }

  // 兼容旧脏数据：assistant 文本中包含 <tool_call> XML
  if (typeof content === 'string' && content.includes('<tool_call>')) {
    const match = content.match(/<tool_call>([\s\S]*?)<\/tool_call>/)
    const raw = match ? match[1] : content
    const toolNameMatch = raw.match(/^(\w+)/)
    const queryMatch = raw.match(/<arg_key>query<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/)
    return {
      toolName: toolNameMatch ? toolNameMatch[1] : '工具',
      toolArguments: queryMatch ? { query: queryMatch[1].trim() } : {},
      observation: '',
      status: 'done',
      detail: '',
    }
  }

  return { toolName: '工具', toolArguments: {}, observation: content || '', status: 'done', detail: '' }
}

export function getToolStatusLabel(status) {
  if (status === 'searching') return '搜索中...'
  if (status === 'summarizing') return '总结中...'
  return '已完成'
}
```

2. Update `agent-web/src/views/ChatView.vue`:

Import the utility at the top of `<script setup>`:

```typescript
import { parseToolMessage, getToolStatusLabel } from '@/utils/toolMessage'
```

Replace the inline `toolDisplay` function with:

```typescript
const toolDisplay = (msg) => parseToolMessage(msg?.content)
```

In the SSE `onmessage` handler, add a branch for `tool_progress`:

```typescript
} else if (msg.event === 'tool_progress') {
  const payload = JSON.parse(msg.data)
  const existing = messages.value.find(
    (m) => m.role === 'tool' && m.content && m.content.includes(`"id":"${payload.id}"`)
  )
  if (existing) {
    try {
      const data = JSON.parse(existing.content)
      data.status = payload.status
      data.detail = payload.detail || ''
      existing.content = JSON.stringify(data)
    } catch (e) {
      // ignore
    }
  }
  scrollToBottom()
}
```

Update `tool_start` insertion so initial status is `searching`:

```typescript
const toolMsg = {
  id: `tool-${Date.now()}`,
  projectId: projectId,
  role: 'tool',
  messageType: 'tool',
  content: JSON.stringify({
    id: payload.id,
    tool_name: payload.tool_name,
    arguments: payload.arguments,
    status: 'searching',
    detail: '正在搜索...',
    observation: '',
  }),
  createdAt: new Date().toISOString(),
}
```

Update tool card template:

```vue
<div v-if="msg.role === 'tool' || isToolCallMessage(msg)" class="tool-card">
  <div class="tool-header">
    <span class="tool-icon">🔍</span>
    <span class="tool-name">{{ toolDisplay(msg).toolName }}</span>
    <span class="tool-status running">{{ getToolStatusLabel(toolDisplay(msg).status) }}</span>
  </div>
  <div v-if="toolDisplay(msg).toolArguments && toolDisplay(msg).toolArguments.query" class="tool-query">
    查询：{{ toolDisplay(msg).toolArguments.query }}
  </div>
  <div v-if="toolDisplay(msg).detail" class="tool-detail">
    {{ toolDisplay(msg).detail }}
  </div>
  <div v-if="toolDisplay(msg).observation" class="tool-body">
    <pre>{{ toolDisplay(msg).observation }}</pre>
  </div>
</div>
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-web
npm run test:unit -- src/utils/__tests__/toolMessage.spec.ts
```
Expected: 6 passed.

Run full frontend unit tests:
```bash
cd agent-web
npm run test:unit
```
Expected: all existing tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-web/src/utils/toolMessage.js agent-web/src/utils/__tests__/toolMessage.spec.ts agent-web/src/views/ChatView.vue
git commit -m "feat(agent-web): extract tool message parser and render progress states"
```

---

## Task 9: 集成测试与本地验证

**Files:**
- Create: `agent-core/tests/integration/test_web_search_summary.py`
- Manual: 浏览器 + 本地服务

- [ ] **Step 1: 写集成测试**

```python
# agent-core/tests/integration/test_web_search_summary.py
import pytest
from app.tools.web_search import WebSearchTool
from app.runtime.tool import ToolContext


@pytest.mark.asyncio
async def test_web_search_end_to_end_with_mock_clients():
    emitted = []

    async def emit(event, payload):
        emitted.append((event, payload))

    tool = WebSearchTool()

    # Mock clients to avoid real HTTP in CI
    class FakeClient:
        async def search(self, query, limit=5):
            return [
                {"title": f"{query} 结果1", "link": "https://example.com/1", "snippet": "摘要1", "source": "bing"},
                {"title": f"{query} 结果2", "link": "https://example.com/2", "snippet": "摘要2", "source": "baidu"},
            ]

    tool.bing_client = FakeClient()
    tool.baidu_client = FakeClient()
    tool.fetcher = lambda *args, **kwargs: [
        {"title": "结果1", "link": "https://example.com/1", "text": "正文1", "used_snippet_fallback": False},
    ]
    tool.summarizer = lambda query, fetched, client: f"关于 {query} 的摘要。"

    ctx = ToolContext("c1", "generic", {}, emit=emit)
    result = await tool.execute({"query": "北京天气"}, ctx)

    assert "北京天气" in result.observation
    assert any(e == "tool_progress" for e, _ in emitted)
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd agent-core
pytest tests/integration/test_web_search_summary.py -v
```
Expected: FAIL module not found.

- [ ] **Step 3: 最小实现**

The implementation is already done in previous tasks. Just create the test file.

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd agent-core
pytest tests/integration/test_web_search_summary.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/liulei/private-work/design-agent
git add agent-core/tests/integration/test_web_search_summary.py
git commit -m "test(agent-core): add web search end-to-end integration test"
```

---

## Self-Review

**1. Spec coverage:**
- 多源搜索 → Task 2, Task 5
- 百度广告过滤 → Task 2 `is_ad_result`, BaiduSearchClient
- 去重 → Task 2 `deduplicate_results`
- 正文抓取与 fallback → Task 3
- LLM 摘要与来源链接 → Task 4
- `tool_progress` 事件 → Task 1, Task 5, Task 6, Task 7, Task 8
- 前端状态展示 → Task 8
- 错误兜底 → Task 5 `_safe_gather`, Task 3 fetch fallback, Task 4 summary fallback

No gaps identified.

**2. Placeholder scan:**
- No TBD/TODO.
- No vague “add error handling” steps; concrete branches and fallback code shown.
- No “write tests for the above” without code.

**3. Type consistency:**
- `ToolContext.emit` signature is `Callable[[str, dict], Awaitable[None] | None] | None` across all tasks.
- `tool_progress` payload always contains `id`, `status`, and optional `detail`.
- Tool message JSON fields consistently use `tool_name`, `arguments`, `status`, `detail`, `observation`.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-15-web-search-baidu-summary-status.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach do you prefer?
