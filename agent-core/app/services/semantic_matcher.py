from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from app.services.embedding_client import embedding_client
from app.services.taxonomy_loader import Taxonomy

EmbedFunc = Callable[[str], Awaitable[list[float]]]


class SemanticMatcher:
    def __init__(
        self,
        taxonomy: Taxonomy,
        threshold: float = 0.82,
        embed_func: EmbedFunc | None = None,
    ):
        self.taxonomy = taxonomy
        self.threshold = threshold
        self._embed_func = embed_func
        self._embedding_cache: dict[str, list[float]] = {}

    async def _embed(self, text: str) -> list[float]:
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        if self._embed_func is not None:
            emb = await self._embed_func(text)
        else:
            emb = await embedding_client.embed(text, use_cache=True)
        self._embedding_cache[text] = emb
        return emb

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        va = np.array(a)
        vb = np.array(b)
        norm = np.linalg.norm(va) * np.linalg.norm(vb)
        if norm == 0:
            return 0.0
        return float(np.dot(va, vb) / norm)

    async def match(
        self,
        text: str,
        field_type: str,
    ) -> tuple[str | None, float]:
        candidates = self._candidates_for_field(field_type)
        if not candidates:
            return None, 0.0

        query_emb = await self._embed(text)
        best_name: str | None = None
        best_score = 0.0
        for name, aliases in candidates:
            texts = [name, *aliases]
            scores: list[float] = []
            for t in texts:
                key = t.lower()
                emb = await self._embed(key)
                scores.append(self._cosine_similarity(query_emb, emb))
            score = max(scores)
            if score > best_score:
                best_score = score
                best_name = name

        if best_score >= self.threshold:
            return best_name, best_score
        return None, best_score

    def _candidates_for_field(self, field_type: str) -> list[tuple[str, list[str]]]:
        mapping: dict[str, list[dict[str, Any]]] = {
            "space_type": self.taxonomy.space_types,
            "point": self.taxonomy.points,
            "budget_level": self.taxonomy.budget_levels,
            "style": self.taxonomy.styles,
            "material": self.taxonomy.materials,
        }
        items = mapping.get(field_type, [])
        return [(item["name"], item.get("aliases", [])) for item in items]
