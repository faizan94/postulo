#!/usr/bin/env bash
# Create a Nebius CPU VM with Docker ready for Postulo.
# Requires: nebius CLI (authenticated), jq, an SSH public key.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$DIR/.env.nebius" ]] && source "$DIR/.env.nebius"

need() { command -v "$1" >/dev/null || { echo "Missing dependency: $1" >&2; exit 1; }; }
need nebius
need jq

PROJECT_ID="${PROJECT_ID:-$(nebius config get parent-id)}"
VM_NAME="${VM_NAME:-postulo}"
PLATFORM="${PLATFORM:-cpu-d3}"
PRESET="${PRESET:-2vcpu-8gb}"
DISK_GIB="${DISK_GIB:-80}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu24.04-driverless}"
SSH_USER="${SSH_USER:-postulo}"
SSH_PUBKEY="${SSH_PUBKEY:-${HOME}/.ssh/id_ed25519.pub}"
[[ -f "$SSH_PUBKEY" ]] || SSH_PUBKEY="${HOME}/.ssh/id_rsa.pub"
[[ -f "$SSH_PUBKEY" ]] || { echo "Set SSH_PUBKEY to an existing public key file." >&2; exit 1; }

STATE_DIR="$DIR/.state"
mkdir -p "$STATE_DIR"

echo "Project:  $PROJECT_ID"
echo "VM:       $VM_NAME ($PLATFORM / $PRESET)"
echo "SSH key:  $SSH_PUBKEY"

if [[ -z "${SUBNET_ID:-}" ]]; then
  echo "Looking up an existing subnet in the project…"
  SUBNET_ID=$(nebius vpc subnet list --parent-id "$PROJECT_ID" --format json \
    | jq -r '.items[0].metadata.id // empty')
  if [[ -z "$SUBNET_ID" ]]; then
    echo "No subnet found; trying to create a VPC network + subnet…"
    NETWORK_ID=$(nebius vpc network create \
      --name "${VM_NAME}-net" \
      --parent-id "$PROJECT_ID" \
      --format json | jq -r '.metadata.id')
    SUBNET_ID=$(nebius vpc subnet create \
      --name "${VM_NAME}-subnet" \
      --parent-id "$PROJECT_ID" \
      --network-id "$NETWORK_ID" \
      --ipv4-cidr-blocks '["10.20.0.0/24"]' \
      --format json | jq -r '.metadata.id')
    echo "Network:  $NETWORK_ID"
    echo "$NETWORK_ID" >"$STATE_DIR/network_id"
  fi
fi
echo "Subnet:   $SUBNET_ID"
echo "$SUBNET_ID" >"$STATE_DIR/subnet_id"

SSH_PUBLIC_KEY="$(cat "$SSH_PUBKEY")"
CLOUD_INIT="$(sed "s|SSH_KEY_PLACEHOLDER|${SSH_PUBLIC_KEY}|g" "$DIR/cloud-init.yaml")"

echo "Creating VM…"
INSTANCE_JSON=$(nebius compute instance create \
  --name "$VM_NAME" \
  --parent-id "$PROJECT_ID" \
  --resources-platform "$PLATFORM" \
  --resources-preset "$PRESET" \
  --boot-disk-managed-disk-name "${VM_NAME}-boot" \
  --boot-disk-managed-disk-type network_ssd \
  --boot-disk-managed-disk-size-gibibytes "$DISK_GIB" \
  --boot-disk-managed-disk-source-image-family-image-family "$IMAGE_FAMILY" \
  --boot-disk-attach-mode READ_WRITE \
  --network-interfaces "[{\"name\":\"eth0\",\"subnet_id\":\"${SUBNET_ID}\",\"ip_address\":{},\"public_ip_address\":{}}]" \
  --cloud-init-user-data "$CLOUD_INIT" \
  --format json)

INSTANCE_ID=$(echo "$INSTANCE_JSON" | jq -r '.metadata.id')
echo "$INSTANCE_ID" >"$STATE_DIR/instance_id"
echo "Instance: $INSTANCE_ID"

echo "Waiting for RUNNING…"
PUBLIC_IP=""
for _ in $(seq 1 60); do
  INFO=$(nebius compute instance get --id "$INSTANCE_ID" --format json)
  STATE=$(echo "$INFO" | jq -r '.status.state // .status // empty')
  PUBLIC_IP=$(echo "$INFO" | jq -r '
    .status.network_interfaces[0].public_ip_address.address //
    .status.network_interfaces[0].public_ip_address //
    empty' | cut -d/ -f1)
  echo "  state=$STATE ip=${PUBLIC_IP:-…}"
  if [[ "$STATE" == "RUNNING" && -n "$PUBLIC_IP" ]]; then
    break
  fi
  sleep 5
done
[[ -n "$PUBLIC_IP" ]] || { echo "Timed out waiting for public IP." >&2; exit 1; }
echo "$PUBLIC_IP" >"$STATE_DIR/public_ip"

echo "Waiting for cloud-init (Docker)…"
for _ in $(seq 1 36); do
  if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
    "${SSH_USER}@${PUBLIC_IP}" "test -f /opt/postulo/.bootstrap-ok" 2>/dev/null; then
    break
  fi
  sleep 5
done

cat >"$STATE_DIR/ssh.env" <<EOF
export POSTULO_HOST=$PUBLIC_IP
export POSTULO_SSH=${SSH_USER}@${PUBLIC_IP}
export POSTULO_INSTANCE_ID=$INSTANCE_ID
EOF

echo
echo "VM ready."
echo "  SSH:   ssh ${SSH_USER}@${PUBLIC_IP}"
echo "  Next:  ./deploy/nebius/deploy.sh"
echo "  State: $STATE_DIR"
