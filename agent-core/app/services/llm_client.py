from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

import httpx

from app.core.config import settings
from app.services.call_logger import log_ai_call


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)


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

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Optional tool-aware chat. Default implementation falls back to complete()."""
        text = await self.complete(system_prompt, user_prompt, json_mode=False, temperature=temperature)
        return LLMResponse(content=text)

    async def chat_complete(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        """给定完整 messages 列表完成一次对话。默认实现取首条 system 与首个 user 消息回退到 complete()。"""
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            elif msg.get("role") == "user":
                user_prompt = msg.get("content", "")
                break
        return await self.complete(system_prompt, user_prompt, json_mode=json_mode, temperature=temperature)


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

    async def chat_complete(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
            "keep_alive": "10m",
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = await self.client.post(
                f"{self.base_url}/api/chat", json=payload, timeout=300.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            print(f"LLM chat_complete error: {type(e).__name__}: {e}")
            return ""


class ZhipuProvider(LLMProvider):
    """智谱 AI (GLM) API Provider，兼容 OpenAI 接口格式。"""

    def __init__(
        self,
        api_key: str = settings.zhipu_api_key,
        base_url: str = settings.zhipu_base_url,
        model: str = settings.zhipu_model,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(180.0))

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @log_ai_call("llm", "zhipu")
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        self._last_usage = None
        payload: dict = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "stream": False,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        max_retries = 3
        backoff_factor = 1.0
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=180.0,
                )
                print(f"DEBUG: Zhipu response status: {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                usage = data.get("usage", {})
                self._last_usage = usage
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                print(f"Zhipu HTTP error: {status_code} - {e.response.text[:300]}")
                if status_code == 429 and attempt < max_retries:
                    wait = backoff_factor * (2 ** attempt)
                    print(f"Zhipu rate limited; retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
            except httpx.TimeoutException as e:
                last_exception = e
                print(f"Zhipu timeout: {e}")
                if attempt < max_retries:
                    wait = backoff_factor * (2 ** attempt)
                    print(f"Zhipu timeout; retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception as e:
                print(f"Zhipu call failed: {type(e).__name__}: {e}")
                raise

        if last_exception:
            raise last_exception
        return ""

    @log_ai_call("llm", "zhipu")
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "stream": False,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        resp = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=180.0,
        )
        print(f"DEBUG: Zhipu chat response status: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []
        return LLMResponse(content=content, tool_calls=tool_calls)

    @log_ai_call("llm", "zhipu")
    async def chat_complete(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        max_retries = 3
        backoff_factor = 1.0
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=180.0,
                )
                print(f"DEBUG: Zhipu chat_complete response status: {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                usage = data.get("usage", {})
                self._last_usage = usage
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                print(f"Zhipu HTTP error: {status_code} - {e.response.text[:300]}")
                if status_code == 429 and attempt < max_retries:
                    wait = backoff_factor * (2 ** attempt)
                    print(f"Zhipu rate limited; retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
            except httpx.TimeoutException as e:
                last_exception = e
                print(f"Zhipu timeout: {e}")
                if attempt < max_retries:
                    wait = backoff_factor * (2 ** attempt)
                    print(f"Zhipu timeout; retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception as e:
                print(f"Zhipu chat_complete failed: {type(e).__name__}: {e}")
                raise

        if last_exception:
            raise last_exception
        return ""

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "stream": True,
            "temperature": temperature,
        }
        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip() or line.strip() == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                try:
                    chunk = json.loads(line)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


class LLMClient:
    """统一 LLM 客户端，支持 provider 选择和自动 fallback。"""

    def __init__(self, primary_provider: LLMProvider | None = None):
        # 默认根据配置选择 primary provider；不再设置本地 Ollama fallback
        self.primary_provider = primary_provider or self._create_provider(settings.llm_provider)

    @staticmethod
    def _create_provider(provider_name: str) -> LLMProvider:
        if provider_name.lower() == "zhipu":
            return ZhipuProvider()
        return OllamaProvider()

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        # 仅使用主 provider；失败直接抛出异常，不再 fallback 到本地 Ollama
        return await self.primary_provider.complete(
            system_prompt, user_prompt, json_mode, temperature
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        # 仅使用主 provider；失败直接抛出异常
        async for chunk in self.primary_provider.stream(system_prompt, user_prompt, temperature):
            if chunk:
                yield chunk

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        return await self.primary_provider.chat(
            system_prompt, user_prompt, tools, temperature
        )

    async def chat_complete(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        return await self.primary_provider.chat_complete(
            messages, json_mode, temperature
        )


llm_client = LLMClient()
