"""
MavadoClaw Chairman Console — HuggingFace Space
Gradio UI: Chat · Approval Queue · OSINT · Agents · Memory
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


def chat(message, history):
    if not message.strip():
        return ""
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
        content = data.get("content", "No response")
        return f"{content}\n\n*[via {provider}]*"
    except Exception as e:
        return f"❌ Error: {e}"


def get_queue():
    try:
        r = requests.get(f"{API_URL}/api/queue", headers=_headers(), timeout=10)
        tasks = r.json().get("tasks", [])
        if not tasks:
            return "✅ No pending tasks — Chairman is free!"
        return json.dumps(tasks, indent=2)
    except Exception as e:
        return f"❌ Error: {e}"


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
        return f"❌ {e}"


def list_agents():
    try:
        r = requests.get(f"{API_URL}/api/agents", timeout=10)
        agents = r.json().get("agents", [])
        return "\n".join([f"**{a['name']}** ({a['department']}) — {a['calls']} calls" for a in agents])
    except Exception as e:
        return f"❌ {e}"


with gr.Blocks(
    title="🐄 MavadoClaw — Chairman Console",
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="green"),
) as demo:
    gr.Markdown("""
    # 🐄 MavadoClaw Worker001 — Chairman Console
    *Autonomous AI Virtual Company · 33 Agents · Free-Forever LLM Cascade*
    """)

    with gr.Tab("💬 Chat"):
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

    with gr.Tab("✅ Approval Queue"):
        gr.Markdown("Review and approve/reject pending agent tasks.")
        queue_display = gr.Textbox(label="Pending Tasks", lines=20, interactive=False)
        gr.Button("🔄 Refresh Queue", variant="secondary").click(get_queue, outputs=queue_display)

        with gr.Row():
            task_id_input = gr.Textbox(label="Task ID", placeholder="abc12345")
            decision_radio = gr.Radio(["approved", "rejected"], label="Decision", value="approved")
            note_input = gr.Textbox(label="Note (optional)", placeholder="Approved — looks good")
        decision_result = gr.JSON(label="Result")
        gr.Button("Submit Decision", variant="primary").click(
            approve_task, inputs=[task_id_input, decision_radio, note_input], outputs=decision_result
        )

    with gr.Tab("🔍 OSINT Treasure Hunt"):
        gr.Markdown("Launch OSINT scan on any public target.")
        osint_target = gr.Textbox(label="Target (domain, company, username)", placeholder="tesla.com")
        osint_result = gr.JSON(label="Scan Result (task queued)")
        gr.Button("🏴‍☠️ Start Treasure Hunt", variant="primary").click(
            run_osint, inputs=[osint_target], outputs=osint_result
        )

    with gr.Tab("🤖 Agents"):
        gr.Markdown("View all 33 agents in the roster.")
        agents_display = gr.Markdown()
        gr.Button("🔄 Refresh", variant="secondary").click(list_agents, outputs=agents_display)

    with gr.Tab("📊 System Status"):
        status_display = gr.Textbox(label="Full System Status", lines=30, interactive=False)
        gr.Button("🔄 Refresh Status", variant="secondary").click(get_status, outputs=status_display)

    gr.Markdown("---\n*MavadoClaw Worker001 · Free Forever · Lagos 2026*")

demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
