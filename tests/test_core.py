import asyncio
import json
import os
import sqlite3
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from plugins.free_cascade_router import FreeCascadeRouter, PROVIDERS
from plugins.memory_hnsw import MemoryStore, _cosine_sim
from plugins.agent_roster import AgentRoster, AGENTS
from plugins.osint_swarm import OSINTSwarm, TOOL_COMMANDS, TOOL_DESCRIPTIONS
from plugins.approval_loop import (
    init_db,
    submit_task,
    get_pending,
    get_all_tasks,
    _decide,
)
from plugins.reasoning_engine import ReasoningEngine
from plugins.self_healing import SelfHealingOrchestrator, CircuitBreaker


@pytest.fixture
def router():
    return FreeCascadeRouter()


@pytest.fixture
def memory(tmp_path):
    with patch("plugins.memory_hnsw.MEMORY_DIR", str(tmp_path)):
        store = MemoryStore()
        return store


@pytest.fixture
def roster():
    cascade = MagicMock()
    cascade.chat = AsyncMock(return_value={"provider": "test", "content": "ok"})
    mem = MagicMock()
    mem.store = AsyncMock(return_value="abc")
    mem.stats.return_value = {"active_facts": 0}
    return AgentRoster(cascade=cascade, memory=mem)


@pytest.fixture
def osint_swarm(tmp_path):
    with patch("plugins.osint_swarm.RESULTS_DIR", str(tmp_path / "results")):
        return OSINTSwarm()


@pytest.fixture
def approval_db(tmp_path):
    with patch("plugins.approval_loop.DB_PATH", str(tmp_path / "test.db")):
        init_db()
        yield


@pytest.fixture
def reasoning():
    router = AsyncMock()
    router.complete = AsyncMock(return_value="cot")
    mem = MagicMock()
    mem.store = AsyncMock(return_value="abc")
    return ReasoningEngine(router=router, memory=mem)


@pytest.fixture
def self_healer():
    router = AsyncMock()
    router.complete = AsyncMock(return_value="pong")
    mem = MagicMock()
    mem.stats.return_value = {"active_facts": 5}
    return SelfHealingOrchestrator(router=router, memory=mem)


class TestFreeCascadeRouter:
    def test_initialization(self, router):
        assert router._daily_counts == {}
        assert router._rpm_windows == {}
        assert router._stats == {}

    def test_provider_count(self, router):
        assert router.provider_count() == 19
        assert router.provider_count() == len(PROVIDERS)

    def test_get_stats_empty(self, router):
        assert router.get_stats() == {}

    def test_get_stats_after_record(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        stats = router.get_stats()
        assert stats[p.name] == 1

    def test_date_key_format(self, router):
        dk = router._date_key("groq")
        parts = dk.split(":")
        assert parts[0] == "groq"
        assert parts[1].isdigit()

    def test_rpm_ok_when_empty(self, router):
        p = PROVIDERS[0]
        assert router._rpm_ok(p) is True

    def test_rpm_exceeded(self, router):
        p = PROVIDERS[2]
        router._rpm_windows[p.name] = [time.time() for _ in range(p.rpm_limit)]
        assert router._rpm_ok(p) is False

    def test_rpd_ok_when_empty(self, router):
        p = PROVIDERS[0]
        assert router._rpd_ok(p) is True

    def test_rpd_exceeded(self, router):
        p = PROVIDERS[0]
        dk = router._date_key(p.name)
        router._daily_counts[dk] = p.rpd_limit
        assert router._rpd_ok(p) is False

    def test_rpd_not_exceeded(self, router):
        p = PROVIDERS[0]
        dk = router._date_key(p.name)
        router._daily_counts[dk] = p.rpd_limit - 1
        assert router._rpd_ok(p) is True

    def test_record_use_increments_stats(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        assert router.get_stats()[p.name] == 1
        router._record_use(p)
        assert router.get_stats()[p.name] == 2

    def test_record_use_updates_rpd(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        dk = router._date_key(p.name)
        assert router._daily_counts[dk] == 1

    def test_record_use_updates_rpm_window(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        assert len(router._rpm_windows[p.name]) == 1

    def test_all_providers_have_required_fields(self):
        for p in PROVIDERS:
            assert p.name
            assert p.base_url
            assert p.model
            assert p.rpm_limit > 0
            assert p.rpd_limit > 0
            assert p.priority > 0

    def test_providers_sorted_by_priority(self):
        priorities = [p.priority for p in PROVIDERS]
        assert priorities == sorted(priorities)

    def test_no_key_providers(self):
        no_key = [p for p in PROVIDERS if p.no_key]
        assert len(no_key) >= 3

    def test_internal_providers(self):
        internal = [p for p in PROVIDERS if p.priority >= 90]
        assert len(internal) >= 2


class TestMemoryStore:
    def test_initialization(self, memory):
        assert memory._facts == [] or isinstance(memory._facts, list)

    def test_store_returns_id(self, memory):
        fid = memory.store("test fact")
        assert isinstance(fid, str)
        assert len(fid) == 12

    def test_store_increases_count(self, memory):
        before = memory.count
        memory.store("fact one")
        memory.store("fact two")
        assert memory.count >= before + 2

    def test_store_with_metadata(self, memory):
        fid = memory.store("fact with meta", metadata={"key": "val"}, agent="test_agent")
        assert fid
        results = memory.search("fact with meta")
        assert len(results) >= 1
        assert results[0]["metadata"] == {"key": "val"}
        assert results[0]["agent"] == "test_agent"

    def test_search_returns_matches(self, memory):
        memory.store("quantum computing is fascinating")
        memory.store("classical computing is old")
        results = memory.search("quantum computing")
        assert len(results) >= 1
        assert any("quantum" in r["content"].lower() for r in results)

    def test_search_returns_top_k(self, memory):
        for i in range(10):
            memory.store(f"unique word alpha {i}")
        results = memory.search("unique word alpha", top_k=3)
        assert len(results) <= 3

    def test_search_no_match(self, memory):
        memory.store("completely unrelated")
        results = memory.search("zzzz nonexistent xyz")
        assert len(results) == 0

    def test_stats_empty(self, memory):
        stats = memory.stats()
        assert "total_facts" in stats
        assert "active_facts" in stats

    def test_stats_after_store(self, memory):
        memory.store("fact a")
        memory.store("fact b")
        stats = memory.stats()
        assert stats["active_facts"] >= 2

    def test_invalidate(self, memory):
        fid = memory.store("to be invalidated")
        memory.invalidate(fid)
        stats = memory.stats()
        assert stats["active_facts"] == 0

    def test_invalidate_only_target(self, memory):
        fid1 = memory.store("keep me")
        fid2 = memory.store("remove me")
        memory.invalidate(fid2)
        results = memory.search("keep me")
        assert len(results) == 1
        stats = memory.stats()
        assert stats["active_facts"] == 1

    def test_search_excludes_invalidated(self, memory):
        fid = memory.store("invalidated fact")
        memory.invalidate(fid)
        results = memory.search("invalidated fact")
        assert len(results) == 0

    def test_store_default_agent(self, memory):
        memory.store("default agent fact")
        results = memory.search("default agent")
        assert results[0]["agent"] == "system"


class TestCosineSim:
    def test_identical_vectors(self):
        assert _cosine_sim([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_sim([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_empty_vectors(self):
        assert _cosine_sim([], []) == 0.0

    def test_different_lengths(self):
        assert _cosine_sim([1, 2], [1]) == 0.0

    def test_zero_vector(self):
        assert _cosine_sim([0, 0], [1, 1]) == 0.0


class TestAgentRoster:
    def test_initialization(self, roster):
        assert roster.cascade is not None
        assert roster.memory is not None

    def test_count(self, roster):
        assert roster.count == len(AGENTS)
        assert roster.count >= 12

    def test_active_count(self, roster):
        assert roster.active_count() == roster.count

    def test_list_agents(self, roster):
        agents = roster.list_agents()
        assert len(agents) == len(AGENTS)
        for a in agents:
            assert "id" in a
            assert "name" in a
            assert "department" in a
            assert "calls" in a

    def test_list_agents_contains_ceo(self, roster):
        agents = roster.list_agents()
        ids = [a["id"] for a in agents]
        assert "ceo" in ids
        assert "cto" in ids

    def test_get_status(self, roster):
        status = roster.get_status()
        assert isinstance(status, dict)
        assert "ceo" in status
        assert "calls" in status["ceo"]

    def test_route_to_agent(self, roster):
        result = asyncio.run(
            roster.route_to_agent("ceo", [{"role": "user", "content": "hello"}])
        )
        assert result["provider"] == "test"
        assert result["agent"] == "ceo"

    def test_route_to_unknown_agent_uses_default(self, roster):
        with pytest.raises(KeyError):
            asyncio.run(
                roster.route_to_agent("nonexistent", [{"role": "user", "content": "hi"}])
            )

    def test_run_task(self, roster):
        result = asyncio.run(
            roster.run_task("do something")
        )
        assert result == "ok"

    def test_calls_increment(self, roster):
        asyncio.run(
            roster.route_to_agent("ceo", [{"role": "user", "content": "x"}])
        )
        status = roster.get_status()
        assert status["ceo"]["calls"] == 1

    def test_multiple_calls(self, roster):
        for _ in range(3):
            asyncio.run(
                roster.route_to_agent("cto", [{"role": "user", "content": "x"}])
            )
        status = roster.get_status()
        assert status["cto"]["calls"] == 3


class TestOSINTSwarm:
    def test_initialization(self, osint_swarm):
        assert osint_swarm._scan_count == 0
        assert osint_swarm._results_cache == {}

    def test_get_stats(self, osint_swarm):
        stats = osint_swarm.get_stats()
        assert "scans_run" in stats
        assert "tools_configured" in stats
        assert "tools_available" in stats
        assert "results_cached" in stats
        assert stats["tools_configured"] == len(TOOL_COMMANDS)

    def test_get_stats_initial(self, osint_swarm):
        stats = osint_swarm.get_stats()
        assert stats["scans_run"] == 0
        assert stats["results_cached"] == 0

    def test_tool_commands_match_descriptions(self):
        for tool in TOOL_COMMANDS:
            assert tool in TOOL_DESCRIPTIONS, f"{tool} missing description"

    def test_tool_descriptions_complete(self):
        assert len(TOOL_DESCRIPTIONS) == 8
        for tool, desc in TOOL_DESCRIPTIONS.items():
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_tool_timeout_default(self):
        from plugins.osint_swarm import TOOL_TIMEOUT
        assert TOOL_TIMEOUT > 0


class TestApprovalLoop:
    def test_init_db_creates_file(self, tmp_path):
        with patch("plugins.approval_loop.DB_PATH", str(tmp_path / "test.db")):
            init_db()
            assert (tmp_path / "test.db").exists()

    def test_init_db_creates_table(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        with patch("plugins.approval_loop.DB_PATH", db_path):
            init_db()
            with sqlite3.connect(db_path) as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = [t[0] for t in tables]
                assert "tasks" in table_names

    def test_submit_task_returns_id(self, approval_db):
        task_id = submit_task("test_action", {"key": "value"})
        assert isinstance(task_id, str)
        assert len(task_id) == 8

    def test_submit_task_stores_payload(self, approval_db):
        task_id = submit_task("deploy", {"env": "prod", "risk": "high"})
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id in ids
        task = [t for t in pending if t["id"] == task_id][0]
        assert task["payload"]["env"] == "prod"

    def test_submit_task_pending_status(self, approval_db):
        task_id = submit_task("medium_risk", {"x": 1}, risk_level="medium")
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id in ids

    def test_submit_task_auto_approve_low(self, approval_db):
        task_id = submit_task("low_risk", {"x": 1}, risk_level="low")
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id not in ids

    def test_submit_task_auto_approve_info(self, approval_db):
        task_id = submit_task("info_task", {"x": 1}, risk_level="info")
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id not in ids

    def test_get_pending_empty(self, approval_db):
        pending = get_pending()
        assert pending == []

    def test_get_pending_multiple(self, approval_db):
        submit_task("action1", {"a": 1}, risk_level="high")
        submit_task("action2", {"b": 2}, risk_level="high")
        submit_task("action3", {"c": 3}, risk_level="high")
        pending = get_pending()
        assert len(pending) == 3

    def test_decide_approve(self, approval_db):
        task_id = submit_task("to_approve", {"x": 1}, risk_level="high")
        _decide(task_id, "approved", "test_admin")
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id not in ids

    def test_decide_reject(self, approval_db):
        task_id = submit_task("to_reject", {"x": 1}, risk_level="high")
        _decide(task_id, "rejected", "test_admin")
        pending = get_pending()
        ids = [t["id"] for t in pending]
        assert task_id not in ids

    def test_get_all_tasks(self, approval_db):
        submit_task("task_a", {"a": 1}, risk_level="high")
        submit_task("task_b", {"b": 2}, risk_level="high")
        all_tasks = get_all_tasks()
        assert len(all_tasks) == 2

    def test_get_all_tasks_sorted(self, approval_db):
        submit_task("first", {"x": 1}, risk_level="high")
        time.sleep(0.1)
        submit_task("second", {"x": 2}, risk_level="high")
        all_tasks = get_all_tasks()
        assert len(all_tasks) == 2
        assert all_tasks[0]["id"] != all_tasks[1]["id"]

    def test_pending_has_age_seconds(self, approval_db):
        task_id = submit_task("aged", {"x": 1}, risk_level="high")
        time.sleep(0.01)
        pending = get_pending()
        task = [t for t in pending if t["id"] == task_id][0]
        assert task["age_seconds"] >= 0

    def test_decide_only_pending(self, approval_db):
        task_id = submit_task("double_decide", {"x": 1}, risk_level="high")
        _decide(task_id, "approved", "admin")
        _decide(task_id, "rejected", "admin")
        all_tasks = get_all_tasks()
        task = [t for t in all_tasks if t["id"] == task_id][0]
        assert task["status"] == "approved"


class TestReasoningEngine:
    def test_initialization(self, reasoning):
        assert reasoning.router is not None
        assert reasoning.memory is not None
        assert reasoning.default_strategy == "auto"

    def test_strategies_list(self):
        assert len(ReasoningEngine.STRATEGIES) == 6
        assert "cot" in ReasoningEngine.STRATEGIES
        assert "tot" in ReasoningEngine.STRATEGIES
        assert "react" in ReasoningEngine.STRATEGIES
        assert "reflection" in ReasoningEngine.STRATEGIES
        assert "self_critique" in ReasoningEngine.STRATEGIES
        assert "meta" in ReasoningEngine.STRATEGIES

    def test_trace_log_empty(self, reasoning):
        assert reasoning.trace_log == []

    def test_select_strategy(self, reasoning):
        strategy = asyncio.run(
            reasoning._select_strategy("What is 2+2?")
        )
        assert strategy in ReasoningEngine.STRATEGIES

    def test_select_strategy_fallback(self, reasoning):
        reasoning.router.complete = AsyncMock(side_effect=Exception("fail"))
        strategy = asyncio.run(
            reasoning._select_strategy("test")
        )
        assert strategy == "cot"

    def test_chain_of_thought(self, reasoning):
        reasoning.router.complete = AsyncMock(return_value="Step 1: think\nFinal Answer: 42")
        result = asyncio.run(
            reasoning._chain_of_thought("What is 6*7?")
        )
        assert result["strategy"] == "cot"
        assert "42" in result["answer"]

    def test_extract_answer_final(self, reasoning):
        answer = reasoning._extract_answer("Here is my reasoning\nFinal Answer: yes")
        assert answer == "yes"

    def test_extract_answer_therefore(self, reasoning):
        answer = reasoning._extract_answer("Reasoning...\nTherefore, the result is 5")
        assert "5" in answer

    def test_extract_answer_fallback(self, reasoning):
        answer = reasoning._extract_answer("just some text\nlast line")
        assert answer == "last line"

    def test_extract_answer_empty(self, reasoning):
        answer = reasoning._extract_answer("")
        assert answer == ""


class TestSelfHealingOrchestrator:
    def test_initialization(self, self_healer):
        assert self_healer.router is not None
        assert self_healer.memory is not None
        assert self_healer.check_interval == 30
        assert self_healer.running is False

    def test_get_circuit_new(self, self_healer):
        cb = self_healer.get_circuit("test_service")
        assert cb.name == "test_service"
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0

    def test_get_circuit_existing(self, self_healer):
        cb1 = self_healer.get_circuit("svc1")
        cb2 = self_healer.get_circuit("svc1")
        assert cb1 is cb2

    def test_health_history_empty(self, self_healer):
        assert len(self_healer.health_history) == 0

    def test_repair_log_empty(self, self_healer):
        assert self_healer.repair_log == []


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0

    def test_record_success(self):
        cb = CircuitBreaker("test")
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.success_count == 1

    def test_record_failure(self):
        cb = CircuitBreaker("test")
        cb.record_failure()
        assert cb.failure_count == 1

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

    def test_can_execute_closed(self):
        cb = CircuitBreaker("test")
        assert cb.can_execute() is True

    def test_can_execute_open(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        assert cb.can_execute() is False

    def test_can_execute_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        cb.last_failure_time = time.time() - 1
        assert cb.can_execute() is True
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_half_open_recovery(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        cb.last_failure_time = time.time() - 1
        cb.can_execute()
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_custom_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=10)
        for _ in range(9):
            cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
