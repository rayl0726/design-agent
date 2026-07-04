from __future__ import annotations

from pathlib import Path

from app.crawlers.base import BaseCrawler


class DummyCrawler(BaseCrawler):
    def parse(self, html: str) -> dict:
        return {"title": "dummy", "html_len": len(html), "images": []}

    def save(self, extracted: dict, raw_dir: Path) -> None:
        self.saved = extracted


def test_base_crawler_init():
    c = DummyCrawler(name="test", output_dir="/tmp/test_crawler")
    assert c.name == "test"
    assert c.delay_min == 2.0
    assert c.max_retries == 3


def test_base_crawler_dedup_skips_crawled(tmp_path: Path):
    c = DummyCrawler(name="test", output_dir=str(tmp_path))
    url = "https://example.com/a"
    c._mark_crawled(url)
    assert c._should_skip(url) is True


def test_base_crawler_local_raw_dir(tmp_path: Path):
    c = DummyCrawler(name="test", output_dir=str(tmp_path))
    raw_dir = c._local_raw_dir("https://example.com/page")
    assert raw_dir.name.startswith("20")
    assert "example" in str(raw_dir) or len(raw_dir.name) > 10
