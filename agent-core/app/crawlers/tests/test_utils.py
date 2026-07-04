from __future__ import annotations

import time
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
