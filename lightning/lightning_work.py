"""
MavadoClaw — Lightning.ai Burst Worker
GPU-accelerated tasks: heavy OSINT scans, LLM inference, model fine-tuning
Run: lightning run app lightning/lightning_work.py --cloud
"""
import lightning as L
import subprocess
import os
import json
import requests

class MavadoClawWork(L.LightningWork):
    def __init__(self):
        super().__init__(cloud_compute=L.CloudCompute("cpu-medium"), parallel=True)
        self.result = None

    def run(self, task: str, target: str = ""):
        print(f"[Lightning] Running task: {task} | target: {target}")
        if task == "osint_sweep":
            result = self._run_osint(target)
        elif task == "llm_batch":
            result = self._run_llm_batch(target)
        else:
            result = f"Unknown task: {task}"
        self.result = result

    def _run_osint(self, target):
        tools_output = {}
        for tool, cmd in [
            ("theharvester", f"theHarvester -d {target} -b all 2>&1 || echo not_installed"),
            ("maigret", f"maigret {target} --timeout 30 2>&1 || echo not_installed"),
        ]:
            try:
                out = subprocess.check_output(cmd, shell=True, timeout=120).decode()[:5000]
                tools_output[tool] = out
            except Exception as e:
                tools_output[tool] = str(e)
        return tools_output

    def _run_llm_batch(self, prompts_json):
        try:
            prompts = json.loads(prompts_json)
        except Exception:
            prompts = [prompts_json]
        results = []
        api_url = os.getenv("MAVADOCLAW_API_URL", "http://localhost:8080")
        for prompt in prompts[:10]:
            try:
                r = requests.post(f"{api_url}/api/chat",
                    json={"messages": [{"role": "user", "content": prompt}]}, timeout=30)
                results.append(r.json().get("content", ""))
            except Exception as e:
                results.append(str(e))
        return results


class MavadoClawApp(L.LightningApp):
    def __init__(self):
        super().__init__()
        self.work = MavadoClawWork()

    def run(self):
        task = os.getenv("LIGHTNING_TASK", "osint_sweep")
        target = os.getenv("LIGHTNING_TARGET", "example.com")
        self.work.run(task=task, target=target)
        print(f"[Lightning App] Result: {self.work.result}")


app = MavadoClawApp()
