# 知识库爬虫模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现美陈设计 Agent 的知识库爬虫模块，支持站酷、公众号、1688、Pinterest 四源定向爬取，内置多层反爬策略。

**Architecture:** 以 `BaseCrawler` 抽象类为核心，继承者按需选择 `requests` 或 `Playwright` 引擎；反爬逻辑（延迟、UA、重试、去重）下沉到独立 `utils` 模块；所有爬虫通过统一 CLI 入口调用。

**Tech Stack:** Python 3.9+, requests, BeautifulSoup4, Playwright, SQLAlchemy, Milvus

## Global Constraints

- Python 3.9 兼容：每个 `.py` 文件顶部必须添加 `from __future__ import annotations`
- 无占位符：每个步骤必须包含可直接运行的代码和命令
- TDD：每个 Task 先写测试，再写实现
- 文件路径以 `python-ai/` 为根目录

---

## 文件结构

```
app/crawlers/
├── __init__.py
├── base.py              # BaseCrawler 抽象类 + 反爬封装
├── utils.py             # UA 轮换、随机延迟、URL 去重、进度保存
├── zcool.py             # 站酷作品爬虫（requests，静态页面）
├── wechat_article.py    # 公众号文章爬虫（Playwright）
├── alibaba_1688.py      # 1688 材料爬虫（Playwright）
├── cli.py               # 统一 CLI 入口
└── tests/
    ├── __init__.py
    ├── test_utils.py
    ├── test_base.py
    └── test_zcool.py
```

---

### Task 1: 反爬工具模块 (`utils.py`)

**Files:**
- Create: `app/crawlers/utils.py`
- Create: `app/crawlers/tests/test_utils.py`
- Modify: `app/pyproject.toml` — 添加依赖

**Interfaces:**
- Produces:
  - `USER_AGENTS: list[str]` — 10 个常见浏览器 UA
  - `get_random_ua() -> str` — 随机 UA
  - `random_delay(min_sec: float, max_sec: float) -> None` — 随机睡眠
  - `is_url_crawled(url: str, db_path: str) -> bool` — URL 去重检查
  - `mark_url_crawled(url: str, db_path: str) -> None` — 标记已爬
  - `load_progress(name: str, output_dir: str) -> dict` — 加载断点
  - `save_progress(name: str, data: dict, output_dir: str) -> None` — 保存断点

- [ ] **Step 1: 添加依赖**

在 `pyproject.toml` 的 `[project]` 段追加：
```toml
dependencies = [
    # ... existing ...
    "requests>=2.32.0",
    "beautifulsoup4>=4.12.0",
    "playwright>=1.45.0",
]
```

- [ ] **Step 2: 写测试**

创建 `app/crawlers/tests/test_utils.py`：
```python
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.crawlers.utils import (
    get_random_ua,
    is_url_crawled,
    load_progress,
    mark_url_crawled,
    random_delay,
    save_progress,
)


def test_get_random_ua_returns_string():
    ua = get_random_ua()
    assert isinstance(ua, str)
    assert "Mozilla" in ua


def test_random_delay_does_not_crash():
    import time

    start = time.time()
    random_delay(0.01, 0.02)
    elapsed = time.time() - start
    assert 0.01 <= elapsed <= 0.05


def test_url_dedup(tmp_path: Path):
    db_path = str(tmp_path / "crawled.db")
    url = "https://example.com/test"
    assert is_url_crawled(url, db_path) is False
    mark_url_crawled(url, db_path)
    assert is_url_crawled(url, db_path) is True


def test_progress_save_and_load(tmp_path: Path):
    output_dir = str(tmp_path)
    data = {"offset": 42, "last_url": "https://example.com"}
    save_progress("zcool", data, output_dir)
    loaded = load_progress("zcool", output_dir)
    assert loaded == data
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd python-ai && pytest app/crawlers/tests/test_utils.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.crawlers'`

- [ ] **Step 4: 实现 `utils.py`**

创建 `app/crawlers/utils.py`：
```python
from __future__ import annotations

import json
import random
import sqlite3
import time
from pathlib import Path

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def get_random_ua() -> str:
    return random.choice(USER_AGENTS)


def random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def _ensure_dedup_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS crawled_urls (url TEXT PRIMARY KEY, crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()


def is_url_crawled(url: str, db_path: str) -> bool:
    _ensure_dedup_db(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT 1 FROM crawled_urls WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def mark_url_crawled(url: str, db_path: str) -> None:
    _ensure_dedup_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR IGNORE INTO crawled_urls (url) VALUES (?)",
        (url,),
    )
    conn.commit()
    conn.close()


def load_progress(name: str, output_dir: str) -> dict:
    path = Path(output_dir) / f"{name}_progress.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_progress(name: str, data: dict, output_dir: str) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{name}_progress.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd python-ai && pytest app/crawlers/tests/test_utils.py -v
```
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add python-ai/app/crawlers/
git commit -m "feat(crawler): add anti-crawl utils (UA rotation, delay, dedup, progress)"
```

---

### Task 2: BaseCrawler 基础类 (`base.py`)

**Files:**
- Create: `app/crawlers/base.py`
- Create: `app/crawlers/tests/test_base.py`
- Modify: `app/crawlers/__init__.py`

**Interfaces:**
- Consumes: `utils.get_random_ua`, `utils.random_delay`, `utils.is_url_crawled`, `utils.mark_url_crawled`
- Produces:
  - `BaseCrawler` (abstract)
    - `__init__(name, output_dir, delay_min, delay_max, max_retries, max_concurrent)`
    - `fetch(url: str) -> str` — requests 抓取
    - `fetch_pw(url: str) -> str` — Playwright 抓取
    - `parse(html: str) -> list[dict]` — abstract
    - `save(items: list[dict]) -> None` — abstract
    - `run(seed_urls: list[str]) -> None` — 主流程
  - `RetryableError` / `BlockedError`

- [ ] **Step 1: 写测试**

创建 `app/crawlers/tests/test_base.py`：
```python
from __future__ import annotations

import pytest
from pathlib import Path

from app.crawlers.base import BaseCrawler, RetryableError


class DummyCrawler(BaseCrawler):
    def parse(self, html: str) -> list[dict]:
        return [{"title": "dummy", "html_len": len(html)}]

    def save(self, items: list[dict]) -> None:
        self.saved = items


def test_base_crawler_init():
    c = DummyCrawler(name="test", output_dir="/tmp")
    assert c.name == "test"
    assert c.delay_min == 2.0
    assert c.max_retries == 3


def test_base_crawler_dedup_skips_crawled(tmp_path: Path):
    c = DummyCrawler(name="test", output_dir=str(tmp_path))
    url = "https://example.com/a"
    c._mark_crawled(url)
    assert c._should_skip(url) is True


def test_base_crawler_fetch_mock(requests_mock):
    c = DummyCrawler(name="test", output_dir="/tmp")
    requests_mock.get("https://example.com", text="<html>hello</html>")
    html = c.fetch("https://example.com")
    assert "hello" in html
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd python-ai && pytest app/crawlers/tests/test_base.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: 实现 `base.py`**

创建 `app/crawlers/base.py`：
```python
from __future__ import annotations

import abc
import concurrent.futures
import logging
import time
from pathlib import Path
from typing import Any

import requests

from app.crawlers.utils import (
    get_random_ua,
    is_url_crawled,
    load_progress,
    mark_url_crawled,
    random_delay,
    save_progress,
)

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    pass


class BlockedError(Exception):
    pass


class BaseCrawler(abc.ABC):
    def __init__(
        self,
        name: str,
        output_dir: str,
        delay_min: float = 2.0,
        delay_max: float = 5.0,
        max_retries: int = 3,
        max_concurrent: int = 2,
    ):
        self.name = name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self.dedup_db = str(self.output_dir / "crawled_urls.db")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_random_ua()})
        self._playwright = None
        self._browser = None

    def _should_skip(self, url: str) -> bool:
        if is_url_crawled(url, self.dedup_db):
            logger.info("[SKIP] already crawled: %s", url)
            return True
        return False

    def _mark_crawled(self, url: str) -> None:
        mark_url_crawled(url, self.dedup_db)

    def fetch(self, url: str) -> str:
        for attempt in range(1, self.max_retries + 1):
            try:
                random_delay(self.delay_min, self.delay_max)
                resp = self.session.get(url, timeout=30)
                if resp.status_code in (403, 429, 503):
                    wait = 2 ** attempt
                    logger.warning("[BLOCKED] %s -> sleep %ds", url, wait)
                    time.sleep(wait)
                    if resp.status_code == 403:
                        raise BlockedError(f"Blocked: {url}")
                    raise RetryableError(f"Status {resp.status_code}: {url}")
                resp.raise_for_status()
                return resp.text
            except (requests.RequestException, RetryableError) as exc:
                logger.warning("[RETRY %d/%d] %s: %s", attempt, self.max_retries, url, exc)
                if attempt == self.max_retries:
                    raise
        return ""

    def fetch_pw(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

        random_delay(self.delay_min, self.delay_max)
        context = self._browser.new_context(
            user_agent=get_random_ua(),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            # simulate human behavior
            page.mouse.move(100, 200)
            page.wait_for_timeout(random.randint(3000, 8000))
            html = page.content()
            if "访问频繁" in html or "captcha" in html.lower():
                raise BlockedError(f"Captcha detected: {url}")
            return html
        finally:
            context.close()

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    @abc.abstractmethod
    def parse(self, html: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, items: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def run(self, seed_urls: list[str]) -> None:
        progress = load_progress(self.name, str(self.output_dir))
        completed = set(progress.get("completed", []))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {}
            for url in seed_urls:
                if url in completed or self._should_skip(url):
                    continue
                future = executor.submit(self._crawl_one, url)
                futures[future] = url

            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    future.result()
                    completed.add(url)
                except BlockedError:
                    logger.error("[BLOCKED] pausing source: %s", url)
                    break
                except Exception:
                    logger.exception("[ERROR] %s", url)

        save_progress(self.name, {"completed": list(completed)}, str(self.output_dir))

    def _crawl_one(self, url: str) -> None:
        html = self.fetch(url)
        items = self.parse(html)
        if items:
            self.save(items)
        self._mark_crawled(url)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd python-ai && pytest app/crawlers/tests/test_base.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add python-ai/app/crawlers/
git commit -m "feat(crawler): add BaseCrawler with retry, blocking detection, Playwright support"
```

---

### Task 3: 站酷爬虫 (`zcool.py`)

**Files:**
- Create: `app/crawlers/zcool.py`
- Create: `app/crawlers/tests/test_zcool.py`

**Interfaces:**
- Consumes: `BaseCrawler.fetch`, `BaseCrawler.parse`, `BaseCrawler.save`
- Produces:
  - `ZcoolCrawler(BaseCrawler)`
    - `search(keywords: list[str], limit: int) -> list[str]` — 获取作品 URL 列表
    - `parse(html: str) -> list[dict]` — 提取标题、作者、描述、图片
    - `save(items: list[dict]) -> None` — 写入 SQLite + 下载图片

- [ ] **Step 1: 写测试**

创建 `app/crawlers/tests/test_zcool.py`：
```python
from __future__ import annotations

from pathlib import Path

from app.crawlers.zcool import ZcoolCrawler


SAMPLE_DETAIL_HTML = """
<html>
<head><title>夏日海洋美陈设计 - 站酷 (ZCOOL)</title></head>
<body>
<div class="work-title"><h1>夏日海洋美陈设计</h1></div>
<div class="work-author"><a>设计师小王</a></div>
<div class="work-desc"><p>为某商场中庭设计的夏日海洋主题吊饰方案，预算约15万。</p></div>
<img src="https://img.zcool.cn/1.jpg" class="work-img"/>
<img src="https://img.zcool.cn/2.jpg" class="work-img"/>
</body>
</html>
"""


def test_zcool_parse_detail():
    c = ZcoolCrawler(name="zcool", output_dir="/tmp")
    items = c.parse(SAMPLE_DETAIL_HTML)
    assert len(items) == 1
    assert items[0]["title"] == "夏日海洋美陈设计"
    assert "15万" in items[0]["description"]
    assert len(items[0]["images"]) == 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd python-ai && pytest app/crawlers/tests/test_zcool.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 实现 `zcool.py`**

创建 `app/crawlers/zcool.py`：
```python
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.zcool.com.cn/search/content?word={keyword}&type=0&sort=1&page={page}"


class ZcoolCrawler(BaseCrawler):
    def search(self, keywords: list[str], limit: int = 100) -> list[str]:
        urls: list[str] = []
        for keyword in keywords:
            page = 1
            while len(urls) < limit:
                url = SEARCH_URL.format(keyword=quote(keyword), page=page)
                try:
                    html = self.fetch(url)
                    soup = BeautifulSoup(html, "html.parser")
                    links = soup.select("a[href^='/work/']")
                    for a in links:
                        detail = urljoin("https://www.zcool.com.cn", a["href"])
                        if detail not in urls:
                            urls.append(detail)
                        if len(urls) >= limit:
                            break
                    if not links:
                        break
                    page += 1
                except Exception:
                    logger.exception("[SEARCH] keyword=%s page=%d", keyword, page)
                    break
        return urls[:limit]

    def parse(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.select_one(".work-title h1, .details-cont-title h2")
        title = title_tag.get_text(strip=True) if title_tag else ""

        author_tag = soup.select_one(".work-author a, .user-card-name")
        author = author_tag.get_text(strip=True) if author_tag else ""

        desc_tag = soup.select_one(".work-desc p, .work-content-text")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        images = []
        for img in soup.select(".work-img, .details-picture-img, img[src*='zcool.cn']"):
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                images.append(src)

        if not title:
            return []

        return [{
            "source": "zcool",
            "title": title,
            "author": author,
            "description": description,
            "images": images,
            "url": "",  # filled by caller
        }]

    def save(self, items: list[dict[str, Any]]) -> None:
        from app.models.database import SessionLocal
        from app.models.project import DesignCase
        from app.services.embedding_client import embedding_client
        from app.services.knowledge_base import knowledge_base

        db = SessionLocal()
        try:
            for item in items:
                case = DesignCase(
                    title=item["title"],
                    space_type="",
                    budget_level="",
                    theme="",
                    style="",
                    summary=item["description"][:500],
                    images_json=json.dumps(item.get("images", [])),
                    source=item.get("source", "zcool"),
                )
                db.add(case)
                db.commit()

                # Download images
                img_dir = self.output_dir / "images" / f"case_{case.id}"
                img_dir.mkdir(parents=True, exist_ok=True)
                local_images = []
                for idx, img_url in enumerate(item.get("images", [])[:5]):
                    try:
                        ext = Path(img_url).suffix or ".jpg"
                        img_path = img_dir / f"{idx}{ext}"
                        r = self.session.get(img_url, timeout=30)
                        r.raise_for_status()
                        img_path.write_bytes(r.content)
                        local_images.append(str(img_path))
                    except Exception:
                        logger.warning("[IMG] failed %s", img_url)

                if local_images:
                    case.images_json = json.dumps(local_images)
                    db.commit()

                # Milvus
                try:
                    embedding = embedding_client.embed(case.summary or case.title)
                    collection = knowledge_base._get_case_collection()
                    collection.insert([
                        [case.id], [embedding], [case.title], [case.space_type or ""],
                        [case.budget_level or ""], [case.theme or ""], [case.style or ""], [case.summary or ""]
                    ])
                except Exception:
                    logger.exception("[MILVUS] failed %s", case.title)
        finally:
            db.close()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd python-ai && pytest app/crawlers/tests/test_zcool.py -v
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add python-ai/app/crawlers/
git commit -m "feat(crawler): add ZcoolCrawler for zcool.com.cn"
```

---

### Task 4: CLI 入口 (`cli.py`)

**Files:**
- Create: `app/crawlers/cli.py`
- Modify: `pyproject.toml` — 添加 console script

**Interfaces:**
- Produces: `python -m app.crawlers.cli zcool --keywords "美陈,商业空间" --limit 100`

- [ ] **Step 1: 写测试**

创建 `app/crawlers/tests/test_cli.py`：
```python
from __future__ import annotations

from click.testing import CliRunner

from app.crawlers.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "zcool" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd python-ai && pytest app/crawlers/tests/test_cli.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 实现 `cli.py`**

创建 `app/crawlers/cli.py`：
```python
from __future__ import annotations

import logging

import click

from app.crawlers.zcool import ZcoolCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@click.group()
@click.option("--output-dir", default="data/crawler_downloads", help="下载目录")
@click.option("--delay-min", default=2.0, help="最小延迟（秒）")
@click.option("--delay-max", default=5.0, help="最大延迟（秒）")
@click.pass_context
def cli(ctx, output_dir, delay_min, delay_max):
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = output_dir
    ctx.obj["delay_min"] = delay_min
    ctx.obj["delay_max"] = delay_max


@cli.command()
@click.option("--keywords", required=True, help="关键词，逗号分隔")
@click.option("--limit", default=100, help="最大爬取数量")
@click.pass_context
def zcool(ctx, keywords, limit):
    crawler = ZcoolCrawler(
        name="zcool",
        output_dir=ctx.obj["output_dir"],
        delay_min=ctx.obj["delay_min"],
        delay_max=ctx.obj["delay_max"],
    )
    kw_list = [k.strip() for k in keywords.split(",")]
    urls = crawler.search(kw_list, limit=limit)
    click.echo(f"Found {len(urls)} works, start crawling...")
    crawler.run(urls)
    crawler.close()
    click.echo("Done.")


if __name__ == "__main__":
    cli()
```

在 `pyproject.toml` 的 `[project.scripts]` 段添加：
```toml
[project.scripts]
meichen-crawler = "app.crawlers.cli:cli"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd python-ai && pytest app/crawlers/tests/test_cli.py -v
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add python-ai/app/crawlers/ python-ai/pyproject.toml
git commit -m "feat(crawler): add unified CLI entry with Click"
```

---

## Self-Review

1. **Spec coverage:** 反爬策略（延迟、UA、重试、去重、断点）✓，BaseCrawler 抽象 ✓，站酷实现 ✓，CLI ✓
2. **Placeholder scan:** 无 TBD/TODO/"implement later"
3. **Type consistency:** `BaseCrawler.parse/save` 签名一致，`items: list[dict[str, Any]]`
4. **Scope:** 本计划覆盖爬虫核心骨架（utils + base + zcool + CLI），公众号/1688/Pinterest 为 Phase 2 扩展

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2025-07-01-knowledge-base-crawler.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task
2. **Inline Execution** - execute tasks in this session using executing-plans

Which approach?
