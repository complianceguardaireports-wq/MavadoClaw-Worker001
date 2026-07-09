"""
MavadoClaw AI Infrastructure — Unified Failover Layer
Wraps OmniRoute + 9Router + Free Cascade
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

from plugins.free_cascade_router import FreeCascadeRouter
from plugins.omniroute_client import OmniRouteClient
from plugins.ninerouter_client import NineRouterFailoverManager

logger = logging.getLogger("ai_infra")


@dataclass
class InfraConfig:
    omniroute_url: str = os.getenv("OMNIROUTE_URL", "http://omniroute:3000")
    ninerouter_url: str = os.getenv("NINEROUTER_URL", "http://ninerouter:8081")
    use_cascade: bool = True


class AIInfrastructure:
    def __init__(self, config: Optional[InfraConfig] = None):
        self.config = config or InfraConfig()
        self.cascade = FreeCascadeRouter()
        self.omniroute = OmniRouteClient()
        self.failover = NineRouterFailoverManager(
            omniroute_url=self.config.omniroute_url,
            ninerouter_url=self.config.ninerouter_url,
        )

    async def chat(self, messages: list, **kwargs) -> dict:
        if self.config.use_cascade:
            return await self.cascade.chat(messages, **kwargs)
        try:
            return await self.omniroute.chat(messages, **kwargs)
        except Exception:
            return await self.failover.chat(messages, **kwargs)
