"""
MavadoClaw Free Cascade Router
19-provider LLM cascade — auto-failover — RPM/RPD tracking
Priority order: keyless first → free-key → local fallbacks
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import aiohttp

logger = logging.getLogger("cascade")


@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    env_key: Optional[str]
    rpm_limit: int
    rpd_limit: int
    priority: int
    no_key: bool = False
    notes: str = ""


PROVIDERS: List[Provider] = [
    Provider("llm7",        "https://api.llm7.io/v1",                                   "qwen2.5-coder-32b",                None,               60,   5000, 1,  True,  "Free forever, OpenAI-compat"),
    Provider("ovh_anon",    "https://qwen-3-coder-30b.endpoints.kepler.ai.cloud.ovh.net","Qwen3-Coder-30B-A3B-Instruct",     None,                2,    500, 2,  True,  "Anonymous 2RPM/IP"),
    Provider("groq",        "https://api.groq.com/openai/v1",                           "llama-3.3-70b-versatile",          "GROQ_API_KEY",     30,   1000, 10, False, "500-700 tok/s"),
    Provider("gemini",      "https://generativelanguage.googleapis.com/v1beta/openai",  "gemini-2.0-flash",                 "GEMINI_API_KEY",   15,   1500, 11, False, "1500 req/day free"),
    Provider("cerebras",    "https://api.cerebras.ai/v1",                               "llama-3.3-70b",                    "CEREBRAS_API_KEY",  5,  14400, 12, False, "2100 tok/s"),
    Provider("openrouter",  "https://openrouter.ai/api/v1",                             "qwen/qwen3-coder:free",            "OPENROUTER_API_KEY",20,   200, 13, False, "Free :free models"),
    Provider("github",      "https://models.inference.ai.azure.com",                    "gpt-4o-mini",                      "GITHUB_TOKEN",     10,    150, 14, False, "50-150 req/day"),
    Provider("mistral",     "https://api.mistral.ai/v1",                                "mistral-small-latest",             "MISTRAL_API_KEY",  60,  86400, 15, False, "~1B tokens/month"),
    Provider("nvidia_nim",  "https://integrate.api.nvidia.com/v1",                      "meta/llama-3.3-70b-instruct",      "NVAPI_KEY",        40,   9999, 16, False, "1K credits free"),
    Provider("cohere",      "https://api.cohere.ai/v1",                                 "command-r",                        "COHERE_API_KEY",   10,   1000, 17, False, "~1K calls/month"),
    Provider("sambanova",   "https://api.sambanova.ai/v1",                              "Meta-Llama-3.3-70B-Instruct",      "SAMBANOVA_API_KEY",30,   9999, 18, False, "10-30 RPM free"),
    Provider("huggingface", "https://api-inference.huggingface.co/v1",                  "meta-llama/Llama-3.1-8B-Instruct", "HF_TOKEN",         10,    500, 19, False, "Free credits"),
    Provider("together",    "https://api.together.xyz/v1",                              "meta-llama/Llama-3.3-70B-Instruct-Turbo", "TOGETHER_API_KEY", 10, 500, 20, False, "Signup credits"),
    Provider("deepinfra",   "https://api.deepinfra.com/v1/openai",                      "meta-llama/Llama-3.3-70B-Instruct", "DEEPINFRA_KEY",   10,    500, 21, False, "Free tier"),
    Provider("fireworks",   "https://api.fireworks.ai/inference/v1",                    "accounts/fireworks/models/llama-v3p3-70b-instruct", "FIREWORKS_KEY", 10, 500, 22, False, "Free tier"),
    Provider("glhf",        "https://glhf.chat/api/openai/v1",                          "hf:meta-llama/Llama-3.3-70B-Instruct", "GLHF_API_KEY", 10, 500, 23, False, "Free community"),
    Provider("ollama",      "http://localhost:11434/v1",                                 "llama3.2",                         None,              999,  99999, 90, True,  "Local inference"),
    Provider("omniroute",   "http://omniroute:3000/v1",                                  "auto",                             None,              999,  99999, 99, True,  "Internal gateway"),
    Provider("ninerouter",  "http://ninerouter:8081/v1",                                 "auto",                             None,              999,  99999,100, True,  "Internal backup"),
]


class FreeCascadeRouter:
    def __init__(self):
        self._daily_counts: Dict[str, int] = {}
        self._rpm_windows: Dict[str, List[float]] = {}
        self._stats: Dict[str, int] = {}

    def provider_count(self) -> int:
        return len(PROVIDERS)

    def get_stats(self) -> dict:
        return dict(self._stats)

    def _date_key(self, name: str) -> str:
        return f"{name}:{int(time.time() // 86400)}"

    def _rpm_ok(self, p: Provider) -> bool:
        now = time.time()
        window = [t for t in self._rpm_windows.get(p.name, []) if now - t < 60]
        self._rpm_windows[p.name] = window
        return len(window) < p.rpm_limit

    def _rpd_ok(self, p: Provider) -> bool:
        return self._daily_counts.get(self._date_key(p.name), 0) < p.rpd_limit

    def _record_use(self, p: Provider):
        dk = self._date_key(p.name)
        self._daily_counts[dk] = self._daily_counts.get(dk, 0) + 1
        self._rpm_windows.setdefault(p.name, []).append(time.time())
        self._stats[p.name] = self._stats.get(p.name, 0) + 1

    async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        sorted_providers = sorted(PROVIDERS, key=lambda x: x.priority)
        for p in sorted_providers:
            if not self._rpd_ok(p) or not self._rpm_ok(p):
                logger.debug(f"Skipping {p.name} — quota")
                continue

            api_key = None if p.env_key is None else os.getenv(p.env_key, "")
            if p.env_key and not api_key and p.priority < 90:
                logger.debug(f"Skipping {p.name} — no key in env")
                continue

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": p.model,
                "messages": messages,
                "stream": False,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            try:
                timeout = aiohttp.ClientTimeout(total=25)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{p.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    ) as resp:
                        if resp.status in (429, 503, 529, 402):
                            logger.warning(f"{p.name} rate-limited or quota hit ({resp.status})")
                            continue
                        if resp.status >= 400:
                            logger.debug(f"{p.name} HTTP {resp.status}")
                            continue
                        data = await resp.json()
                        content = (
                            data.get("choices", [{}])[0]
                                .get("message", {})
                                .get("content", "")
                            or data.get("response", "")
                        )
                        if not content:
                            continue
                        self._record_use(p)
                        logger.info(f"✅ Served by {p.name} ({p.model})")
                        return {
                            "provider": p.name,
                            "model": p.model,
                            "content": content,
                            "no_key": p.no_key,
                            "notes": p.notes,
                        }
            except asyncio.TimeoutError:
                logger.debug(f"{p.name} timed out")
            except aiohttp.ClientConnectorError:
                logger.debug(f"{p.name} connection refused (not running)")
            except Exception as exc:
                logger.debug(f"{p.name} error: {exc}")

        raise RuntimeError("All 19 LLM providers exhausted or rate-limited — add more API keys")

    async def complete(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return result["content"]
