#!/usr/bin/env bash
# Create or update a Nebius Serverless AI endpoint running the Postulo image.
# nginx (:8080) fronts FastAPI + Next.js on one managed HTTPS URL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"
[[ -f "$DIR/.state/image" ]] || {
  echo "No image in .state — run ./deploy/nebius/build-push.sh first." >&2
  exit 1
}

need() { command -v "$1" >/dev/null || { echo "Missing dependency: $1" >&2; exit 1; }; }
need nebius
need jq

PROJECT_ID="${PROJECT_ID:-$(nebius config get parent-id)}"
SUBNET_ID="${SUBNET_ID:-}"
ENDPOINT_NAME="${ENDPOINT_NAME:-postulo}"
PLATFORM="${PLATFORM:-cpu-d3}"
PRESET="${PRESET:-2vcpu-8gb}"
DISK_SIZE="${DISK_SIZE:-40Gi}"
IMAGE="$(cat "$DIR/.state/image")"
STATE_DIR="$DIR/.state"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

[[ -f "$ENV_FILE" ]] || {
  echo "Missing $ENV_FILE with NEBIUS_API_KEY and TAVILY_API_KEY." >&2
  exit 1
}

# Pull selected keys from local .env into --env flags (no secrets printed).
env_from_dotenv() {
  local key="$1" default="${2:-}"
  local val
  val="$(awk -F= -v k="$key" '$1==k {sub(/^[^=]*=/,""); print; exit}' "$ENV_FILE")"
  if [[ -z "$val" ]]; then
    val="$default"
  fi
  # strip surrounding quotes
  val="${val%\"}"
  val="${val#\"}"
  val="${val%\'}"
  val="${val#\'}"
  printf '%s' "$val"
}

MOCK_MODE="$(env_from_dotenv MOCK_MODE false)"
NEBIUS_API_KEY="$(env_from_dotenv NEBIUS_API_KEY)"
TAVILY_API_KEY="$(env_from_dotenv TAVILY_API_KEY)"
NEBIUS_BASE_URL="$(env_from_dotenv NEBIUS_BASE_URL https://api.tokenfactory.nebius.com/v1/)"
NEMOTRON_MODEL="$(env_from_dotenv NEMOTRON_MODEL)"
NEMOTRON_FAST_MODEL="$(env_from_dotenv NEMOTRON_FAST_MODEL)"
LOG_LEVEL="$(env_from_dotenv LOG_LEVEL INFO)"

[[ -n "$NEBIUS_API_KEY" && -n "$TAVILY_API_KEY" ]] || {
  echo "NEBIUS_API_KEY and TAVILY_API_KEY must be set in $ENV_FILE" >&2
  exit 1
}

if [[ -z "$SUBNET_ID" ]]; then
  SUBNET_ID=$(nebius vpc subnet list --parent-id "$PROJECT_ID" --format json \
    | jq -r '.items[0].metadata.id // empty')
fi
[[ -n "$SUBNET_ID" ]] || { echo "No subnet found for project." >&2; exit 1; }

EXISTING=$(nebius ai endpoint get-by-name --name "$ENDPOINT_NAME" --format json 2>/dev/null \
  | jq -r '.metadata.id // empty' || true)

COMMON=(
  --image "$IMAGE"
  --platform "$PLATFORM"
  --preset "$PRESET"
  --container-port 8080
  --auth none
  --subnet-id "$SUBNET_ID"
  --disk-size "$DISK_SIZE"
  --parent-id "$PROJECT_ID"
  --env "MOCK_MODE=${MOCK_MODE}"
  --env "NEBIUS_API_KEY=${NEBIUS_API_KEY}"
  --env "TAVILY_API_KEY=${TAVILY_API_KEY}"
  --env "NEBIUS_BASE_URL=${NEBIUS_BASE_URL}"
  --env "LOG_LEVEL=${LOG_LEVEL}"
  # Same-origin via nginx: browser talks to one HTTPS URL; CORS unused.
)
[[ -n "$NEMOTRON_MODEL" ]] && COMMON+=(--env "NEMOTRON_MODEL=${NEMOTRON_MODEL}")
[[ -n "$NEMOTRON_FAST_MODEL" ]] && COMMON+=(--env "NEMOTRON_FAST_MODEL=${NEMOTRON_FAST_MODEL}")

if [[ -n "$EXISTING" ]]; then
  echo "Updating endpoint ${EXISTING} (${ENDPOINT_NAME})..."
  # delete + recreate is the reliable path for image updates
  nebius ai endpoint delete --id "$EXISTING"
  sleep 5
fi

echo "Creating endpoint ${ENDPOINT_NAME}..."
echo "  image:    $IMAGE"
echo "  platform: $PLATFORM / $PRESET"
CREATE_OUT=$(nebius ai endpoint create \
  --name "$ENDPOINT_NAME" \
  "${COMMON[@]}" \
  --format json)
ENDPOINT_ID=$(echo "$CREATE_OUT" | jq -r '.metadata.id // .resource_id // empty')
if [[ -z "$ENDPOINT_ID" ]]; then
  # async operation shape
  ENDPOINT_ID=$(echo "$CREATE_OUT" | jq -r '.resource_id // empty')
fi
[[ -n "$ENDPOINT_ID" ]] || {
  echo "Create failed:" >&2
  echo "$CREATE_OUT" >&2
  exit 1
}
echo "$ENDPOINT_ID" >"$STATE_DIR/endpoint_id"
echo "Endpoint: $ENDPOINT_ID"

echo "Waiting for RUNNING..."
URL=""
for _ in $(seq 1 90); do
  INFO=$(nebius ai endpoint get --id "$ENDPOINT_ID" --format json)
  STATE=$(echo "$INFO" | jq -r '.status.state // empty')
  URL=$(echo "$INFO" | jq -r '
    (.status.public_endpoints // [])[]?
    | select(startswith("https://"))
  ' | head -1)
  echo "  state=$STATE url=${URL:-...}"
  if [[ "$STATE" == "RUNNING" && -n "$URL" ]]; then
    break
  fi
  if [[ "$STATE" == "FAILED" || "$STATE" == "ERROR" ]]; then
    echo "$INFO" | jq .
    exit 1
  fi
  sleep 10
done
[[ -n "$URL" ]] || { echo "Timed out waiting for HTTPS URL." >&2; exit 1; }
echo "$URL" >"$STATE_DIR/endpoint_url"

echo
echo "Deployed."
echo "  UI:   $URL"
echo "  API:  $URL/docs"
echo "  Logs: nebius ai endpoint logs $ENDPOINT_ID"
