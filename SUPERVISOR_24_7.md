# MavadoClaw 24/7 Operations Manual

## Architecture Overview
```
Platform         | Role                    | Always-On | Free
-----------------|-------------------------|-----------|------
HF Spaces (CPU)  | Chairman Console UI     | ✅        | ✅
Cloudflare Worker| Edge API Gateway        | ✅        | ✅
GitHub Actions   | Cron (keep-alive, OSINT)| ✅ (cron) | ✅
Lightning.ai     | Burst GPU compute       | Scheduled | ✅
Kaggle           | Heavy ML notebooks      | Scheduled | ✅
```

## 24/7 Uptime Strategy
1. **supervisor.sh** — auto-restart all processes, exponential backoff
2. **GitHub Actions keep_alive.yml** — pings every 14 minutes
3. **Cloudflare Worker** — edge always-on, 100K req/day free
4. **HF Space** — CPU always-on, never sleeps with keep-alive pings

## Health Endpoints
- `GET /health` — main health check
- `GET /api/agents` — agent status (requires ADMIN_TOKEN)
- `GET /api/queue` — approval queue (requires ADMIN_TOKEN)

## Chairman Daily Workflow
- **08:00 UTC** — Daily briefing auto-generated, sent to approval queue
- **06:00 UTC** — OSINT sweep runs
- **Real-time** — Chat at `/api/chat` or HF Space UI

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| ADMIN_TOKEN | YES | Your secret admin token |
| GROQ_API_KEY | No | Groq free API key |
| GEMINI_API_KEY | No | Google AI Studio key |
| CEREBRAS_API_KEY | No | Cerebras free key |
| OPENROUTER_API_KEY | No | OpenRouter key |
| HF_TOKEN | No | HuggingFace token |
| MAVADOCLAW_API_URL | No | Backend URL for HF Space |

## Zero-Key Operation
System works with ZERO API keys via:
- LLM7.io (qwen2.5-coder-32b, no key)
- OVHcloud AI Endpoints (anonymous, 2 RPM/IP)
- Cloudflare Workers AI (10K neurons/day free)
- Local Ollama fallback
