"""
MavadoClaw Worker001 — CEO Orchestrator
FastAPI app: /health, /api/chat, /api/queue, /api/approve, /api/osint, /api/status
"""
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from plugins.free_cascade_router import FreeCascadeRouter
from plugins.approval_loop import router as approval_router, init_db, submit_task
from plugins.osint_swarm import OSINTSwarm
from plugins.agent_roster import AgentRoster

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("mavadoclaw")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mavadoclaw-changeme")
START_TIME = time.time()

cascade = FreeCascadeRouter()
osint = OSINTSwarm()
roster = AgentRoster(cascade)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("🐄 MavadoClaw Worker001 — CEO Online — Port 8080")
    logger.info("Free LLM Cascade: 19 providers loaded")
    logger.info("OSINT Swarm: 8 tools ready")
    logger.info("Agent Roster: 33 micro-agents initialized")
    asyncio.create_task(roster.run_background_workers())
    yield
    logger.info("Shutting down gracefully...")


app = FastAPI(
    title="MavadoClaw Worker001",
    description="Autonomous AI Virtual Company — 111-Agent Swarm",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(approval_router)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 2048
    agent: Optional[str] = None


class OSINTRequest(BaseModel):
    target: str
    tools: Optional[List[str]] = None


def _check_admin(token: Optional[str]):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "MavadoClaw-Worker001",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - START_TIME),
        "agents_active": roster.active_count(),
        "cascade_providers": cascade.provider_count(),
    }


@app.get("/")
async def root():
    return {"service": "MavadoClaw Worker001", "status": "online", "health": "/health", "docs": "/docs"}


@app.post("/api/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks, x_admin_token: Optional[str] = Header(None)):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    if last_user_msg.startswith("@osint "):
        target = last_user_msg[7:].strip()
        task_id = submit_task("osint_scan", {"target": target}, risk_level="medium")
        background_tasks.add_task(osint.treasure_hunt_background, target, task_id)
        return {
            "provider": "mavadoclaw-router",
            "model": "osint-swarm",
            "content": f"🔍 OSINT treasure hunt queued for `{target}` (task_id: `{task_id}`). Results will be ready in ~2 minutes. Check `/api/queue` for status.",
            "task_id": task_id,
        }

    if last_user_msg.startswith("@agent "):
        parts = last_user_msg.split(" ", 2)
        agent_name = parts[1] if len(parts) > 1 else "ceo"
        agent_msg = parts[2] if len(parts) > 2 else last_user_msg
        messages[-1]["content"] = agent_msg
        return await roster.route_to_agent(agent_name, messages, req.temperature, req.max_tokens)

    result = await cascade.chat(messages, temperature=req.temperature, max_tokens=req.max_tokens)
    return result


@app.post("/api/osint")
async def osint_scan(req: OSINTRequest, background_tasks: BackgroundTasks, x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    task_id = submit_task("osint_scan", {"target": req.target, "tools": req.tools}, risk_level="medium")
    background_tasks.add_task(osint.treasure_hunt_background, req.target, task_id, req.tools)
    return {"task_id": task_id, "status": "queued", "target": req.target}


@app.get("/api/status")
async def status(x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    return {
        "uptime": round(time.time() - START_TIME),
        "agents": roster.get_status(),
        "cascade": cascade.get_stats(),
        "osint": osint.get_stats(),
    }


@app.get("/api/agents")
async def list_agents():
    return {"agents": roster.list_agents()}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False, workers=1)
