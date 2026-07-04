import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings


class ImageGenerationProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        raise NotImplementedError


class PollinationsProvider(ImageGenerationProvider):
    def __init__(self, base_url: str = settings.pollinations_base_url, timeout: int = settings.pollinations_timeout):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        # Pollinations 使用 URL 参数
        encoded = quote(prompt)
        url = f"{self.base_url}/prompt/{encoded}?width=1024&height=576&nologo=true&seed=42&enhance=true"
        resp = await self.client.get(url)
        resp.raise_for_status()

        # 保存图片
        cache_dir = Path(settings.image_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        path = cache_dir / f"pollinations_{content_hash}.png"
        with open(path, "wb") as f:
            f.write(resp.content)
        return str(path)


class ComfyUIProvider(ImageGenerationProvider):
    def __init__(self, base_url: str = settings.comfyui_base_url):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        # ComfyUI 占位实现，实际需对接工作流 API
        payload = {"prompt": prompt, "aspect_ratio": aspect_ratio, "style": style}
        resp = await self.client.post(f"{self.base_url}/prompt", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # 假设返回图片路径
        return data.get("image_path", "")


class PlaceholderProvider(ImageGenerationProvider):
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        from PIL import Image, ImageDraw, ImageFont

        cache_dir = Path(settings.image_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        path = cache_dir / f"placeholder_{content_hash}.png"

        width, height = (1024, 576) if aspect_ratio == "16:9" else (576, 1024)
        img = Image.new("RGB", (width, height), "#E0E0E0")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
        except Exception:
            font = ImageFont.load_default()

        text = f"[占位图]\n{prompt[:60]}..."
        draw.text((width // 2 - 200, height // 2 - 30), text, fill="#888888", font=font)
        img.save(path)
        return str(path)


class ImageGenerationService:
    def __init__(self):
        self.providers = [
            PollinationsProvider(),
            ComfyUIProvider(),
            PlaceholderProvider(),
        ]

    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        last_error = None
        for provider in self.providers:
            try:
                return await provider.generate(prompt, aspect_ratio, style)
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"所有图像生成提供者均失败: {last_error}")


image_generation = ImageGenerationService()


async def generate_images_with_fallback(prompts: list[str], aspect_ratio: str = "16:9", style: str = "realistic") -> list[str]:
    results = []
    for prompt in prompts:
        try:
            path = await image_generation.generate(prompt, aspect_ratio, style)
            results.append(path)
        except Exception:
            results.append("")
    return results
