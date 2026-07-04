from __future__ import annotations

import abc
import concurrent.futures
import hashlib
import json
import logging
import random
import time
from datetime import datetime
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
    """美陈设计知识库爬虫基础类，支持本地原始文件归档。"""

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

    def _local_raw_dir(self, url: str) -> Path:
        """为每个 URL 生成唯一的本地归档目录。"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / "raw" / self.name / f"{ts}_{url_hash}"

    def _save_raw_html(self, url: str, html: str) -> Path:
        """保存原始 HTML 到本地。"""
        raw_dir = self._local_raw_dir(url)
        raw_dir.mkdir(parents=True, exist_ok=True)
        html_path = raw_dir / "page.html"
        html_path.write_text(html, encoding="utf-8")
        return raw_dir

    def _save_raw_images(self, raw_dir: Path, images: list[dict[str, str]]) -> list[str]:
        """下载并保存原始图片到本地。"""
        img_dir = raw_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        local_paths: list[str] = []
        for idx, img_info in enumerate(images):
            img_url = img_info.get("url", "")
            if not img_url:
                continue
            try:
                ext = Path(img_url).suffix or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    ext = ".jpg"
                img_path = img_dir / f"{idx}{ext}"
                r = self.session.get(img_url, timeout=30)
                r.raise_for_status()
                img_path.write_bytes(r.content)
                local_paths.append(str(img_path))
                logger.info("[IMG] saved %s", img_path)
            except Exception:
                logger.warning("[IMG] failed %s", img_url)
        return local_paths

    def _save_meta(self, raw_dir: Path, url: str, extracted: dict[str, Any]) -> None:
        """保存元数据 JSON。"""
        meta = {
            "source": self.name,
            "url": url,
            "crawled_at": datetime.now().isoformat(),
            "extracted": extracted,
        }
        meta_path = raw_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

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
            raise RuntimeError(
                "playwright not installed. Run: pip install playwright && playwright install chromium"
            )

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
            page.mouse.move(random.randint(100, 500), random.randint(200, 600))
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
    def parse(self, html: str) -> dict[str, Any]:
        """解析 HTML，返回提取的结构化数据。"""
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
        raw_dir = self._save_raw_html(url, html)
        extracted = self.parse(html)
        images = extracted.pop("images", [])
        local_images = self._save_raw_images(raw_dir, images)
        extracted["local_images"] = local_images
        self._save_meta(raw_dir, url, extracted)
        self.save(extracted, raw_dir)
        self._mark_crawled(url)

    @abc.abstractmethod
    def save(self, extracted: dict[str, Any], raw_dir: Path) -> None:
        """将提取的数据写入业务数据库（SQLite / Milvus）。"""
        raise NotImplementedError
