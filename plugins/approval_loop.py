"""
MavadoClaw Approval Loop
Human-in-the-loop task queue: Chairman approves/rejects agent actions.
SQLite-backed, FastAPI router, auto-approve low-risk tasks.
"""
import json
import logging
import os
import sqlite3
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("approval")

DB_PATH = os.getenv("APPROVAL_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "approvals.db"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mavadoclaw-changeme")
AUTO_APPROVE_RISK = {"low", "info"}

router = APIRouter(prefix="/api", tags=["approval"])


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                created_at REAL,
                status TEXT DEFAULT 'pending',
                risk_level TEXT DEFAULT 'medium',
                task_type TEXT,
                payload TEXT,
                result TEXT,
                decided_at REAL,
                decision_by TEXT
            )
        """)
        conn.commit()
    logger.info(f"Approval DB initialized at {DB_PATH}")


def _require_admin(token: Optional[str]):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden — invalid admin token")


def submit_task(task_type: str, payload: dict, risk_level: str = "medium") -> str:
    task_id = str(uuid.uuid4())[:8]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO tasks (id, created_at, status, risk_level, task_type, payload) VALUES (?,?,?,?,?,?)",
            (task_id, time.time(), "pending", risk_level, task_type, json.dumps(payload)),
        )
        conn.commit()
    if risk_level in AUTO_APPROVE_RISK:
        _decide(task_id, "approved", "auto-system")
        logger.info(f"Task {task_id} ({task_type}) auto-approved — risk={risk_level}")
    else:
        logger.info(f"Task {task_id} ({task_type}) queued for Chairman approval — risk={risk_level}")
    return task_id


def _decide(task_id: str, decision: str, by: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE tasks SET status=?, decided_at=?, decision_by=? WHERE id=? AND status='pending'",
            (decision, time.time(), by, task_id),
        )
        conn.commit()


def get_pending() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, created_at, risk_level, task_type, payload FROM tasks WHERE status='pending' ORDER BY created_at"
        ).fetchall()
    return [
        {
            "id": r[0],
            "created_at": r[1],
            "age_seconds": round(time.time() - r[1]),
            "risk_level": r[2],
            "task_type": r[3],
            "payload": json.loads(r[4]),
        }
        for r in rows
    ]


def get_all_tasks(limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, created_at, status, risk_level, task_type, payload, result, decided_at, decision_by FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r[0], "created_at": r[1], "status": r[2], "risk_level": r[3],
            "task_type": r[4], "payload": json.loads(r[5] or "{}"),
            "result": r[6], "decided_at": r[7], "decision_by": r[8],
        }
        for r in rows
    ]


class DecisionRequest(BaseModel):
    task_id: str
    decision: str
    note: Optional[str] = None


@router.get("/queue")
async def queue_endpoint(x_admin_token: Optional[str] = Header(None)):
    _require_admin(x_admin_token)
    pending = get_pending()
    return {"count": len(pending), "tasks": pending}


@router.get("/tasks")
async def tasks_endpoint(limit: int = 50, x_admin_token: Optional[str] = Header(None)):
    _require_admin(x_admin_token)
    return {"tasks": get_all_tasks(limit)}


@router.post("/approve")
async def approve_endpoint(body: DecisionRequest, x_admin_token: Optional[str] = Header(None)):
    _require_admin(x_admin_token)
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")
    _decide(body.task_id, body.decision, f"chairman:{body.note or ''}")
    logger.info(f"Chairman {body.decision} task {body.task_id}")
    return {"status": "ok", "task_id": body.task_id, "decision": body.decision}
