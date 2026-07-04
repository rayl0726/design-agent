from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

DISCOVER_URL = "https://www.zcool.com.cn/discover?cate=1&subCate=0&page={page}"


class ZcoolCrawler(BaseCrawler):
    """站酷作品爬虫，支持本地归档 + 结构化入库。"""

    def _discover_urls(self, page_num: int) -> list[str]:
        """使用 Playwright 抓取发现页，滚动触发懒加载后提取作品链接。"""
        from playwright.sync_api import sync_playwright
        from app.crawlers.utils import get_random_ua, random_delay

        url = DISCOVER_URL.format(page=page_num)
        urls: list[str] = []

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
            page.wait_for_timeout(5000)
            # 滚动触发懒加载
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(3000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/work/" in href:
                    detail = urljoin("https://www.zcool.com.cn", href)
                    if detail not in urls:
                        urls.append(detail)
        finally:
            context.close()
        return urls

    def search(self, keywords: list[str], limit: int = 100) -> list[str]:
        """keywords 仅作日志记录，实际抓取发现页全量作品。"""
        urls: list[str] = []
        page = 1
        while len(urls) < limit:
            try:
                found = self._discover_urls(page)
                for u in found:
                    if u not in urls:
                        urls.append(u)
                    if len(urls) >= limit:
                        break
                if not found:
                    break
                page += 1
            except Exception:
                logger.exception("[SEARCH] discover page=%d", page)
                break
        logger.info("[SEARCH] keywords=%s total=%d", keywords, len(urls))
        return urls[:limit]

    def parse(self, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        # 标题：优先 h1.contentTitle，其次 title 标签
        title = ""
        h1 = soup.select_one("h1.contentTitle")
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True).split("_")[0]

        # 作者：优先 section.detail-head-user，其次 a.cardUser
        author = ""
        author_section = soup.select_one("section.detail-head-user")
        if author_section:
            author = author_section.get_text(strip=True).split("/")[0].split("广州")[0]
        if not author:
            card_user = soup.select_one("a.cardUser")
            if card_user:
                author = card_user.get_text(strip=True)

        # 描述：优先 meta description，其次 JSON-LD
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "").split(",")[0]

        # 图片：优先 og:image，其次页面内 zcool 图片
        images = []
        for meta in soup.find_all("meta", property="og:image"):
            src = meta.get("content")
            if src:
                images.append({"url": src, "alt": title})
        if not images:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src and "zcool.cn" in src and src.startswith("http"):
                    images.append({"url": src, "alt": img.get("alt", "")})

        if not title:
            return {"title": "", "author": "", "description": "", "images": []}

        return {
            "title": title,
            "author": author,
            "description": description,
            "images": images,
        }

    def save(self, extracted: dict[str, Any], raw_dir: Path) -> None:
        # 读取 meta.json 中的 URL
        meta_path = raw_dir / "meta.json"
        source_url = ""
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                source_url = meta.get("url", "")
            except Exception:
                pass

        # 1) 追加到本地 JSONL
        jsonl_path = Path("/Users/liulei/private-work/design-data/extracted/cases.jsonl")
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        record = dict(extracted)
        record["source_url"] = source_url
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 2) 写入 SQLite
        try:
            from app.models.database import SessionLocal
            from app.models.project import DesignCase

            db = SessionLocal()
            case = DesignCase(
                title=extracted.get("title", "") or "未知标题",
                space_type="",
                budget_level="",
                theme="",
                style="",
                summary=(extracted.get("description", "") or "")[:500],
                images_json=json.dumps(extracted.get("local_images", [])),
                source_url=source_url,
            )
            db.add(case)
            db.commit()
            db.close()
            logger.info("[DB] saved case: %s", extracted.get("title", "")[:50])
        except Exception:
            logger.exception("[DB] failed to save case")

        # 3) 写入 Milvus（可选，失败不阻断）
        try:
            from app.services.embedding_client import embedding_client
            from app.services.knowledge_base import knowledge_base

            text = extracted.get("description", "") or extracted.get("title", "")
            if text:
                embedding = embedding_client.embed(text)
                collection = knowledge_base._get_case_collection()
                logger.info("[MILVUS] skip direct insert, will ingest via admin CLI")
        except Exception:
            logger.info("[MILVUS] not available, skipping")
