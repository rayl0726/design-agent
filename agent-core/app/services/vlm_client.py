from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.core.config import settings


class BaseVLMClient:
    async def describe(
        self,
        image_path: str | Path,
        prompt: str = "请详细描述这张图片中的场景、物体、颜色、材质和空间布局。",
        json_mode: bool = False,
    ) -> str:
        raise NotImplementedError

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


class OllamaVLMClient(BaseVLMClient):
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


class ZhipuVLMClient(BaseVLMClient):
    """智谱 GLM-4V-Flash 视觉模型客户端，兼容 OpenAI 接口。"""

    def __init__(
        self,
        api_key: str = settings.zhipu_api_key,
        base_url: str = settings.zhipu_base_url,
        model: str = settings.zhipu_vlm_model,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

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
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            print(f"Zhipu VLM HTTP error: {e.response.status_code} - {e.response.text[:300]}")
            raise
        except Exception as e:
            print(f"Zhipu VLM call failed: {type(e).__name__}: {e}")
            raise


def create_vlm_client() -> BaseVLMClient:
    # 固定使用智谱 VLM；不再 fallback 到本地 Ollama
    return ZhipuVLMClient()


vlm_client = create_vlm_client()
