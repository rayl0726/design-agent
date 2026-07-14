from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.config import settings
from app.models.database import get_session
from app.models.project import DesignCase, MaterialPrice
from app.services.embedding_client import embedding_client
from app.services.rag_logger import log_rag_search, log_rag_search_sync


class KnowledgeBase:
    def __init__(self):
        self._client = None
        self._milvus_available = None

    def _ensure_client(self):
        if self._milvus_available is not None:
            return
        try:
            from pymilvus import MilvusClient
            self._client = MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")
            self._ensure_collections()
            self._milvus_available = True
        except Exception:
            self._milvus_available = False

    def _ensure_connection(self):
        from pymilvus import MilvusClient
        self._client = MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")

    def _ensure_collections(self):
        self._ensure_case_collection()
        self._ensure_image_collection()

    def _ensure_case_collection(self):
        name = settings.milvus_collection_cases
        if self._client.has_collection(name):
            return
        schema = {
            "fields": [
                {"name": "id", "type": "VARCHAR", "max_length": 36, "is_primary": True},
                {"name": "embedding", "type": "FLOAT_VECTOR", "dim": 1024},
                {"name": "title", "type": "VARCHAR", "max_length": 500},
                {"name": "space_type", "type": "VARCHAR", "max_length": 100},
                {"name": "budget_level", "type": "VARCHAR", "max_length": 20},
                {"name": "theme", "type": "VARCHAR", "max_length": 200},
                {"name": "style", "type": "VARCHAR", "max_length": 200},
                {"name": "summary", "type": "VARCHAR", "max_length": 4000},
            ],
            "description": "设计案例语义检索",
        }
        self._client.create_collection(name=name, schema=schema)
        self._client.create_index(
            collection_name=name,
            field_name="embedding",
            index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
        )

    def _ensure_image_collection(self):
        name = settings.milvus_collection_images
        if self._client.has_collection(name):
            return
        schema = {
            "fields": [
                {"name": "id", "type": "VARCHAR", "max_length": 36, "is_primary": True},
                {"name": "embedding", "type": "FLOAT_VECTOR", "dim": 1024},
                {"name": "description", "type": "VARCHAR", "max_length": 4000},
                {"name": "source_case_id", "type": "VARCHAR", "max_length": 36},
                {"name": "image_path", "type": "VARCHAR", "max_length": 1000},
            ],
            "description": "图片语义检索",
        }
        self._client.create_collection(name=name, schema=schema)
        self._client.create_index(
            collection_name=name,
            field_name="embedding",
            index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
        )

    async def semantic_search(
        self,
        query: str,
        space_type: str | None = None,
        budget_level: str | None = None,
        top_k: int = 5,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        start = time.monotonic()
        try:
            self._ensure_client()
            if self._milvus_available:
                try:
                    embedding = await embedding_client.embed(query)
                    expr_parts = []
                    if space_type:
                        expr_parts.append(f'space_type == "{space_type}"')
                    if budget_level:
                        expr_parts.append(f'budget_level == "{budget_level}"')
                    expr = " and ".join(expr_parts) if expr_parts else ""

                    results = self._client.search(
                        collection_name=settings.milvus_collection_cases,
                        data=[embedding],
                        anns_field="embedding",
                        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
                        limit=top_k,
                        expr=expr or None,
                        output_fields=["title", "space_type", "budget_level", "theme", "style", "summary"],
                    )
                    hits = []
                    for result in results[0]:
                        hits.append(
                            {
                                "id": result.id,
                                "distance": result.distance,
                                "title": result.entity.get("title"),
                                "space_type": result.entity.get("space_type"),
                                "budget_level": result.entity.get("budget_level"),
                                "theme": result.entity.get("theme"),
                                "style": result.entity.get("style"),
                                "summary": result.entity.get("summary"),
                            }
                        )
                    duration_ms = int((time.monotonic() - start) * 1000)
                    await log_rag_search(
                        project_id=project_id,
                        query_text=query,
                        search_type="semantic",
                        result_count=len(hits),
                        duration_ms=duration_ms,
                        cache_hit=False,
                        timed_out=False,
                    )
                    return hits
                except Exception:
                    fallback_results = self._fallback_search(query, space_type, budget_level, top_k)
                    duration_ms = int((time.monotonic() - start) * 1000)
                    await log_rag_search(
                        project_id=project_id,
                        query_text=query,
                        search_type="fallback",
                        result_count=len(fallback_results),
                        duration_ms=duration_ms,
                        cache_hit=False,
                        timed_out=True,
                    )
                    return fallback_results
            else:
                results = self._fallback_search(query, space_type, budget_level, top_k)
                duration_ms = int((time.monotonic() - start) * 1000)
                await log_rag_search(
                    project_id=project_id,
                    query_text=query,
                    search_type="fallback",
                    result_count=len(results),
                    duration_ms=duration_ms,
                    cache_hit=False,
                    timed_out=False,
                )
                return results
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            await log_rag_search(
                project_id=project_id,
                query_text=query,
                search_type="semantic",
                result_count=0,
                duration_ms=duration_ms,
                cache_hit=False,
                timed_out=True,
            )
            return []

    def _fallback_search(
        self,
        query: str,
        space_type: str | None = None,
        budget_level: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        db = get_session()
        try:
            query_obj = db.query(DesignCase)
            if space_type:
                query_obj = query_obj.filter(DesignCase.space_type == space_type)
            if budget_level:
                query_obj = query_obj.filter(DesignCase.budget_level == budget_level)
            
            query_words = query.split()
            for word in query_words:
                query_obj = query_obj.filter(
                    (DesignCase.title.contains(word)) |
                    (DesignCase.summary.contains(word)) |
                    (DesignCase.theme.contains(word)) |
                    (DesignCase.style.contains(word))
                )
            
            rows = query_obj.limit(top_k).all()
            return [
                {
                    "id": r.id,
                    "distance": 0.0,
                    "title": r.title,
                    "space_type": r.space_type,
                    "budget_level": r.budget_level,
                    "theme": r.theme,
                    "style": r.style,
                    "summary": r.summary,
                }
                for r in rows
            ]
        finally:
            db.close()

    def structured_query(
        self,
        material_name: str | None = None,
        category: str | None = None,
        limit: int = 10,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        start = time.monotonic()
        db = get_session()
        try:
            query = db.query(MaterialPrice)
            if material_name:
                query = query.filter(MaterialPrice.name.contains(material_name))
            if category:
                query = query.filter(MaterialPrice.category == category)
            rows = query.limit(limit).all()
            results = [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "spec": r.spec,
                    "unit": r.unit,
                    "price_low": r.price_low,
                    "price_high": r.price_high,
                    "supplier_hint": r.supplier_hint,
                }
                for r in rows
            ]
            duration_ms = int((time.monotonic() - start) * 1000)
            # Fire-and-forget logging. structured_query is sync and may be
            # called from either an async context or a thread pool thread
            # (via loop.run_in_executor in knowledge_retrieval.py), so use the
            # sync wrapper that handles both cases.
            log_rag_search_sync(
                project_id=project_id,
                query_text=material_name or category or "structured_query",
                search_type="structured",
                result_count=len(results),
                duration_ms=duration_ms,
                cache_hit=False,
                timed_out=False,
            )
            return results
        finally:
            db.close()


knowledge_base = KnowledgeBase()


async def search(
    query: str,
    top_k: int = 5,
    agent_type: str | None = None,
) -> list[dict[str, Any]]:
    """Tool-style entry point for knowledge base semantic search.

    The ``agent_type`` parameter is accepted so callers can pass runtime
    context; it is reserved for future per-agent filtering and currently
    does not change the search behavior.
    """
    try:
        return await asyncio.wait_for(
            knowledge_base.semantic_search(query=query, top_k=top_k),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.warning("Knowledge base search timed out after 30s: query=%r", query)
        return []
