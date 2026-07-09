"""
MavadoClaw Chairman Console — HuggingFace Space
Gradio UI: Chat · Approval Queue · OSINT · Agents · Memory · Reasoning
Deploy: huggingface-cli upload YOUR_NAME/mavadoclaw-worker001 spaces/app.py
"""
import json
import os
import time

import gradio as gr
import requests

API_URL = os.getenv("MAVADOCLAW_API_URL", "http://localhost:8080")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _headers():
    return {"X-Admin-Token": ADMIN_TOKEN, "Content-Type": "application/json"}


def _backend_alive():
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def chat(message, history):
    if not message.strip():
        return ""
    if not _backend_alive():
        return "Backend unreachable. Start the API server or set MAVADOCLAW_API_URL."
    formatted = [
        {"role": "user" if item["role"] == "user" else "assistant", "content": item["content"]}
        for item in history
    ]
    formatted.append({"role": "user", "content": message})
    try:
        r = requests.post(
            f"{API_URL}/api/chat",
            json={"messages": formatted},
            headers=_headers(),
            timeout=35,
        )
        data = r.json()
        provider = data.get("provider", "unknown")
        model = data.get("model", "")
        content = data.get("content", "No response")
        agent = data.get("agent", "")
        no_key = data.get("no_key", False)
        notes = data.get("notes", "")
        line1 = content
        parts = []
        if provider:
            parts.append(f"provider: {provider}")
        if model:
            parts.append(f"model: {model}")
        if agent:
            parts.append(f"agent: {agent}")
        if no_key:
            parts.append("free-tier")
        if notes:
            parts.append(notes)
        meta = " · ".join(parts)
        return f"{line1}\n\n*[{meta}]*" if meta else line1
    except Exception as e:
        return f"Error: {e}"


def get_queue():
    try:
        r = requests.get(f"{API_URL}/api/queue", headers=_headers(), timeout=10)
        tasks = r.json().get("tasks", [])
        if not tasks:
            return "No pending tasks — Chairman is free!"
        return json.dumps(tasks, indent=2)
    except Exception as e:
        return f"Error: {e}"


def approve_task(task_id, decision, note):
    if not task_id.strip():
        return {"error": "task_id required"}
    try:
        r = requests.post(
            f"{API_URL}/api/approve",
            json={"task_id": task_id.strip(), "decision": decision, "note": note},
            headers=_headers(),
            timeout=10,
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def run_osint(target):
    if not target.strip():
        return {"error": "target required"}
    try:
        r = requests.post(
            f"{API_URL}/api/osint",
            json={"target": target.strip()},
            headers=_headers(),
            timeout=15,
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_status():
    try:
        r = requests.get(f"{API_URL}/api/status", headers=_headers(), timeout=10)
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return f"{e}"


def list_agents():
    try:
        r = requests.get(f"{API_URL}/api/agents", timeout=10)
        agents = r.json().get("agents", [])
        return "\n".join([
            f"**{a['name']}** ({a['department']}) — {a['calls']} calls"
            for a in agents
        ])
    except Exception as e:
        return f"{e}"


def search_memory(query):
    if not query.strip():
        return "Enter a search query."
    try:
        r = requests.post(
            f"{API_URL}/api/memory/search",
            json={"query": query.strip()},
            headers=_headers(),
            timeout=10,
        )
        data = r.json()
        facts = data.get("results", [])
        if not facts:
            return "No matching facts found."
        lines = []
        for i, f in enumerate(facts, 1):
            content = f.get("content", "")
            agent = f.get("agent", "unknown")
            created = f.get("created_at", 0)
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(created)) if created else "unknown"
            lines.append(f"{i}. [{agent} @ {ts}] {content}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def store_memory(content, agent):
    if not content.strip():
        return "Enter content to store."
    try:
        r = requests.post(
            f"{API_URL}/api/memory/store",
            json={"content": content.strip(), "agent": agent.strip() or "chairman"},
            headers=_headers(),
            timeout=10,
        )
        data = r.json()
        fact_id = data.get("fact_id", "")
        return f"Stored fact: {fact_id}" if fact_id else f"Result: {json.dumps(data)}"
    except Exception as e:
        return f"Error: {e}"


def memory_stats():
    try:
        r = requests.get(f"{API_URL}/api/memory/stats", headers=_headers(), timeout=10)
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return f"Error: {e}"


def run_reasoning(problem, strategy):
    if not problem.strip():
        return "Enter a problem to reason about."
    try:
        s = strategy.strip().lower() if strategy else "auto"
        r = requests.post(
            f"{API_URL}/api/reasoning/think",
            json={"problem": problem.strip(), "strategy": s},
            headers=_headers(),
            timeout=60,
        )
        data = r.json()
        answer = data.get("answer", "")
        strat = data.get("strategy", s)
        trace_lines = [f"Strategy: {strat}", f"Answer: {answer}"]
        if "reasoning" in data:
            trace_lines.append(f"\nReasoning:\n{data['reasoning']}")
        if "branches" in data:
            for i, b in enumerate(data["branches"], 1):
                trace_lines.append(f"\nBranch {i}: {b[:200]}")
        if "trace" in data:
            trace_lines.append("\nReAct Trace:")
            for step in data["trace"]:
                trace_lines.append(f"  {step[:200]}")
        return "\n".join(trace_lines)
    except Exception as e:
        return f"Error: {e}"


def list_reasoning_strategies():
    return "\n".join([
        "cot — Chain of Thought (step-by-step, best for math/logic)",
        "tot — Tree of Thought (multiple paths, best for creative problems)",
        "react — Reason + Act (tool-use cycles, best for research)",
        "reflection — Iterate and improve answers",
        "self_critique — Generate then critique",
        "meta — Reason about reasoning recursively",
        "auto — Let the system choose the best strategy",
    ])


with gr.Blocks(
    title="MavadoClaw — Chairman Console",
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="green"),
) as demo:
    gr.Markdown("""
    # MavadoClaw Worker001 — Chairman Console
    *Autonomous AI Virtual Company · 33 Agents · Free-Forever LLM Cascade*
    """)

    with gr.Tab("Chat"):
        gr.Markdown("Talk to your AI company. Use `@agent cto ...` to route to specific agents. Use `@osint domain.com` to launch treasure hunt.")
        gr.ChatInterface(
            chat,
            title=None,
            examples=[
                "@agent ceo What are our top 3 priorities today?",
                "@osint tesla.com",
                "@agent cto Write a Python health check endpoint",
                "@agent osint_hunter Find all subdomains of example.com",
            ],
        )

    with gr.Tab("Approval Queue"):
        gr.Markdown("Review and approve/reject pending agent tasks.")
        queue_display = gr.Textbox(label="Pending Tasks", lines=20, interactive=False)
        gr.Button("Refresh Queue", variant="secondary").click(get_queue, outputs=queue_display)

        with gr.Row():
            task_id_input = gr.Textbox(label="Task ID", placeholder="abc12345")
            decision_radio = gr.Radio(["approved", "rejected"], label="Decision", value="approved")
            note_input = gr.Textbox(label="Note (optional)", placeholder="Approved — looks good")
        decision_result = gr.JSON(label="Result")
        gr.Button("Submit Decision", variant="primary").click(
            approve_task, inputs=[task_id_input, decision_radio, note_input], outputs=decision_result
        )

    with gr.Tab("OSINT Treasure Hunt"):
        gr.Markdown("Launch OSINT scan on any public target.")
        osint_target = gr.Textbox(label="Target (domain, company, username)", placeholder="tesla.com")
        osint_result = gr.JSON(label="Scan Result (task queued)")
        gr.Button("Start Treasure Hunt", variant="primary").click(
            run_osint, inputs=[osint_target], outputs=osint_result
        )

    with gr.Tab("Agents"):
        gr.Markdown("View all 33 agents in the roster.")
        agents_display = gr.Markdown()
        gr.Button("Refresh", variant="secondary").click(list_agents, outputs=agents_display)

    with gr.Tab("Memory"):
        gr.Markdown("View and search stored facts across all agents.")
        with gr.Row():
            mem_search_input = gr.Textbox(label="Search query", placeholder="search facts...")
            mem_search_btn = gr.Button("Search Memory", variant="primary")
        mem_search_output = gr.Textbox(label="Search Results", lines=15, interactive=False)
        mem_search_btn.click(search_memory, inputs=mem_search_input, outputs=mem_search_output)

        gr.Markdown("---")
        with gr.Row():
            mem_store_input = gr.Textbox(label="Store a new fact", placeholder="The API endpoint is /api/v2")
            mem_agent_input = gr.Textbox(label="Agent", placeholder="chairman", value="chairman")
        mem_store_output = gr.Textbox(label="Store Result", interactive=False)
        gr.Button("Store Fact", variant="primary").click(
            store_memory, inputs=[mem_store_input, mem_agent_input], outputs=mem_store_output
        )

        gr.Markdown("---")
        mem_stats_display = gr.Textbox(label="Memory Stats", lines=5, interactive=False)
        gr.Button("Refresh Stats", variant="secondary").click(memory_stats, outputs=mem_stats_display)

    with gr.Tab("Reasoning"):
        gr.Markdown("Test reasoning strategies on any problem.")
        gr.Markdown("**Available strategies:**\n" + list_reasoning_strategies())
        with gr.Row():
            reasoning_input = gr.Textbox(label="Problem", placeholder="What is the optimal strategy for launching a SaaS product?", lines=3)
            strategy_select = gr.Dropdown(
                choices=["auto", "cot", "tot", "react", "reflection", "self_critique", "meta"],
                value="auto",
                label="Strategy",
            )
        reasoning_output = gr.Textbox(label="Reasoning Result", lines=20, interactive=False)
        gr.Button("Think", variant="primary").click(
            run_reasoning, inputs=[reasoning_input, strategy_select], outputs=reasoning_output
        )

    with gr.Tab("System Status"):
        status_display = gr.Textbox(label="Full System Status", lines=30, interactive=False)
        gr.Button("Refresh Status", variant="secondary").click(get_status, outputs=status_display)

    gr.Markdown("---\n*MavadoClaw Worker001 · Free Forever · Lagos 2026*")

demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
