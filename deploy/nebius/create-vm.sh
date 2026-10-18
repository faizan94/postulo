#!/usr/bin/env bash
# Create the Postulo VM on Nebius AI Cloud with the nebius CLI.
#
# Run it on macOS, Linux or WSL (the nebius CLI supports Ubuntu and macOS):
#   PROJECT_ID=project-... bash deploy/nebius/create-vm.sh
#
# Safe to run again: if a VM with VM_NAME already exists, it only prints its public IP.
# Needs: nebius (logged in, see README.md step 2), jq, ssh, an SSH public key.
set -euo pipefail

# ---------------------------------------------------------------------------
# Settings (override any of them with environment variables)
# ---------------------------------------------------------------------------
PROJECT_ID="${PROJECT_ID:-}"                       # required: console -> project menu -> Copy project ID
VM_NAME="${VM_NAME:-postulo-vm}"
PLATFORM="${PLATFORM:-cpu-d3}"                     # CPU-only AMD EPYC Genoa (cpu-e2 exists only in eu-north1)
PRESET="${PRESET:-2vcpu-8gb}"                      # 2 vCPU / 8 GB
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu24.04-driverless}"
DISK_TYPE="${DISK_TYPE:-network_ssd}"
DISK_SIZE_GIB="${DISK_SIZE_GIB:-50}"               # Docker images + build cache + SQLite
SUBNET_ID="${SUBNET_ID:-}"                         # empty = first subnet in the project
SSH_USER="${SSH_USER:-postulo}"                    # "root" and "admin" are not allowed
SSH_PUBLIC_KEY_FILE="${SSH_PUBLIC_KEY_FILE:-$HOME/.ssh/id_ed25519.pub}"
STATIC_IP="${STATIC_IP:-false}"                    # true = keep the same IP across stop/start
WAIT_FOR_BOOTSTRAP="${WAIT_FOR_BOOTSTRAP:-true}"   # wait over SSH until Docker is installed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD_INIT_FILE="$SCRIPT_DIR/cloud-init.yaml"

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
command -v nebius >/dev/null 2>&1 || die "nebius CLI not found. Install: curl -sSL https://artifacts.nebius.cloud/cli/install.sh | bash"
command -v jq >/dev/null 2>&1 || die "jq not found. Install it (Ubuntu: sudo apt-get install -y jq, macOS: brew install jq)."
[[ -n "$PROJECT_ID" ]] || die "Set PROJECT_ID (web console: project list -> ... -> Copy project ID)."
[[ -f "$SSH_PUBLIC_KEY_FILE" ]] || die "No SSH public key at $SSH_PUBLIC_KEY_FILE. Create one: ssh-keygen -t ed25519"
[[ -f "$CLOUD_INIT_FILE" ]] || die "Missing $CLOUD_INIT_FILE"
case "$SSH_USER" in root|admin) die "SSH_USER cannot be root or admin on Nebius." ;; esac

get_public_ip() {
  nebius compute instance get-by-name --parent-id "$PROJECT_ID" --name "$VM_NAME" --format json \
    | jq -r '.status.network_interfaces[0].public_ip_address.address // empty | split("/")[0]'
}

wait_for_ip() {
  local ip=""
  for _ in $(seq 1 30); do
    ip="$(get_public_ip || true)"
    [[ -n "$ip" ]] && { echo "$ip"; return 0; }
    sleep 5
  done
  return 1
}

# ---------------------------------------------------------------------------
# 1. Reuse the VM if it already exists
# ---------------------------------------------------------------------------
log "Checking for an existing VM named '$VM_NAME' in $PROJECT_ID"
if nebius compute instance get-by-name --parent-id "$PROJECT_ID" --name "$VM_NAME" --format json >/dev/null 2>&1; then
  echo "VM '$VM_NAME' already exists. Nothing to create."
else
  # -------------------------------------------------------------------------
  # 2. Subnet
  # -------------------------------------------------------------------------
  if [[ -z "$SUBNET_ID" ]]; then
    log "Finding a subnet"
    SUBNET_ID="$(nebius vpc subnet list --parent-id "$PROJECT_ID" --format json | jq -r '.items[0].metadata.id // empty')"
    [[ -n "$SUBNET_ID" ]] || die "No subnet found. Create a network in the console (Networking -> Virtual Networks) or set SUBNET_ID."
  fi
  echo "Subnet: $SUBNET_ID"

  # -------------------------------------------------------------------------
  # 3. Cloud-init with your SSH user and key
  # -------------------------------------------------------------------------
  log "Preparing cloud-init (user '$SSH_USER', key $SSH_PUBLIC_KEY_FILE)"
  SSH_PUBLIC_KEY="$(tr -d '\r\n' < "$SSH_PUBLIC_KEY_FILE")"
  USER_DATA="$(cat "$CLOUD_INIT_FILE")"
  USER_DATA="${USER_DATA//__SSH_USER__/"$SSH_USER"}"
  USER_DATA="${USER_DATA//__SSH_PUBLIC_KEY__/"$SSH_PUBLIC_KEY"}"

  if [[ "$STATIC_IP" == "true" ]]; then
    PUBLIC_IP_SPEC='{"static": true}'
  else
    PUBLIC_IP_SPEC='{}'
  fi
  NETWORK_INTERFACES="[{\"name\": \"eth0\", \"subnet_id\": \"$SUBNET_ID\", \"ip_address\": {}, \"public_ip_address\": $PUBLIC_IP_SPEC}]"

  # -------------------------------------------------------------------------
  # 4. Create the VM (boot disk is created from the Ubuntu image and managed by the VM)
  # -------------------------------------------------------------------------
  log "Creating VM '$VM_NAME' ($PLATFORM / $PRESET, $IMAGE_FAMILY, ${DISK_SIZE_GIB} GiB $DISK_TYPE). This takes a few minutes."
  nebius compute instance create \
    --parent-id "$PROJECT_ID" \
    --name "$VM_NAME" \
    --resources-platform "$PLATFORM" \
    --resources-preset "$PRESET" \
    --boot-disk-attach-mode read_write \
    --boot-disk-managed-disk-name "${VM_NAME}-boot" \
    --boot-disk-managed-disk-type "$DISK_TYPE" \
    --boot-disk-managed-disk-size-gibibytes "$DISK_SIZE_GIB" \
    --boot-disk-managed-disk-source-image-family-image-family "$IMAGE_FAMILY" \
    --cloud-init-user-data "$USER_DATA" \
    --network-interfaces "$NETWORK_INTERFACES" \
    --format json >/dev/null
  echo "VM created."
fi

# ---------------------------------------------------------------------------
# 5. Public IP
# ---------------------------------------------------------------------------
log "Reading the public IP"
PUBLIC_IP="$(wait_for_ip)" || die "No public IP yet. Check the VM in the console (Compute -> Virtual machines)."

# ---------------------------------------------------------------------------
# 6. Wait until cloud-init has installed Docker
# ---------------------------------------------------------------------------
if [[ "$WAIT_FOR_BOOTSTRAP" == "true" ]]; then
  log "Waiting for SSH and cloud-init on $SSH_USER@$PUBLIC_IP (up to ~10 minutes)"
  ready=false
  for _ in $(seq 1 60); do
    if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes \
         "$SSH_USER@$PUBLIC_IP" 'test -f /var/lib/postulo-bootstrap-done' 2>/dev/null; then
      ready=true
      break
    fi
    sleep 10
  done
  if [[ "$ready" == "true" ]]; then
    echo "Docker is installed on the VM."
  else
    echo "Not ready yet. Check later with: ssh $SSH_USER@$PUBLIC_IP 'cloud-init status --wait'"
  fi
fi

log "Done"
echo "Public IP:  $PUBLIC_IP"
echo "SSH:        ssh $SSH_USER@$PUBLIC_IP"
echo "Next:       set PUBLIC_URL=http://$PUBLIC_IP in deploy/nebius/.env.production, then"
echo "            bash deploy/nebius/deploy.sh --host $SSH_USER@$PUBLIC_IP --env-file deploy/nebius/.env.production"
