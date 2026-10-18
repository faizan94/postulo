#!/bin/bash
# Start backend + frontend, then nginx on :8080 (Nebius Serverless AI HTTP port).
set -euo pipefail

mkdir -p /app/backend/data

echo "[postulo] starting backend on :8000"
cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "[postulo] starting frontend on :3000"
cd /app/frontend
PORT=3000 HOSTNAME=127.0.0.1 node server.js &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Wait until backend answers health (frontend can lag a bit).
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "[postulo] starting nginx on :8080"
exec nginx -g "daemon off;"
