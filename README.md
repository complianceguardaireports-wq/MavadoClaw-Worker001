# MavadoClaw Worker001 🐄⚡
## Autonomous AI Virtual Company — Elite Edition

> **111-Agent Swarm · Free-Forever LLM Cascade · OSINT Treasure Hunter · 24/7 Self-Running**

[![GitHub Actions](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/workflows/Keep%20Alive/badge.svg)](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Architecture

```
CHAIRMAN (YOU) — Telegram / Slack / Web UI
       │  approve / reject / chat
       ▼
MavadoClaw CEO (port 8080) — FastAPI Orchestrator
  ├─ Free Cascade Router (19 LLM providers, auto-failover)
  ├─ OmniRoute Gateway (port 3000)
  ├─ 9Router Backup (port 8081)
  ├─ OpenHands Coding Agent (port 3001)
  ├─ OSINT Swarm Director (port 9090)
  │    ├─ BBot · SpiderFoot · theHarvester · Maigret
  │    ├─ Uncover · Deepkrak3n · Amass · Sherlock
  ├─ Ruflo Swarm Queen (port 7070) — 33 micro-agents
  └─ Approval Loop (SQLite + admin API)
```

## Free LLM Cascade (19 providers, ~8,400 calls/day FREE)

| Priority | Provider | Model | Key Required |
|---|---|---|---|
| 1 | LLM7.io | qwen2.5-coder-32b | ❌ None |
| 2 | OVHcloud Anon | Qwen3-Coder-30B | ❌ None |
| 3 | Groq | llama-3.3-70b-versatile | ✅ Free account |
| 4 | Gemini | gemini-2.5-flash | ✅ Free account |
| 5 | Cerebras | llama-3.3-70b | ✅ Free account |
| 6 | OpenRouter :free | qwen3-coder:free | ✅ Free account |
| 7 | GitHub Models | gpt-4o | ✅ Free GITHUB_TOKEN |
| 8 | Mistral | mistral-small-latest | ✅ Free account |
| 9 | NVIDIA NIM | llama-3.3-70b | ✅ Free account |
| 10 | HuggingFace | Llama-3.1-8B | ✅ Free account |
| 11 | Cloudflare Workers AI | llama-3.1-8b | ✅ Free account |
| ... | Ollama local | llama3.2 | ❌ None |
| ... | OmniRoute | auto | ❌ Local |
| ... | 9Router | auto | ❌ Local |

## Quick Start

```bash
git clone https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001
cd MavadoClaw-Worker001
cp config.json.template config.json
# Optionally add free API keys to config.json
docker compose up --build

# Test
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"@osint treasure hunt tesla.com"}]}'
```

## Services

| Service | Port | Role |
|---|---|---|
| MavadoClaw CEO | 8080 | FastAPI orchestrator, approval API |
| OmniRoute | 3000 | Primary AI gateway |
| 9Router | 8081 | Backup gateway + network intel |
| OpenHands | 3001 | AI coding agent |
| OSINT Director | 9090 | Treasure hunter swarm |
| Ruflo Queen | 7070 | 33 micro-agent coordinator |

## Human-in-the-Loop Approval

```bash
# View pending tasks
curl http://localhost:8080/api/queue -H "X-Admin-Token: your-token"

# Approve / reject
curl -X POST http://localhost:8080/api/approve \
  -H "X-Admin-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"abc12345","decision":"approved"}'
```

## Deploy Matrix (All Free)

| Platform | Role | Cost |
|---|---|---|
| PandaStack | Primary 24/7 | $0 |
| Hugging Face Spaces | Web UI + API mirror | $0 |
| Cloudflare Workers | Edge failover | $0 |
| GitHub Actions | CI/CD + keep-alive | $0 |
| Lightning.ai | GPU burst (22h/wk) | $0 |

## smolagents Computer-Use Integration

MavadoClaw integrates the [smolagents computer-use-agent](https://huggingface.co/spaces/smolagents/computer-use-agent) 
as a GUI automation sub-agent. It controls a full desktop via vision+mouse/keyboard — 
called whenever the CEO needs to interact with web UIs, GUIs, or browser automation.

---

*Built by MavadoClaw Council · Lagos 2026 · Free Forever*
