from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.core.config import settings


@dataclass
class IntentCorrectionRecord:
    intent_field: str
    original_value: str
    corrected_value: str
    count: int


@dataclass
class ImageFeedbackRecord:
    category: str
    tag: str
    point_name: str | None
    image_index: int | None
    prompt_template_version: str | None
    comment: str | None


class FeedbackReader:
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url
        self._conn_params = self._build_conn_params()

    def _build_conn_params(self) -> dict[str, Any]:
        return {
            "host": settings.mysql_host,
            "port": settings.mysql_port,
            "user": settings.mysql_username,
            "password": settings.mysql_password,
            "database": settings.mysql_db,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
        }

    async def list_unprocessed_intent_corrections(self) -> list[IntentCorrectionRecord]:
        query = """
            SELECT intent_field, original_value, corrected_value, COUNT(*) AS count
            FROM feedbacks
            WHERE feedback_type = 'intent'
              AND processed = FALSE
            GROUP BY intent_field, original_value, corrected_value
            ORDER BY count DESC
        """
        rows = await self._execute(query)
        return [
            IntentCorrectionRecord(
                intent_field=r["intent_field"],
                original_value=r["original_value"],
                corrected_value=r["corrected_value"],
                count=int(r["count"]),
            )
            for r in rows
        ]

    async def list_image_feedback_by_version(self, version: str) -> list[ImageFeedbackRecord]:
        query = """
            SELECT category, tag, point_name, image_index, prompt_template_version, comment
            FROM feedbacks
            WHERE feedback_type = 'image'
              AND prompt_template_version = %s
            ORDER BY created_at DESC
        """
        rows = await self._execute(query, (version,))
        return [ImageFeedbackRecord(**r) for r in rows]

    async def _execute(self, query: str, params: tuple | None = None) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, params)

    def _execute_sync(self, query: str, params: tuple | None = None) -> list[dict]:
        conn = pymysql.connect(**self._conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.fetchall()
        finally:
            conn.close()
