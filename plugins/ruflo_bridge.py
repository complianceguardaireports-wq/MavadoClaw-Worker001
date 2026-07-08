"""
MavadoClaw Ruflo Bridge — Swarm Queen Connector
Connects to Ruflo swarm at port 7070 (if running)
Falls back gracefully if Ruflo is not deployed
"""
import asyncio
import logging
import os

import aiohttp

logger = logging.getLogger("ruflo")

RUFLO_URL = os.getenv("RUFLO_URL", "http://ruflo:7070")
RUFLO_KEY = os.getenv("RUFLO_API_KEY", "")


class RufloSwarmBridge:
    def __init__(self):
        self.base_url = RUFLO_URL
        self._available: bool = False

    async def check_availability(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    self._available = resp.status == 200
        except Exception:
            self._available = False
        return self._available

    async def dispatch_worker(self, task: dict) -> dict:
        if not self._available:
            await self.check_availability()
        if not self._available:
            return {"status": "ruflo_unavailable", "fallback": "using_cascade_router"}
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {"Content-Type": "application/json"}
                if RUFLO_KEY:
                    headers["Authorization"] = f"Bearer {RUFLO_KEY}"
                async with session.post(f"{self.base_url}/api/dispatch", json=task, headers=headers) as resp:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Ruflo dispatch failed: {e}")
            return {"status": "error", "message": str(e)}

    async def get_swarm_status(self) -> dict:
        if not self._available:
            return {"status": "offline", "workers": []}
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/api/workers") as resp:
                    return await resp.json()
        except Exception:
            return {"status": "error"}


ruflo = RufloSwarmBridge()
