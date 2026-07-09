"""
MavadoClaw API Server — FastAPI application
Exposes: /health, /api/chat, /api/agents, /api/osint, approval routes
"""
import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("api_server")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mavadoclaw-dev-token")


def _check_admin(token: Optional[str]):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    agent: Optional[str] = "ceo"
    stream: Optional[bool] = False


class OSINTRequest(BaseModel):
    target: str
    tools: Optional[List[str]] = None


async def run_api_server(roster, multimodal, osint=None):
    import uvicorn

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

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "MavadoClaw Worker001",
            "version": "2.0.0",
            "timestamp": time.time(),
            "agents": roster.active_count() if roster else 0,
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
    async def chat(req: ChatRequest, x_admin_token: Optional[str] = Header(None)):
        if not roster:
            raise HTTPException(status_code=503, detail="Agent roster not initialized")
        try:
            last_msg = req.messages[-1]["content"] if req.messages else ""
            result = await roster.run_task(last_msg, agent_id=req.agent)
            return {"status": "ok", "content": result, "agent": req.agent, "timestamp": time.time()}
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/agents")
    async def agents(x_admin_token: Optional[str] = Header(None)):
        _check_admin(x_admin_token)
        if not roster:
            return {"agents": [], "count": 0}
        agent_list = roster.list_agents() if hasattr(roster, "list_agents") else []
        return {"count": roster.active_count(), "agents": agent_list}

    @app.post("/api/osint")
    async def osint_scan(req: OSINTRequest, x_admin_token: Optional[str] = Header(None)):
        _check_admin(x_admin_token)
        if not osint and not roster:
            raise HTTPException(status_code=503, detail="OSINT swarm not available")
        if osint:
            results = await osint.treasure_hunt(req.target)
        else:
            results = await roster.run_task(
                f"Run OSINT scan on target: {req.target}",
                agent_id="osint_hunter",
            )
        return {"target": req.target, "results": results, "timestamp": time.time()}

    @app.post("/api/multimodal")
    async def multimodal_task(request: Request, x_admin_token: Optional[str] = Header(None)):
        _check_admin(x_admin_token)
        body = await request.json()
        if not multimodal:
            raise HTTPException(status_code=503, detail="Multimodal agent not available")
        result = await multimodal.run(body.get("task", ""), body.get("image_url"))
        return {"result": result, "timestamp": time.time()}

    try:
        from plugins.approval_loop import router as approval_router
        app.include_router(approval_router, prefix="/api")
        logger.info("Approval loop router mounted at /api")
    except Exception as e:
        logger.warning(f"Could not mount approval router: {e}")

    port = int(os.getenv("PORT", "8080"))
    logger.info(f"MavadoClaw API Server starting on port {port}")
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
