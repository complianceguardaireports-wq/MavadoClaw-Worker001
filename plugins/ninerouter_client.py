"""
9Router Client — Backup AI Gateway Plugin
aiohttp-based backup/failover router with failover manager
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger("ninerouter")

NINEROUTER_URL = os.getenv("NINEROUTER_URL", "http://ninerouter:8081")
NINEROUTER_KEY = os.getenv("NINEROUTER_API_KEY", "local-autonomous-key")
NINEROUTER_TIMEOUT = int(os.getenv("NINEROUTER_TIMEOUT", "60"))


@dataclass
class NineRouterConfig:
    base_url: str = NINEROUTER_URL
    api_key: str = NINEROUTER_KEY
    timeout: int = NINEROUTER_TIMEOUT


class NineRouterClient:
    def __init__(self, config: Optional[NineRouterConfig] = None):
        self.config = config or NineRouterConfig()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def health_check(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.config.base_url}/health") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def chat(self, messages: list, model: str = "auto", temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        payload = {"model": model, "messages": messages, "stream": False, "temperature": temperature, "max_tokens": max_tokens}
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{self.config.base_url}/v1/chat/completions", json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"provider": "ninerouter", "model": model, "content": content}


class NineRouterFailoverManager:
    """Wraps OmniRoute as primary and 9Router as backup."""
    def __init__(self, omniroute_url: str = "http://omniroute:3000", ninerouter_url: str = "http://ninerouter:8081", api_key: str = ""):
        self.primary = NineRouterClient(NineRouterConfig(base_url=omniroute_url, api_key=api_key))
        self.backup = NineRouterClient(NineRouterConfig(base_url=ninerouter_url, api_key=api_key))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def chat(self, messages: list, **kwargs) -> dict:
        try:
            return await self.primary.chat(messages, **kwargs)
        except Exception as e:
            logger.warning(f"Primary router failed ({e}), falling back to 9Router")
            return await self.backup.chat(messages, **kwargs)
