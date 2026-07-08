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

async def boot_sequence():
    print(BANNER)
    log.info("🚀 Booting MavadoClaw Worker001...")

    from plugins.free_cascade_router import FreeCascadeRouter
    from plugins.memory_hnsw import HNSWMemory
    from plugins.agent_roster import AgentRoster
    from plugins.osint_swarm import OSINTSwarm
    from plugins.approval_loop import ApprovalLoop
    from plugins.ai_infrastructure import AIInfrastructure
    from plugins.reasoning_engine import ReasoningEngine
    from plugins.self_healing import SelfHealingOrchestrator
    from plugins.multimodal_agent import MultiModalAgent
    from plugins.tool_synthesizer import ToolSynthesizer

    infra = AIInfrastructure()
    await infra.initialize()

    memory = HNSWMemory(dim=1536, space="cosine", max_elements=1_000_000)
    await memory.initialize()

    router = FreeCascadeRouter(config=CONFIG.get("llm_cascade", {}))
    await router.initialize()

    reasoning = ReasoningEngine(router=router, memory=memory)
    self_healer = SelfHealingOrchestrator(router=router, memory=memory)
    
    tool_synth = ToolSynthesizer(router=router)
    tools = await tool_synth.synthesize_all_available_tools()
    log.info(f"🔧 Synthesized {len(tools)} tools from all available sources")

    osint = OSINTSwarm(config=CONFIG.get("osint", {}), memory=memory)
    approval = ApprovalLoop(config=CONFIG.get("approval", {}))

    roster = AgentRoster(
        router=router,
        memory=memory,
        tools=tools,
        reasoning=reasoning,
        self_healer=self_healer,
        osint=osint,
        approval=approval,
        config=CONFIG.get("agents", {})
    )
    await roster.spawn_all()

    multimodal = MultiModalAgent(router=router, memory=memory, tools=tools)

    log.info("✅ All systems online — MavadoClaw Worker001 is FULLY OPERATIONAL")
    log.info(f"   Active agents : {roster.count}")
    log.info(f"   Available LLMs: {router.provider_count}")
    log.info(f"   Tools loaded  : {len(tools)}")
    log.info(f"   Memory vectors: {memory.count}")

    return roster, multimodal, self_healer

async def main():
    roster, multimodal, self_healer = await boot_sequence()

    async def graceful_shutdown(sig):
        log.info(f"Received {sig.name}, shutting down gracefully...")
        await roster.shutdown()
        sys.exit(0)

    loop = asyncio.get_event_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(graceful_shutdown(s)))

    mode = os.environ.get("WORKER_MODE", "interactive")
    
    if mode == "daemon":
        log.info("Running in daemon mode — autonomous background operations")
        await self_healer.run_forever(roster)
    elif mode == "api":
        from plugins.api_server import run_api_server
        await run_api_server(roster, multimodal)
    else:
        log.info("Running in interactive mode — type your task:")
        while True:
            try:
                task = input("\nTask> ").strip()
                if task.lower() in ("exit", "quit", "q"):
                    break
                if not task:
                    continue
                result = await roster.run_task(task)
                print(f"\n{result}\n")
            except (EOFError, KeyboardInterrupt):
                break

if __name__ == "__main__":
    asyncio.run(main())
