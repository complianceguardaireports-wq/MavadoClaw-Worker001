# MavadoClaw Worker001 — Multi-stage Dockerfile
# Services: CowAgent CEO (8080) + OmniRoute (3000) + 9Router (8081) + OpenHands (3001)
# OSINT: BBot + SpiderFoot + theHarvester + Maigret + Amass + Sherlock + Uncover

FROM node:20-slim AS node-builder
WORKDIR /build
COPY omniroute/package*.json ./omniroute/
RUN cd omniroute && npm install --production 2>/dev/null || echo "omniroute deps skipped"
COPY ninerouter/package*.json ./ninerouter/ 2>/dev/null || mkdir -p ninerouter
RUN cd ninerouter && npm install --production 2>/dev/null || echo "ninerouter deps skipped"

FROM python:3.11-slim AS python-builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git supervisor nodejs npm \
    golang-go amass tor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /root/.local /root/.local
COPY --from=node-builder /build/omniroute /app/omniroute
COPY --from=node-builder /build/ninerouter /app/ninerouter 2>/dev/null || true

RUN pip install --no-cache-dir bbot spiderfoot theHarvester maigret-dap sherlock-project \
    2>/dev/null || echo "OSINT tools: partial install OK (some need Go/npm)"

RUN go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest 2>/dev/null || true

RUN pip install --no-cache-dir gitguardian-shield 2>/dev/null || true

ENV PATH="/root/.local/bin:/root/go/bin:$PATH"

COPY . .

RUN mkdir -p /app/data/approvals /app/data/osint /app/data/memory /app/logs

EXPOSE 8080 3000 8081 3001 9090 7070

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["bash", "supervisor.sh"]
