#!/usr/bin/env bash
# Delete the Postulo Nebius VM (and optional network created by create-vm.sh).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"
[[ -f "$DIR/.state/ssh.env" ]] && source "$DIR/.state/ssh.env"

STATE="$DIR/.state"
INSTANCE_ID="${POSTULO_INSTANCE_ID:-$(cat "$STATE/instance_id" 2>/dev/null || true)}"
SUBNET_ID="$(cat "$STATE/subnet_id" 2>/dev/null || true)"
NETWORK_ID="$(cat "$STATE/network_id" 2>/dev/null || true)"

[[ -n "$INSTANCE_ID" ]] || { echo "No instance id in $STATE/instance_id" >&2; exit 1; }

echo "Deleting instance ${INSTANCE_ID}..."
nebius compute instance delete --id "$INSTANCE_ID" || true

if [[ "${DESTROY_NETWORK:-0}" == "1" && -n "$NETWORK_ID" ]]; then
  echo "Deleting subnet/network (DESTROY_NETWORK=1)..."
  [[ -n "$SUBNET_ID" ]] && nebius vpc subnet delete --id "$SUBNET_ID" || true
  nebius vpc network delete --id "$NETWORK_ID" || true
fi

rm -rf "$STATE"
echo "Done. Set DESTROY_NETWORK=1 next time to also remove the VPC created by create-vm.sh."
