#!/usr/bin/env python3
"""
MavadoClaw Worker001 — Autonomous AI Virtual Company
The most intelligent, self-reasoning, self-healing multi-agent system (2026).

Capabilities:
  - Free-tier cascade routing across 20+ LLM providers
  - OSINT swarm (BBot, SpiderFoot, Shodan, Censys, GreyNoise, FOFA, ZoomEye)
  - HNSW vector memory with semantic search
  - Multi-agent orchestration (smolagents, LangGraph, CrewAI, AutoGen)
  - Approval loop with human-in-the-loop escalation
  - Self-healing retries, circuit breakers, exponential backoff
  - Cloudflare Workers edge deployment
  - HuggingFace Spaces UI
  - Daily autonomous briefings & OSINT reports
  - Reasoning chains (CoT, ToT, ReAct, Reflection)
"""
import asyncio, json, os, logging, sys, signal
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("MavadoClaw")

CONFIG_PATH = Path("config.json")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║     MavadoClaw Worker001 — Autonomous AI Virtual Company     ║
║     Version: 2.0.0 | Built: 2026-07-08                      ║
║     Intelligence Level: MAXIMUM                              ║
║     Mode: FULLY AUTONOMOUS SELF-REASONING                    ║
╚══════════════════════════════════════════════════════════════╝
"""

app = FastAPI(
    title="MavadoClaw Worker001 API",
    description="Autonomous AI Virtual Company — Chairman Console API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_roster = None
_multimodal = None
_self_healer = None


@app.get("/health")
async def health():
    from time import time as _time
    return {
        "status": "ok",
        "service": "MavadoClaw Worker001",
        "version": "2.0.0",
        "timestamp": _time(),
        "agents": _roster.count if _roster else 0,
    }


@app.get("/")
async def root():
    return {
        "name": "MavadoClaw Worker001",
        "description": "Autonomous AI Virtual Company — 33 agents, 19 LLM providers, OSINT swarm",
        "endpoints": ["/health", "/api/chat", "/api/agents", "/api/osint", "/api/queue", "/api/approve"],
        "docs": "/docs",
    }


@app.post("/api/chat")
async def chat(request: dict):
    if not _roster:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Agent roster not initialized")
    messages = request.get("messages", [])
    agent = request.get("agent", "ceo")
    last_msg = messages[-1]["content"] if messages else ""
    result = await _roster.run_task(last_msg, agent_id=agent)
    return {"status": "ok", "content": result, "agent": agent}


@app.get("/api/agents")
async def agents():
    if not _roster:
        return {"agents": [], "count": 0}
    return {"count": _roster.count, "agents": _roster.list_agents()}


async def boot_sequence():
    print(BANNER)
    log.info("🚀 Booting MavadoClaw Worker001...")

    from plugins.free_cascade_router import FreeCascadeRouter
    from plugins.memory_hnsw import MemoryStore
    from plugins.agent_roster import AgentRoster
    from plugins.osint_swarm import OSINTSwarm
    from plugins.approval_loop import init_db as init_approval_db
    from plugins.ai_infrastructure import AIInfrastructure
    from plugins.reasoning_engine import ReasoningEngine
    from plugins.self_healing import SelfHealingOrchestrator
    from plugins.multimodal_agent import MultiModalAgent
    from plugins.tool_synthesizer import ToolSynthesizer

    infra = AIInfrastructure()
    init_approval_db()

    memory = MemoryStore()

    router = FreeCascadeRouter()

    reasoning = ReasoningEngine(router=router, memory=memory)
    self_healer = SelfHealingOrchestrator(router=router, memory=memory)

    tool_synth = ToolSynthesizer(router=router)
    tools = await tool_synth.synthesize_all_available_tools()
    log.info(f"🔧 Synthesized {len(tools)} tools from all available sources")

    osint = OSINTSwarm(config=CONFIG.get("osint", {}), memory=memory)

    roster = AgentRoster(
        cascade=router,
        memory=memory,
        tools=tools,
        reasoning=reasoning,
        self_healer=self_healer,
        osint=osint,
        config=CONFIG.get("agents", {}),
    )
    await roster.spawn_all()

    multimodal = MultiModalAgent(router=router, memory=memory, tools=tools)

    log.info("✅ All systems online — MavadoClaw Worker001 is FULLY OPERATIONAL")
    log.info(f"   Active agents : {roster.count}")
    log.info(f"   Available LLMs: {router.provider_count()}")
    log.info(f"   Tools loaded  : {len(tools)}")
    log.info(f"   Memory facts  : {memory.stats()['active_facts']}")

    return roster, multimodal, self_healer


async def main():
    global _roster, _multimodal, _self_healer
    _roster, _multimodal, _self_healer = await boot_sequence()

    async def graceful_shutdown(sig):
        log.info(f"Received {sig.name}, shutting down gracefully...")
        await _roster.shutdown()
        sys.exit(0)

    loop = asyncio.get_event_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(graceful_shutdown(s)))

    mode = os.environ.get("WORKER_MODE", "interactive")

    if mode == "daemon":
        log.info("Running in daemon mode — autonomous background operations")
        await _self_healer.run_forever(_roster)
    elif mode == "api":
        from plugins.api_server import run_api_server
        await run_api_server(_roster, _multimodal)
    else:
        log.info("Running in interactive mode — type your task:")
        while True:
            try:
                task = input("\nTask> ").strip()
                if task.lower() in ("exit", "quit", "q"):
                    break
                if not task:
                    continue
                result = await _roster.run_task(task)
                print(f"\n{result}\n")
            except (EOFError, KeyboardInterrupt):
                break


@app.on_event("startup")
async def startup_event():
    global _roster, _multimodal, _self_healer
    _roster, _multimodal, _self_healer = await boot_sequence()


if __name__ == "__main__":
    asyncio.run(main())
