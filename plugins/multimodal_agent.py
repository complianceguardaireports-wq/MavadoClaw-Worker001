"""
MavadoClaw Multimodal Agent — Vision + Text tasks
Wraps smolagents computer-use agent and vision-capable LLMs.
Handles image analysis, screenshot tasks, GUI automation.
"""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("multimodal")


class MultiModalAgent:
    """
    Vision + Text agent.
    - Attempts smolagents computer-use agent if available
    - Falls back to LLM vision API (gemini, gpt-4o)
    - Final fallback: text-only response
    """

    def __init__(self, router, memory, tools: List = None):
        self.router = router
        self.memory = memory
        self.tools = tools or []
        self._smolagent = None
        self._initialized = False

    async def initialize(self):
        """Try to load smolagents computer-use agent."""
        try:
            from smolagents import CodeAgent, HfApiModel
            model = HfApiModel(
                model_id="Qwen/Qwen2-VL-7B-Instruct",
                token=os.getenv("HF_TOKEN", ""),
            )
            self._smolagent = CodeAgent(tools=[], model=model)
            logger.info("✅ smolagents computer-use agent initialized")
        except ImportError:
            logger.info("smolagents not installed — multimodal fallback mode")
        except Exception as e:
            logger.warning(f"smolagents init failed: {e} — fallback mode")
        self._initialized = True

    async def run(self, task: str, image_url: Optional[str] = None) -> str:
        """Run a multimodal task."""
        if not self._initialized:
            await self.initialize()

        if image_url and self._smolagent:
            try:
                result = self._smolagent.run(f"Analyze this image and {task}: {image_url}")
                return str(result)
            except Exception as e:
                logger.warning(f"smolagents error: {e}")

        messages = [{"role": "user", "content": task}]
        if image_url:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]

        try:
            result = await self.router.chat(messages, max_tokens=1024)
            return result.get("content", "No response from multimodal LLM")
        except Exception as e:
            logger.error(f"Multimodal LLM error: {e}")
            return f"Multimodal processing unavailable. Task: {task}"

    async def analyze_screenshot(self, screenshot_path: str, instruction: str) -> str:
        """Analyze a screenshot file."""
        import base64
        try:
            with open(screenshot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            image_url = f"data:image/png;base64,{img_b64}"
            return await self.run(instruction, image_url)
        except Exception as e:
            return f"Screenshot analysis error: {e}"
