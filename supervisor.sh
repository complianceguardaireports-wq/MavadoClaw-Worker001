#!/bin/bash
# MavadoClaw Worker001 — 24/7 Supervisor
# Auto-restart, health checks, exponential backoff

set -e

LOG_DIR="/app/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUPERVISOR] $*" | tee -a "$LOG_DIR/supervisor.log"; }

log "🐄 MavadoClaw Worker001 starting..."

start_service() {
    local name="$1"; local cmd="$2"; local log_file="$LOG_DIR/${name}.log"
    log "Starting $name..."
    eval "$cmd >> $log_file 2>&1 &"
    echo $! > "/tmp/${name}.pid"
    log "$name PID: $(cat /tmp/${name}.pid)"
}

check_service() {
    local name="$1"; local pid_file="/tmp/${name}.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Start OmniRoute if available
if [ -d "/app/omniroute" ] && [ -f "/app/omniroute/server.js" ]; then
    start_service "omniroute" "node /app/omniroute/server.js --port 3000"
    sleep 2
fi

# Start 9Router if available
if [ -d "/app/ninerouter" ] && [ -f "/app/ninerouter/server.js" ]; then
    start_service "ninerouter" "node /app/ninerouter/server.js --port 8081"
    sleep 2
fi

# Start MavadoClaw CEO — main service
start_service "mavadoclaw" "python -m uvicorn main:app --host 0.0.0.0 --port 8080 --workers 1"
sleep 3

log "✅ All services started. Health monitor active."

BACKOFF=5
while true; do
    sleep 30
    if ! check_service "mavadoclaw"; then
        log "⚠️  MavadoClaw CEO crashed — restarting in ${BACKOFF}s..."
        sleep $BACKOFF
        start_service "mavadoclaw" "python -m uvicorn main:app --host 0.0.0.0 --port 8080 --workers 1"
        BACKOFF=$((BACKOFF * 2))
        if [ "$BACKOFF" -gt 300 ]; then BACKOFF=300; fi
    else
        BACKOFF=5
    fi

    if ! check_service "omniroute" && [ -f "/app/omniroute/server.js" ]; then
        log "Restarting omniroute..."
        start_service "omniroute" "node /app/omniroute/server.js --port 3000"
    fi
done
