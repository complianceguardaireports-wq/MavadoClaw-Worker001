"""
OmniRoute Client — Primary AI Gateway Plugin
httpx-based, retries, model cache, health check
"""
import asyncio
import logging
import os
from typing import Optional, List

import aiohttp

logger = logging.getLogger("omniroute")

OMNIROUTE_URL = os.getenv("OMNIROUTE_URL", "http://omniroute:3000")
OMNIROUTE_KEY = os.getenv("OMNIROUTE_API_KEY", "local-autonomous-key")
OMNIROUTE_RETRIES = int(os.getenv("OMNIROUTE_RETRIES", "3"))
OMNIROUTE_TIMEOUT = int(os.getenv("OMNIROUTE_TIMEOUT", "120"))


class OmniRouteClient:
    def __init__(self):
        self.base_url = OMNIROUTE_URL
        self.api_key = OMNIROUTE_KEY
        self._healthy: Optional[bool] = None
        self._model_cache: List[str] = []

    async def health_check(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    self._healthy = resp.status == 200
                    return self._healthy
        except Exception:
            self._healthy = False
            return False

    async def list_models(self) -> List[str]:
        if self._model_cache:
            return self._model_cache
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(f"{self.base_url}/v1/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._model_cache = [m["id"] for m in data.get("data", [])]
                        return self._model_cache
        except Exception as e:
            logger.debug(f"OmniRoute model list failed: {e}")
        return []

    async def chat(self, messages: list, model: str = "auto", temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"model": model, "messages": messages, "stream": False, "temperature": temperature, "max_tokens": max_tokens}
        last_err = None
        for attempt in range(OMNIROUTE_RETRIES):
            try:
                timeout = aiohttp.ClientTimeout(total=OMNIROUTE_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{self.base_url}/v1/chat/completions", json=payload, headers=headers) as resp:
                        if resp.status >= 400:
                            last_err = f"HTTP {resp.status}"
                            await asyncio.sleep(2 ** attempt)
                            continue
                        data = await resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return {"provider": "omniroute", "model": model, "content": content}
            except Exception as e:
                last_err = str(e)
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"OmniRoute failed after {OMNIROUTE_RETRIES} attempts: {last_err}")
