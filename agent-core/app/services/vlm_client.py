from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.core.config import settings


class VLMClient:
    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_vlm_model,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    def _encode_image(self, image_path: str | Path) -> str:
        path = Path(image_path)
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def describe(
        self,
        image_path: str | Path,
        prompt: str = "请详细描述这张图片中的场景、物体、颜色、材质和空间布局。",
        json_mode: bool = False,
    ) -> str:
        image_b64 = self._encode_image(image_path)
        payload: dict = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        resp = await self.client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    async def describe_batch(
        self,
        image_paths: list[str | Path],
        prompt: str = "请详细描述这张图片中的场景、物体、颜色、材质和空间布局。",
    ) -> list[str]:
        results = []
        for path in image_paths:
            result = await self.describe(path, prompt)
            results.append(result)
        return results


vlm_client = VLMClient()
