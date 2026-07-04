import hashlib
import json
from pathlib import Path

import httpx
import numpy as np

from app.core.config import settings


class EmbeddingClient:
    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_embedding_model,
        cache_dir: str = settings.image_cache_dir,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        self.cache_dir = Path(cache_dir).parent / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    async def _fetch(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        resp = await self.client.post(f"{self.base_url}/api/embeddings", json=payload)
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding")
        if not embedding:
            raise ValueError(f"Ollama returned empty embedding for: {text[:50]}...")
        return embedding

    async def embed(self, text: str, use_cache: bool = True) -> list[float]:
        if use_cache:
            key = self._cache_key(text)
            cache_file = self._cache_path(key)
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)

        embedding = await self._fetch(text)

        if use_cache:
            key = self._cache_key(text)
            cache_file = self._cache_path(key)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(embedding, f)

        return embedding

    async def embed_batch(self, texts: list[str], use_cache: bool = True) -> list[list[float]]:
        results = []
        for text in texts:
            emb = await self.embed(text, use_cache=use_cache)
            results.append(emb)
        return results

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        va = np.array(a)
        vb = np.array(b)
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


embedding_client = EmbeddingClient()
