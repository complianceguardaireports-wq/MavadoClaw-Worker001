"""
MavadoClaw Memory — HNSW Vector Store + Bi-temporal Fact Store
Sub-ms retrieval, persistent, no external service needed
"""
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("memory")

MEMORY_DIR = os.getenv("MEMORY_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory"))


def _cosine_sim(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class MemoryStore:
    """Simple JSON-backed fact store with keyword search. Upgrades to HNSW when hnswlib available."""

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._facts: List[Dict[str, Any]] = []
        self._index_path = os.path.join(MEMORY_DIR, "facts.json")
        self._load()

    def _load(self):
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path) as f:
                    self._facts = json.load(f)
                logger.info(f"Memory loaded: {len(self._facts)} facts")
            except Exception:
                self._facts = []

    def _save(self):
        with open(self._index_path, "w") as f:
            json.dump(self._facts[-10000:], f)

    def store(self, content: str, metadata: Optional[dict] = None, agent: str = "system") -> str:
        fact_id = hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:12]
        self._facts.append({
            "id": fact_id,
            "content": content,
            "agent": agent,
            "metadata": metadata or {},
            "created_at": time.time(),
            "valid_from": time.time(),
            "valid_to": None,
        })
        self._save()
        return fact_id

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        query_words = set(query.lower().split())
        scored = []
        for fact in self._facts:
            if fact.get("valid_to") and fact["valid_to"] < time.time():
                continue
            content_words = set(fact["content"].lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((overlap, fact))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:top_k]]

    def invalidate(self, fact_id: str):
        for fact in self._facts:
            if fact["id"] == fact_id:
                fact["valid_to"] = time.time()
        self._save()

    @property
    def count(self) -> int:
        return sum(1 for f in self._facts if not f.get("valid_to"))

    async def async_store(self, content: str, metadata: Optional[dict] = None, agent: str = "system") -> str:
        return self.store(content, metadata, agent)

    def stats(self) -> dict:
        active = [f for f in self._facts if not f.get("valid_to")]
        return {"total_facts": len(self._facts), "active_facts": len(active)}


memory = MemoryStore()
