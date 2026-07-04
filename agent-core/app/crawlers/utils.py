from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from app.models.database import SessionLocal, init_db
from app.models.crawler import CrawledUrl

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


def is_url_crawled(url: str, db_path: str = "") -> bool:
    init_db()
    db = SessionLocal()
    try:
        row = db.query(CrawledUrl).filter(CrawledUrl.url == url).first()
        return row is not None
    finally:
        db.close()


def mark_url_crawled(url: str, db_path: str = "") -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(CrawledUrl).filter(CrawledUrl.url == url).first()
        if not existing:
            db.add(CrawledUrl(url=url))
            db.commit()
    finally:
        db.close()


def load_progress(name: str, output_dir: str) -> dict[str, Any]:
    path = Path(output_dir) / f"{name}_progress.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_progress(name: str, data: dict[str, Any], output_dir: str) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{name}_progress.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
