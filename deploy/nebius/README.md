# Deploy Postulo on Nebius AI Cloud

Minimum setup: one **CPU** VM running the existing `docker compose` stack.
Nemotron stays on **Token Factory** (no GPU on this VM).

```
Browser → :3000 frontend → :8000 backend → Token Factory + Tavily
                                 └── SQLite volume
```

## Prerequisites

1. **Nebius CLI** ([install docs](https://docs.nebius.com/cli/install)):

   ```bash
   curl -sSL https://artifacts.nebius.cloud/cli/install.sh | bash
   exec -l $SHELL
   nebius version
   ```

   Then create a profile (project ID from the Nebius console → project):

   ```bash
   export PROJECT_ID=<your_project_id>
   nebius profile create \
     --profile postulo \
     --endpoint api.nebius.cloud \
     --federation-endpoint auth.nebius.com \
     --parent-id "$PROJECT_ID"
   # complete browser login, then:
   nebius iam whoami
   ```

2. `jq`, `rsync`, `ssh`
3. An SSH key pair (`~/.ssh/id_ed25519.pub` or `id_rsa.pub`)
4. Repo-root `.env` with `NEBIUS_API_KEY` and `TAVILY_API_KEY` filled in

Optional: copy `env.example` → `.env.nebius` to override VM size / name.

If `vpc network create` returns **PermissionDenied**, set `SUBNET_ID` to the
project’s existing default subnet (console → VPC, or
`nebius vpc subnet list --parent-id "$PROJECT_ID"`) instead of creating a new network.

## One-time: create the VM

```bash
./deploy/nebius/create-vm.sh
```

Creates a `cpu-d3` / `2vcpu-8gb` Ubuntu VM, installs Docker via cloud-init, and writes
connection details under `deploy/nebius/.state/` (gitignored).

## Deploy / update the app

```bash
./deploy/nebius/deploy.sh
```

Syncs the repo to `/opt/postulo`, uploads a server `.env` with:

- `MOCK_MODE=false`
- `CORS_ORIGINS=http://<public-ip>:3000`
- `NEXT_PUBLIC_API_URL=http://<public-ip>:8000`

then builds and starts compose.

Open:

- UI: `http://<public-ip>:3000`
- API: `http://<public-ip>:8000/docs`

## Tear down

```bash
./deploy/nebius/destroy.sh
# also delete the VPC created by create-vm.sh:
DESTROY_NETWORK=1 ./deploy/nebius/destroy.sh
```

## Notes

- Rebuild after changing the public IP or `NEXT_PUBLIC_*` (values are baked at frontend build time).
- SQLite lives in the `postulo-data` Docker volume — fine for a demo, not for multi-replica.
- Ports 3000/8000 are exposed on the public IP; add TLS/reverse proxy before sharing widely.
