# 🤖 MavadoClaw Worker001
## Autonomous AI Virtual Company — Free-Forever | 24/7 | OSINT + Multi-Agent

> *Convened by: Five-Mind Elite Council + Council of 100 Eternal Architects*  
> *You = Chairman. You approve. Agents execute.*

[![CI](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/actions/workflows/ci.yml/badge.svg)](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/actions)
[![Keep Alive](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/actions/workflows/keep_alive.yml/badge.svg)](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001/actions)

---

## 🏢 What Is This?

**MavadoClaw Worker001** is a fully autonomous AI virtual company that runs 24/7 for **$0/month**. You are the Chairman. You communicate and approve daily. 33 AI agents handle everything else.

```
CHAIRMAN (YOU)
    │  Telegram / HF Space UI / API
    ▼
CEO Agent (FastAPI :8080)
    ├── CTO → Engineering (8 OpenHands workers)
    ├── CISO → Security (BBot + GitGuardian)
    ├── CIO/OSINT → Intelligence (7 OSINT tools)
    ├── COO → Operations (Ruflo swarm)
    └── CFO → Cost optimization

FREE LLM ROUTER (19 providers, auto-failover)
    1. LLM7.io (no key) → 2. OVHcloud anon → 3. Groq → 4. Gemini → 5. Cerebras → ...

COMPUTE PLATFORMS
    HF Spaces (UI, always-on) | Cloudflare Workers (edge) | GitHub Actions (cron) | Lightning.ai (GPU burst)
```

---

## 🚀 Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001
cd MavadoClaw-Worker001
cp config.json.template config.json
# Edit config.json — all keys optional, system runs on zero keys
```

### 2. Run Locally (Docker)
```bash
docker compose up --build
# CEO: http://localhost:8080
# Docs: http://localhost:8080/docs
```

### 3. Test
```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"@ai status report"}]}'
```

### 4. Deploy HuggingFace Space (Chairman Console)
```bash
huggingface-cli upload YOUR_HF_USERNAME/mavadoclaw-worker001 spaces/app.py
# Set secret: MAVADOCLAW_API_URL = your backend URL
# Set secret: ADMIN_TOKEN = your token
```

### 5. Deploy Cloudflare Edge Worker
```bash
wrangler secret put PANDASTACK_URL
wrangler secret put ADMIN_TOKEN
wrangler deploy workers/chat.js
```

### 6. GitHub Actions Secrets
Set these in repo Settings → Secrets:
| Secret | Value |
|--------|-------|
| `ADMIN_TOKEN` | Your 32-char random token |
| `PANDASTACK_URL` | Your backend URL |
| `HF_SPACE_URL` | Your HF Space URL |

---

## 📁 Repository Structure

```
MavadoClaw-Worker001/
├── main.py                          # Boot entry point
├── Dockerfile                       # Multi-service container
├── docker-compose.yml               # Local orchestration
├── supervisor.sh                    # 24/7 process manager
├── wrangler.toml                    # Cloudflare Workers config
├── config.json.template             # Config template (zero keys needed)
├── TREASURE_API_REGISTRY.json       # All free LLM providers
├── SUPERVISOR_24_7.md               # Operations manual
│
├── plugins/                         # All AI agents & systems
│   ├── api_server.py                # FastAPI application
│   ├── free_cascade_router.py       # 19-provider LLM router
│   ├── agent_roster.py              # 33 micro-agents
│   ├── osint_swarm.py               # OSINT tools swarm
│   ├── approval_loop.py             # Human-in-the-loop (SQLite)
│   ├── memory_hnsw.py               # Vector memory store
│   ├── reasoning_engine.py          # CoT/ToT/ReAct reasoning
│   ├── self_healing.py              # Auto-restart & circuit breakers
│   ├── multimodal_agent.py          # Vision + smolagents
│   ├── ruflo_bridge.py              # Ruflo swarm connector
│   ├── smolagents_bridge.py         # HF smolagents integration
│   └── tool_synthesizer.py          # Auto-discover tools
│
├── workers/
│   └── chat.js                      # Cloudflare edge worker
│
├── spaces/
│   ├── app.py                       # HF Gradio Chairman Console
│   └── requirements.txt
│
├── lightning/
│   └── lightning_work.py            # Lightning.ai GPU burst jobs
│
├── orca/
│   └── orca.yaml                    # Orca ADE mobile control
│
└── .github/workflows/
    ├── ci.yml                       # Test + lint on push
    ├── keep_alive.yml               # Ping every 14 min
    ├── daily_briefing.yml           # 08:00 UTC briefing
    └── osint_cron.yml               # 06:00 UTC OSINT sweep
```

---

## 🔑 Free LLM Providers (Zero Cost Forever)

| Provider | Model | Daily Limit | Key Needed |
|----------|-------|-------------|------------|
| LLM7.io | qwen2.5-coder-32b | 5000 | ❌ No |
| OVHcloud AI | Qwen3-Coder-30B | 2 RPM/IP | ❌ No |
| Cloudflare Workers AI | llama-3.1-8b | 10K neurons/day | ❌ No |
| Groq | llama-3.3-70b | 1000 req/day | ✅ Free |
| Gemini AI Studio | gemini-2.5-flash | 1500 req/day | ✅ Free |
| Cerebras | llama-3.3-70b | 1M tokens/day | ✅ Free |
| OpenRouter :free | qwen3-coder | 50 req/day | ✅ Free |
| GitHub Models | gpt-4o | 150 req/day | ✅ Free |
| Mistral AI | mistral-small | ~1B tokens/mo | ✅ Free |
| NVIDIA NIM | llama-3.3-70b | 1000 credits | ✅ Free |

---

## 🔭 OSINT Swarm Tools

| Tool | Purpose | Free |
|------|---------|------|
| BBot | Full OSINT recon | ✅ |
| SpiderFoot | 200+ module automation | ✅ |
| theHarvester | Email/domain discovery | ✅ |
| Maigret | Username across 3000+ sites | ✅ |
| Uncover | Host discovery (Shodan/Censys) | ✅ |
| Sherlock | Username hunt | ✅ |
| GitGuardian ggshield | Secret scanning | ✅ |
| Amass | Subdomain enumeration | ✅ |

> **Ethics**: Public data only. No auth bypass. Human approval required for all OSINT targets.

---

## 👤 Daily Chairman Workflow

1. **08:00 UTC** — Receive daily briefing in approval queue
2. **Anytime** — Chat at `/api/chat` or HF Space UI  
3. **Approve/Reject** — POST `/api/approve` with your ADMIN_TOKEN
4. **Monitor** — GET `/api/queue` for pending tasks

---

## 📜 License

MIT — Free forever. Build the future.

---

*MavadoClaw Worker001 — Built on the shoulders of 111 Eternal Architects*
