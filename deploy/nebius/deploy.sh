#!/usr/bin/env bash
# Deploy or update Postulo (backend + frontend + Caddy) on the Nebius VM.
#
# On the VM:
#   bash deploy.sh [--env-file FILE] [--public-url URL]
# From your laptop over SSH (copies the env file to the VM, then runs this script there):
#   bash deploy/nebius/deploy.sh --host postulo@<VM_IP> --env-file deploy/nebius/.env.production
#
# Options:
#   --host USER@IP     run on that VM over SSH instead of locally
#   --env-file FILE    settings file to install as <repo>/.env (see .env.production.example)
#   --public-url URL   overrides PUBLIC_URL from the env file (http://<ip> or https://<domain>)
#   --repo URL         git URL to clone (default: $REPO_URL or the public GitHub HTTPS URL)
#   --branch NAME      git branch (default: main)
#   --dir PATH         checkout folder on the VM (default: ~/postulo)
#   --forward-agent    with --host: forward your SSH agent (for a private repo over SSH)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/faizan94/postulo.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-$HOME/postulo}"
HOST=""
ENV_FILE=""
PUBLIC_URL_ARG=""
FORWARD_AGENT=false
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-600}"

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:?--host needs USER@IP}"; shift 2 ;;
    --env-file) ENV_FILE="${2:?--env-file needs a path}"; shift 2 ;;
    --public-url) PUBLIC_URL_ARG="${2:?--public-url needs a URL}"; shift 2 ;;
    --repo) REPO_URL="${2:?--repo needs a URL}"; shift 2 ;;
    --branch) BRANCH="${2:?--branch needs a name}"; shift 2 ;;
    --dir) APP_DIR="${2:?--dir needs a path}"; shift 2 ;;
    --forward-agent) FORWARD_AGENT=true; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
done

# ---------------------------------------------------------------------------
# Remote mode: copy the env file, then run this same script on the VM.
# ---------------------------------------------------------------------------
if [[ -n "$HOST" ]]; then
  ssh_opts=(-o StrictHostKeyChecking=accept-new)
  [[ "$FORWARD_AGENT" == "true" ]] && ssh_opts+=(-A)
  remote_args=(--repo "$REPO_URL" --branch "$BRANCH")
  [[ "$APP_DIR" != "$HOME/postulo" ]] && remote_args+=(--dir "$APP_DIR")
  [[ -n "$PUBLIC_URL_ARG" ]] && remote_args+=(--public-url "$PUBLIC_URL_ARG")

  if [[ -n "$ENV_FILE" ]]; then
    [[ -f "$ENV_FILE" ]] || die "Env file not found: $ENV_FILE"
    log "Copying $ENV_FILE to $HOST:~/.postulo.env (mode 600)"
    ssh "${ssh_opts[@]}" "$HOST" 'umask 077; cat > "$HOME/.postulo.env"' < "$ENV_FILE"
    remote_args+=(--env-file .postulo.env)   # relative to the remote home folder
  fi

  log "Running deploy on $HOST"
  # bash -s reads this script from stdin and runs it on the VM (in the remote home folder).
  ssh "${ssh_opts[@]}" "$HOST" "bash -s -- $(printf '%q ' "${remote_args[@]}")" < "${BASH_SOURCE[0]}"
  exit 0
fi

# ---------------------------------------------------------------------------
# From here on we are on the VM.
# ---------------------------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is missing. Did cloud-init finish? Run: cloud-init status --wait"
command -v docker >/dev/null 2>&1 || die "docker is missing. Did cloud-init finish? Run: cloud-init status --wait"
if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  DOCKER=(sudo docker)   # the docker group applies only after a new login
fi
"${DOCKER[@]}" compose version >/dev/null 2>&1 || die "docker compose plugin is missing."

if [[ -n "$ENV_FILE" ]]; then   # make it absolute before we cd into the repo
  [[ -f "$ENV_FILE" ]] || die "Env file not found: $ENV_FILE"
  ENV_FILE="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
fi

# 1. Code ------------------------------------------------------------------
if [[ -d "$APP_DIR/.git" ]]; then
  log "Updating $APP_DIR ($BRANCH)"
  git -C "$APP_DIR" fetch --prune origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  log "Cloning $REPO_URL ($BRANCH) into $APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
echo "Commit: $(git rev-parse --short HEAD)"

# 2. .env ------------------------------------------------------------------
if [[ -n "$ENV_FILE" ]]; then
  [[ -f "$ENV_FILE" ]] || die "Env file not found: $ENV_FILE"
  log "Installing $ENV_FILE as $APP_DIR/.env"
  install -m 600 "$ENV_FILE" .env
fi
if [[ ! -f .env ]]; then
  install -m 600 deploy/nebius/.env.production.example .env
  die "Created $APP_DIR/.env from the example. Fill in PUBLIC_URL, NEBIUS_API_KEY, TAVILY_API_KEY, then run again."
fi
sed -i 's/\r$//' .env    # files edited on Windows have CRLF line ends
chmod 600 .env

env_get() {   # last value of KEY in .env, without surrounding quotes
  local v
  v="$(grep -E "^[[:space:]]*$1=" .env | tail -n 1 | cut -d= -f2- || true)"
  v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
  printf '%s' "$v"
}
env_set() {   # replace or append KEY=VALUE in .env
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { done = 0 }
    $0 ~ "^[[:space:]]*" k "=" { if (!done) { print k "=" v; done = 1 }; next }
    { print }
    END { if (!done) print k "=" v }
  ' .env > "$tmp"
  cat "$tmp" > .env
  rm -f "$tmp"
}

log "Checking .env"
NEBIUS_API_KEY_VALUE="$(env_get NEBIUS_API_KEY)"
TAVILY_API_KEY_VALUE="$(env_get TAVILY_API_KEY)"
MOCK_MODE_VALUE="$(env_get MOCK_MODE | tr '[:upper:]' '[:lower:]')"
case "$MOCK_MODE_VALUE" in
  true|false) ;;
  *) die "MOCK_MODE must be set to true or false in $APP_DIR/.env" ;;
esac
if [[ "$MOCK_MODE_VALUE" == "true" ]]; then
  echo "Warning: MOCK_MODE=true, the app will show fake data (API keys not needed)."
else
  [[ -n "$NEBIUS_API_KEY_VALUE" ]] || die "NEBIUS_API_KEY is empty in $APP_DIR/.env (needed when MOCK_MODE=false)"
  [[ -n "$TAVILY_API_KEY_VALUE" ]] || die "TAVILY_API_KEY is empty in $APP_DIR/.env (needed when MOCK_MODE=false)"
fi

PUBLIC_URL="${PUBLIC_URL_ARG:-$(env_get PUBLIC_URL)}"
PUBLIC_URL="${PUBLIC_URL%/}"
[[ "$PUBLIC_URL" =~ ^https?://[^/[:space:]]+$ ]] \
  || die "PUBLIC_URL must look like http://<VM_IP> or https://<domain> (no path). Got: '${PUBLIC_URL}'"
[[ "$PUBLIC_URL" == *YOUR_VM_PUBLIC_IP* ]] && die "Replace the PUBLIC_URL placeholder in .env."

if [[ "$PUBLIC_URL" == https://* ]]; then
  SITE_ADDRESS="${PUBLIC_URL#https://}"   # Caddy gets a certificate for this domain
else
  SITE_ADDRESS=":80"                      # plain HTTP on any host name / IP
fi

# Same origin: the browser calls the API through Caddy at PUBLIC_URL.
env_set PUBLIC_URL "$PUBLIC_URL"
env_set NEXT_PUBLIC_API_URL "$PUBLIC_URL"
env_set CORS_ORIGINS "$PUBLIC_URL"
env_set SITE_ADDRESS "$SITE_ADDRESS"
echo "PUBLIC_URL / NEXT_PUBLIC_API_URL / CORS_ORIGINS = $PUBLIC_URL"
echo "Caddy site address = $SITE_ADDRESS"

# 3. Build and start ------------------------------------------------------
COMPOSE=("${DOCKER[@]}" compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml)
log "Building and starting containers (the first frontend build takes several minutes)"
"${COMPOSE[@]}" up -d --build --remove-orphans

# 4. Health ---------------------------------------------------------------
log "Waiting for the backend health check"
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
backend_id="$("${COMPOSE[@]}" ps -q backend)"
while :; do
  status="$("${DOCKER[@]}" inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$backend_id" 2>/dev/null || echo unknown)"
  [[ "$status" == "healthy" ]] && break
  if (( $(date +%s) > deadline )); then
    "${COMPOSE[@]}" logs --tail 50 backend || true
    die "Backend is not healthy (status: $status). Logs above."
  fi
  sleep 5
done
echo "Backend: healthy"

log "Checking /health through Caddy"
if [[ "$SITE_ADDRESS" == ":80" ]]; then
  check=(curl -fsS --max-time 5 http://127.0.0.1/health)
else
  check=(curl -fsS --max-time 5 --resolve "$SITE_ADDRESS:443:127.0.0.1" "https://$SITE_ADDRESS/health")
fi
ok=false
for _ in $(seq 1 24); do
  if "${check[@]}" >/dev/null 2>&1; then ok=true; break; fi
  sleep 5
done
if [[ "$ok" == "true" ]]; then
  echo "Caddy -> backend: OK"
else
  echo "Warning: /health through Caddy failed. With a domain, the certificate may still be pending."
  echo "Check: ${COMPOSE[*]} logs caddy"
fi

"${COMPOSE[@]}" ps
log "Postulo is live at $PUBLIC_URL"
echo "API docs: $PUBLIC_URL/docs"
