from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol, cast

import httpx
import numpy as np

from app.core.config import settings
from app.services.call_logger import log_ai_call


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class OllamaEmbeddingProvider:
    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_embedding_model,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

    @log_ai_call("embedding", "ollama")
    async def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        resp = await self.client.post(f"{self.base_url}/api/embeddings", json=payload)
        resp.raise_for_status()
        data = resp.json()
        embedding = cast(list[float], data.get("embedding"))
        if not embedding:
            raise ValueError(f"Ollama returned empty embedding for: {text[:50]}...")
        return embedding


class ZhipuEmbeddingProvider:
    """智谱 Embedding-3 客户端，兼容 OpenAI 接口。"""

    def __init__(
        self,
        api_key: str = settings.zhipu_api_key,
        base_url: str = settings.zhipu_base_url,
        model: str = settings.zhipu_embedding_model,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    async def embed(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "input": text,
        }
        try:
            resp = await self.client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = cast(list[float], data.get("data", [{}])[0].get("embedding"))
            if not embedding:
                raise ValueError(f"Zhipu returned empty embedding for: {text[:50]}...")
            return embedding
        except httpx.HTTPStatusError as e:
            print(f"Zhipu Embedding HTTP error: {e.response.status_code} - {e.response.text[:300]}")
            raise
        except Exception as e:
            print(f"Zhipu Embedding call failed: {type(e).__name__}: {e}")
            raise


class EmbeddingClient:
    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        cache_dir: str = settings.image_cache_dir,
    ):
        self.provider = provider or self._default_provider()
        self.cache_dir = Path(cache_dir).parent / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _default_provider(self) -> EmbeddingProvider | None:
        try:
            provider = settings.embedding_provider.lower()
            if provider == "zhipu":
                return ZhipuEmbeddingProvider()
            return OllamaEmbeddingProvider()
        except Exception:
            return None

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    async def embed(self, text: str, use_cache: bool = True) -> list[float]:
        if not self.provider:
            raise ValueError("Embedding provider not configured")

        if use_cache:
            key = self._cache_key(text)
            cache_file = self._cache_path(key)
            if cache_file.exists():
                with open(cache_file, encoding="utf-8") as f:
                    return cast(list[float], json.load(f))

        embedding = await self.provider.embed(text)

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
