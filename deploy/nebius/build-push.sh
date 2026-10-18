#!/usr/bin/env bash
# Build the all-in-one Postulo image and push it to Nebius Container Registry.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"

need() { command -v "$1" >/dev/null || { echo "Missing dependency: $1" >&2; exit 1; }; }
need nebius
need jq
need docker

PROJECT_ID="${PROJECT_ID:-$(nebius config get parent-id)}"
REGION="${REGION:-uk-south2}"
REGISTRY_NAME="${REGISTRY_NAME:-postulo}"
IMAGE_NAME="${IMAGE_NAME:-postulo}"
TAG="${TAG:-latest}"
STATE_DIR="$DIR/.state"
mkdir -p "$STATE_DIR"

echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"

REGISTRY_ID=$(nebius registry list --parent-id "$PROJECT_ID" --format json \
  | jq -r --arg n "$REGISTRY_NAME" '.items[]? | select(.metadata.name==$n) | .metadata.id' \
  | head -1)
if [[ -z "$REGISTRY_ID" ]]; then
  echo "Creating registry '${REGISTRY_NAME}'..."
  REGISTRY_ID=$(nebius registry create \
    --name "$REGISTRY_NAME" \
    --parent-id "$PROJECT_ID" \
    --format json | jq -r '.metadata.id')
fi
echo "Registry: $REGISTRY_ID"
echo "$REGISTRY_ID" >"$STATE_DIR/registry_id"

# Nebius image path uses the registry id WITHOUT the "registry-" prefix.
REGISTRY_PATH="${REGISTRY_ID#registry-}"
IMAGE="cr.${REGION}.nebius.cloud/${REGISTRY_PATH}/${IMAGE_NAME}:${TAG}"
echo "Image:    $IMAGE"

echo "Logging into Container Registry..."
nebius registry configure-helper 2>/dev/null || true
nebius iam get-access-token | docker login "cr.${REGION}.nebius.cloud" \
  --username iam --password-stdin

echo "Building (linux/amd64 for Nebius)..."
docker build \
  --platform linux/amd64 \
  --pull \
  -f "$DIR/serverless/Dockerfile" \
  --build-arg NEXT_PUBLIC_API_URL= \
  -t "$IMAGE" \
  "$ROOT"

echo "Pushing..."
docker push "$IMAGE"
echo "$IMAGE" >"$STATE_DIR/image"

echo
echo "Pushed $IMAGE"
echo "Next: ./deploy/nebius/deploy-endpoint.sh"
