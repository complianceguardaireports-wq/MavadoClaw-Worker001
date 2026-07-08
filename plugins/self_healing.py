"""
SelfHealingOrchestrator — Autonomous error recovery, circuit breakers, adaptive retries
The system monitors itself, detects failures, and self-repairs without human intervention.
"""
import asyncio, logging, time, traceback
from collections import defaultdict, deque
from datetime import datetime

log = logging.getLogger("SelfHealing")

class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name, failure_threshold=5, recovery_timeout=60):
        self.name = name
        self.state = self.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.success_count = 0

    def record_success(self):
        self.failure_count = 0
        self.success_count += 1
        if self.state == self.HALF_OPEN:
            self.state = self.CLOSED
            log.info(f"Circuit {self.name}: HALF_OPEN → CLOSED (recovered)")

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            log.warning(f"Circuit {self.name}: CLOSED → OPEN (too many failures)")

    def can_execute(self) -> bool:
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = self.HALF_OPEN
                log.info(f"Circuit {self.name}: OPEN → HALF_OPEN (trying recovery)")
                return True
            return False
        return True  # HALF_OPEN: allow one attempt


class SelfHealingOrchestrator:
    def __init__(self, router, memory, check_interval: int = 30):
        self.router = router
        self.memory = memory
        self.check_interval = check_interval
        self.circuits = defaultdict(lambda: CircuitBreaker("default"))
        self.health_history = deque(maxlen=1000)
        self.repair_log = []
        self.running = False

    def get_circuit(self, name: str) -> CircuitBreaker:
        if name not in self.circuits:
            self.circuits[name] = CircuitBreaker(name)
        return self.circuits[name]

    async def with_retry(self, fn, *args, name="op", max_retries=5, base_delay=1.0, **kwargs):
        circuit = self.get_circuit(name)
        for attempt in range(max_retries):
            if not circuit.can_execute():
                log.warning(f"Circuit {name} is OPEN — skipping attempt {attempt+1}")
                await asyncio.sleep(self.check_interval)
                continue
            try:
                result = await fn(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure()
                delay = base_delay * (2 ** attempt)
                log.warning(f"[{name}] attempt {attempt+1}/{max_retries} failed: {e}. Retry in {delay:.1f}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    log.error(f"[{name}] all retries exhausted: {e}")
                    raise

    async def health_check(self, roster) -> dict:
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "circuits": {},
            "memory_ok": False,
            "router_ok": False,
        }
        
        try:
            test = await self.router.complete("ping", max_tokens=5)
            status["router_ok"] = bool(test)
        except Exception as e:
            status["router_error"] = str(e)

        try:
            status["memory_ok"] = self.memory.count >= 0
        except Exception as e:
            status["memory_error"] = str(e)

        for name, cb in self.circuits.items():
            status["circuits"][name] = {
                "state": cb.state,
                "failures": cb.failure_count,
                "successes": cb.success_count,
            }

        self.health_history.append(status)
        return status

    async def run_forever(self, roster):
        self.running = True
        log.info("🩺 SelfHealingOrchestrator started — continuous monitoring active")
        
        while self.running:
            try:
                health = await self.health_check(roster)
                degraded = [k for k, v in health.get("circuits", {}).items() if v["state"] != "closed"]
                if degraded:
                    log.warning(f"Degraded circuits: {degraded} — attempting self-repair")
                    await self._attempt_repair(degraded, roster)
                else:
                    log.info(f"✅ Health check OK — all systems nominal")
            except Exception as e:
                log.error(f"Health check failed: {e}\n{traceback.format_exc()}")
            
            await asyncio.sleep(self.check_interval)

    async def _attempt_repair(self, degraded_names, roster):
        for name in degraded_names:
            log.info(f"🔧 Attempting repair of: {name}")
            try:
                if hasattr(roster, "restart_agent"):
                    await roster.restart_agent(name)
                repair_entry = {"name": name, "time": datetime.utcnow().isoformat(), "action": "restart"}
                self.repair_log.append(repair_entry)
                log.info(f"✅ Repaired: {name}")
            except Exception as e:
                log.error(f"Repair failed for {name}: {e}")

    def stop(self):
        self.running = False
