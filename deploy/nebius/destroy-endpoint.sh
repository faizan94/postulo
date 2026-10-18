#!/usr/bin/env bash
# Delete the Nebius Serverless AI endpoint (and optionally the registry image is left).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"

ENDPOINT_NAME="${ENDPOINT_NAME:-postulo}"
ENDPOINT_ID="${ENDPOINT_ID:-$(cat "$DIR/.state/endpoint_id" 2>/dev/null || true)}"

if [[ -z "$ENDPOINT_ID" ]]; then
  ENDPOINT_ID=$(nebius ai endpoint get-by-name --name "$ENDPOINT_NAME" --format json 2>/dev/null \
    | jq -r '.metadata.id // empty' || true)
fi
[[ -n "$ENDPOINT_ID" ]] || { echo "No endpoint to delete." >&2; exit 1; }

echo "Deleting endpoint ${ENDPOINT_ID}..."
nebius ai endpoint delete --id "$ENDPOINT_ID"
rm -f "$DIR/.state/endpoint_id" "$DIR/.state/endpoint_url"
echo "Done."
