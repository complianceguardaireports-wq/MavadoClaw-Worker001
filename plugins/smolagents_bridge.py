"""
MavadoClaw smolagents Computer-Use Bridge
Integrates HuggingFace smolagents/computer-use-agent as a GUI automation sub-agent.
Called by CEO when tasks require screen interaction, browser automation, or GUI control.

Reference: https://huggingface.co/spaces/smolagents/computer-use-agent
"""
import asyncio
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("computer_use")

SMOLAGENTS_URL = os.getenv("SMOLAGENTS_URL", "http://smolagents:7860")
SMOLAGENTS_HF_SPACE = os.getenv("SMOLAGENTS_HF_SPACE", "")


class ComputerUseAgent:
    """
    Vision-capable agent that controls a full desktop via screenshots + mouse/keyboard.
    Backed by smolagents framework with Qwen2-VL or equivalent vision model.
    
    Integration modes:
    1. Local Docker container (smolagents running at port 7860)
    2. HuggingFace Space API (remote inference via Gradio client)
    3. Direct smolagents SDK (if installed in same container)
    """

    def __init__(self):
        self.local_url = SMOLAGENTS_URL
        self.hf_space = SMOLAGENTS_HF_SPACE
        self._available: Optional[bool] = None

    async def check_availability(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.local_url}/health") as resp:
                    self._available = resp.status == 200
        except Exception:
            self._available = False
        logger.info(f"Computer-use agent available: {self._available}")
        return self._available

    async def execute_task(self, task: str, screenshot_url: Optional[str] = None) -> dict:
        """
        Execute a computer-use task.
        task: Natural language instruction e.g. "Open browser, go to github.com, click Sign In"
        screenshot_url: Optional current screenshot to provide context
        """
        available = await self.check_availability()

        if not available:
            logger.warning("Computer-use agent offline — returning stub response")
            return {
                "status": "unavailable",
                "task": task,
                "message": "Deploy smolagents container to enable GUI automation. "
                           "See: https://huggingface.co/spaces/smolagents/computer-use-agent",
                "setup": {
                    "docker": "docker run -p 7860:7860 -e HF_TOKEN=$HF_TOKEN huggingface/smolagents-computer-use",
                    "env": "SMOLAGENTS_URL=http://smolagents:7860",
                }
            }

        try:
            timeout = aiohttp.ClientTimeout(total=120)
            payload = {"task": task}
            if screenshot_url:
                payload["screenshot_url"] = screenshot_url
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.local_url}/api/execute", json=payload) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"status": "error", "http_status": resp.status}
        except asyncio.TimeoutError:
            return {"status": "timeout", "task": task}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_capabilities(self) -> dict:
        return {
            "name": "smolagents computer-use-agent",
            "source": "https://huggingface.co/spaces/smolagents/computer-use-agent",
            "capabilities": [
                "Full desktop control via vision + mouse/keyboard",
                "Browser automation without Selenium/Playwright code",
                "GUI app interaction",
                "Screenshot-based task execution",
                "Web scraping via visual navigation",
                "Form filling and clicking",
            ],
            "recommended_model": "Qwen2-VL-72B-Instruct or Llama-3.2-11B-Vision",
            "vram_requirement": "24GB+ for 72B vision model, 8GB for 11B",
            "integration": "wired as sub-agent — CEO routes GUI tasks here automatically",
            "status": "available" if self._available else "offline_deploy_to_activate",
        }


computer_use = ComputerUseAgent()
