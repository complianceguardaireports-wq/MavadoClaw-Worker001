"""
MavadoClaw OSINT Swarm — Treasure Hunter
8 verified tools: BBot · SpiderFoot · theHarvester · Maigret · Uncover · Amass · Sherlock · GitGuardian
Safe, ethical: public data only. No auth bypass.
"""
import asyncio
import json
import logging
import os
import shutil
import time
from typing import Dict, List, Optional

logger = logging.getLogger("osint")

TOOL_TIMEOUT = int(os.getenv("OSINT_TIMEOUT", "120"))
RESULTS_DIR = os.getenv("OSINT_RESULTS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "osint"))


TOOL_COMMANDS = {
    "bbot": "bbot -t {target} -f subdomain-enum cloud-enum -o json --output-dir /tmp/bbot_{task_id} 2>&1 | tail -200",
    "spiderfoot": "spiderfoot -s {target} -m all -q -o json 2>&1 | tail -200",
    "theharvester": "theHarvester -d {target} -b anubis,baidu,bing,certspotter,crtsh,dnsdumpster,hackertarget,rapiddns,sublist3r,urlscan -f /tmp/harvest_{task_id} 2>&1",
    "maigret": "maigret {target} --json --timeout 15 --output /tmp/maigret_{task_id}.json 2>&1 | tail -50",
    "uncover": "uncover -q {target} -e shodan,censys,fofa -json 2>&1 | head -100",
    "amass": "amass enum -passive -d {target} -json /tmp/amass_{task_id}.json 2>&1 | tail -50",
    "sherlock": "sherlock {target} --json --output /tmp/sherlock_{task_id}.json 2>&1 | tail -50",
    "ggshield": "ggshield secret scan repo https://github.com/{target} 2>&1 | tail -50",
}

TOOL_DESCRIPTIONS = {
    "bbot": "Subdomain enumeration + cloud asset discovery",
    "spiderfoot": "200+ module OSINT automation",
    "theharvester": "Emails, subdomains, hosts, employee names",
    "maigret": "2000+ site username/profile check",
    "uncover": "Shodan/Censys/Fofa aggregator for exposed services",
    "amass": "DNS enumeration and network mapping",
    "sherlock": "Username across 400+ social networks",
    "ggshield": "Secrets/credential leak scanner",
}


class OSINTSwarm:
    def __init__(self, config=None, memory=None):
        self.config = config or {}
        self.memory = memory
        os.makedirs(RESULTS_DIR, exist_ok=True)
        self._scan_count = 0
        self._results_cache: Dict[str, dict] = {}

    def get_stats(self) -> dict:
        available = [t for t in TOOL_COMMANDS if shutil.which(t.replace("ggshield", "gg-shield").replace("theharvester", "theHarvester"))]
        return {
            "scans_run": self._scan_count,
            "tools_configured": len(TOOL_COMMANDS),
            "tools_available": available,
            "results_cached": len(self._results_cache),
        }

    async def _run_tool(self, tool: str, target: str, task_id: str) -> dict:
        if tool not in TOOL_COMMANDS:
            return {"tool": tool, "status": "unknown_tool", "output": ""}

        cmd = TOOL_COMMANDS[tool].format(target=target, task_id=task_id)
        start = time.time()

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=TOOL_TIMEOUT)
            output = stdout.decode("utf-8", errors="replace")[:20000]
            elapsed = round(time.time() - start, 1)

            if proc.returncode == 127:
                return {"tool": tool, "status": "not_installed", "output": f"{tool} not found — install it in Dockerfile", "elapsed": elapsed}

            return {"tool": tool, "status": "ok", "output": output, "elapsed": elapsed}

        except asyncio.TimeoutError:
            return {"tool": tool, "status": "timeout", "output": f"Timed out after {TOOL_TIMEOUT}s", "elapsed": TOOL_TIMEOUT}
        except Exception as e:
            return {"tool": tool, "status": "error", "output": str(e), "elapsed": round(time.time() - start, 1)}

    async def treasure_hunt(self, target: str, tools: Optional[List[str]] = None) -> dict:
        tools_to_run = tools or list(TOOL_COMMANDS.keys())
        task_id = str(int(time.time()))[-6:]

        logger.info(f"🔍 Starting treasure hunt: target={target}, tools={tools_to_run}")
        self._scan_count += 1

        tasks = [self._run_tool(tool, target, task_id) for tool in tools_to_run]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {
            "target": target,
            "task_id": task_id,
            "timestamp": time.time(),
            "tools_run": tools_to_run,
            "results": {},
            "summary": {},
        }

        for item in results_list:
            if isinstance(item, dict):
                tool = item.get("tool", "unknown")
                results["results"][tool] = item
                results["summary"][tool] = item.get("status", "error")

        results_path = os.path.join(RESULTS_DIR, f"{task_id}_{target.replace('.', '_')}.json")
        try:
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
        except Exception:
            pass

        self._results_cache[task_id] = results
        logger.info(f"🏴‍☠️ Treasure hunt complete: {target} — {len(results_list)} tools run")
        return results

    async def treasure_hunt_background(self, target: str, task_id: str, tools: Optional[List[str]] = None):
        try:
            results = await self.treasure_hunt(target, tools)
            from plugins.approval_loop import _decide
            _decide(task_id, "completed", f"osint-swarm:{json.dumps(results.get('summary', {}))[:200]}")
        except Exception as e:
            logger.error(f"Background OSINT scan failed: {e}")
