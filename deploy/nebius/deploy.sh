#!/usr/bin/env bash
# Sync Postulo to the Nebius VM and run docker compose.
# Prerequisites: create-vm.sh (or set POSTULO_SSH), repo-root .env with API keys.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"
[[ -f "$DIR/.state/ssh.env" ]] && source "$DIR/.state/ssh.env"

SSH_USER="${SSH_USER:-postulo}"
REMOTE="${POSTULO_SSH:-${SSH_USER}@${POSTULO_HOST:-}}"
[[ -n "$REMOTE" ]] || {
  echo "No VM target. Run create-vm.sh first, or export POSTULO_SSH=user@ip" >&2
  exit 1
}
HOST="${POSTULO_HOST:-${REMOTE##*@}}"

ENV_FILE="${ENV_FILE:-$ROOT/.env}"
[[ -f "$ENV_FILE" ]] || {
  echo "Missing $ENV_FILE — copy .env.example and fill NEBIUS_API_KEY + TAVILY_API_KEY." >&2
  exit 1
}

REMOTE_DIR=/opt/postulo
SSH=(ssh -o StrictHostKeyChecking=accept-new "$REMOTE")
RSYNC=(rsync -az --delete
  --exclude .git
  --exclude .venv
  --exclude node_modules
  --exclude frontend/node_modules
  --exclude frontend/.next
  --exclude backend/.venv
  --exclude backend/data
  --exclude output
  --exclude deploy/nebius/.state
  --exclude .env
)

echo "Target:  $REMOTE"
echo "Public:  http://${HOST}:3000  (API http://${HOST}:8000)"

echo "Syncing source → ${REMOTE}:${REMOTE_DIR}"
"${SSH[@]}" "mkdir -p $REMOTE_DIR"
"${RSYNC[@]}" "$ROOT/" "${REMOTE}:${REMOTE_DIR}/"

# Bake public URLs into the uploaded .env (do not mutate local .env).
TMP_ENV="$(mktemp)"
# shellcheck disable=SC2016
awk -v host="$HOST" '
  BEGIN { cors=0; api=0; mock=0 }
  /^CORS_ORIGINS=/ { print "CORS_ORIGINS=http://" host ":3000"; cors=1; next }
  /^NEXT_PUBLIC_API_URL=/ { print "NEXT_PUBLIC_API_URL=http://" host ":8000"; api=1; next }
  /^MOCK_MODE=/ { print "MOCK_MODE=false"; mock=1; next }
  { print }
  END {
    if (!cors) print "CORS_ORIGINS=http://" host ":3000"
    if (!api) print "NEXT_PUBLIC_API_URL=http://" host ":8000"
    if (!mock) print "MOCK_MODE=false"
  }
' "$ENV_FILE" >"$TMP_ENV"
scp -o StrictHostKeyChecking=accept-new "$TMP_ENV" "${REMOTE}:${REMOTE_DIR}/.env"
rm -f "$TMP_ENV"

echo "Building and starting containers (first build can take several minutes)…"
"${SSH[@]}" bash -s <<EOF
set -euo pipefail
cd $REMOTE_DIR
export NEXT_PUBLIC_API_URL=http://${HOST}:8000
docker compose build --build-arg NEXT_PUBLIC_API_URL=http://${HOST}:8000
docker compose up -d
docker compose ps
EOF

echo
echo "Deployed."
echo "  UI:   http://${HOST}:3000"
echo "  API:  http://${HOST}:8000/docs"
echo "  Logs: ssh $REMOTE 'cd $REMOTE_DIR && docker compose logs -f'"
