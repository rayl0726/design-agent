from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.services.call_logger import log_ai_call
from app.services.negative_prompt_builder import NegativePromptBuilder
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer


class ImageGenerationProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        raise NotImplementedError


class PollinationsProvider(ImageGenerationProvider):
    def __init__(self, base_url: str = settings.pollinations_base_url, timeout: int = settings.pollinations_timeout):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @log_ai_call("image_gen", "pollinations")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        # Pollinations 使用 URL 参数，添加重试以应对偶发 500
        encoded = quote(prompt)
        url = f"{self.base_url}/prompt/{encoded}?width=1024&height=576&nologo=true&seed=42&enhance=true"

        last_error = None
        for attempt in range(3):
            try:
                resp = await self.client.get(url)
                resp.raise_for_status()

                cache_dir = Path(settings.image_cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                content_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
                path = cache_dir / f"pollinations_{content_hash}.png"
                with open(path, "wb") as f:
                    f.write(resp.content)
                return path.name
            except Exception as e:
                last_error = e
                print(f"[PollinationsProvider] attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1.0 * (attempt + 1))
        raise last_error


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
        return path.name


class ZhipuProvider(ImageGenerationProvider):
    def __init__(
        self,
        api_key: str = settings.zhipu_api_key,
        base_url: str = settings.zhipu_base_url,
        model: str = settings.zhipu_image_model,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(180.0))

    @log_ai_call("image_gen", "zhipu")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        size = "1024x576" if aspect_ratio == "16:9" else "576x1024"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
        }
        print(f"[ZhipuProvider] generating image, model={self.model}, size={size}, prompt={prompt[:80]}...")
        resp = await self.client.post(
            f"{self.base_url}/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        print(f"[ZhipuProvider] response status={resp.status_code}, body={resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()
        image_url = data.get("data", [{}])[0].get("url", "")
        if not image_url:
            raise RuntimeError("智谱未返回图片 URL")

        # 下载图片到本地缓存
        print(f"[ZhipuProvider] downloading image from {image_url[:80]}...")
        img_resp = await self.client.get(image_url)
        print(f"[ZhipuProvider] download status={img_resp.status_code}, len={len(img_resp.content)}")
        img_resp.raise_for_status()
        cache_dir = Path(settings.image_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        path = cache_dir / f"zhipu_{content_hash}.png"
        with open(path, "wb") as f:
            f.write(img_resp.content)
        print(f"[ZhipuProvider] saved to {path}")
        return path.name


class SiliconFlowProvider(ImageGenerationProvider):
    def __init__(
        self,
        api_key: str = settings.siliconflow_api_key,
        base_url: str = settings.siliconflow_base_url,
        model: str = settings.siliconflow_image_model,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(180.0))

    @log_ai_call("image_gen", "siliconflow")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        size = "1024x576" if aspect_ratio == "16:9" else "576x1024"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": size,
        }
        print(f"[SiliconFlowProvider] generating image, model={self.model}, size={size}, prompt={prompt[:80]}...")
        resp = await self.client.post(
            f"{self.base_url}/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        print(f"[SiliconFlowProvider] response status={resp.status_code}, body={resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()
        images = data.get("images", [])
        if not images:
            raise RuntimeError("SiliconFlow 未返回图片 URL")
        image_url = images[0].get("url", "")
        if not image_url:
            raise RuntimeError("SiliconFlow 未返回图片 URL")

        # 下载图片到本地缓存
        print(f"[SiliconFlowProvider] downloading image from {image_url[:80]}...")
        img_resp = await self.client.get(image_url)
        print(f"[SiliconFlowProvider] download status={img_resp.status_code}, len={len(img_resp.content)}")
        img_resp.raise_for_status()
        cache_dir = Path(settings.image_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        path = cache_dir / f"siliconflow_{content_hash}.png"
        with open(path, "wb") as f:
            f.write(img_resp.content)
        print(f"[SiliconFlowProvider] saved to {path}")
        return path.name


class ImageGenerationService:
    def __init__(self):
        self.providers = [
            SiliconFlowProvider(),
            ZhipuProvider(),
            PollinationsProvider(),
            ComfyUIProvider(),
            PlaceholderProvider(),
        ]
        self._template_loader = PromptTemplateLoader()
        self._template_renderer = PromptTemplateRenderer()
        self._negative_builder = NegativePromptBuilder()

    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
        last_error = None
        for provider in self.providers:
            provider_name = type(provider).__name__
            try:
                print(f"[ImageGenerationService] trying {provider_name}...")
                path = await provider.generate(prompt, aspect_ratio, style)
                print(f"[ImageGenerationService] {provider_name} succeeded: {path}")
                return path
            except Exception as e:
                last_error = e
                print(f"[ImageGenerationService] {provider_name} failed: {e}")
                continue
        raise RuntimeError(f"所有图像生成提供者均失败: {last_error}")

    async def generate_from_intent(
        self,
        intent: dict,
        template_version: str | None = None,
        aspect_ratio: str = "16:9",
        style: str = "realistic",
    ) -> dict:
        """Render prompt from intent and generate image. Returns metadata dict."""
        if template_version:
            template = self._template_loader.load(template_version)
            space_type = intent.get("space_type")
            negative = self._negative_builder.build(
                space_type=space_type,
                user_negative=intent.get("negative_prompts"),
            )
            rendered = await self._template_renderer.render(
                template,
                {**intent, "negative_prompts": negative.split(", ") if negative else []},
            )
            prompt = rendered.positive
            final_negative = rendered.negative
        else:
            prompt = self._legacy_prompt(intent)
            final_negative = self._negative_builder.build(
                space_type=intent.get("space_type"),
                user_negative=intent.get("negative_prompts"),
            )
            rendered = None

        filename = await self.generate(prompt, aspect_ratio, style)
        return {
            "filename": filename,
            "prompt": prompt,
            "negative_prompt": final_negative,
            "template_version": rendered.version if rendered else None,
            "aspect_ratio": aspect_ratio,
        }

    def _legacy_prompt(self, intent: dict) -> str:
        parts = [
            f"Commercial display design for {intent.get('space_type', 'commercial space')}",
        ]
        if intent.get("theme"):
            parts.append(f"theme: {intent['theme']}")
        if intent.get("style"):
            parts.append(f"style: {intent['style']}")
        if intent.get("budget_level"):
            parts.append(f"budget level: {intent['budget_level']}")
        return ", ".join(parts)


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
