from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = settings.ollama_base_url, model: str = settings.ollama_text_model):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
            "keep_alive": "10m",
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = await self.client.post(f"{self.base_url}/api/chat", json=payload, timeout=300.0)
            print(f"DEBUG: LLM response status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            print(f"LLM HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return ""
        except httpx.TimeoutException as e:
            print(f"LLM timeout: {e}")
            return ""
        except Exception as e:
            print(f"LLM call failed: {type(e).__name__}: {e}")
            return ""

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


class LLMClient:
    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or OllamaProvider()

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return await self.provider.complete(system_prompt, user_prompt, json_mode, temperature)

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        async for chunk in self.provider.stream(system_prompt, user_prompt, temperature):
            yield chunk


llm_client = LLMClient()
