# Deploy Postulo on Nebius AI Cloud

One small CPU VM runs the whole app with Docker Compose:

```
browser ──> Caddy :80 / :443 ──> /api/*, /health, /docs  ──> backend:8000 (FastAPI, SQLite in a Docker volume)
                             └─> everything else        ──> frontend:3000 (Next.js)
```

Browser, frontend and API share one origin, so `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` are both your public URL. `deploy.sh` sets them for you.

Files in this folder:

| File | What it does |
|---|---|
| `create-vm.sh` | Creates the VM with the `nebius` CLI and prints its public IP |
| `cloud-init.yaml` | First boot: adds your SSH user, installs Docker Engine, the compose plugin and git |
| `deploy.sh` | Clones or updates the repo on the VM, checks `.env`, builds, starts, waits for `/health` |
| `docker-compose.prod.yml` | Override: adds Caddy, hides ports 8000/3000, passes the public URL to the frontend build |
| `Caddyfile` | Reverse proxy rules. Automatic HTTPS if you use a domain |
| `.env.production.example` | Settings template (placeholders only) |

## 1. Prerequisites

1. A Nebius AI Cloud account with a project, and the `editor` role in it (you already use Token Factory).
2. A Nebius Token Factory API key and a Tavily API key.
3. An SSH key. If you have none: `ssh-keygen -t ed25519` (creates `~/.ssh/id_ed25519.pub`).
4. **Commit and push the `deploy/nebius/` folder.** The VM clones the repo from GitHub, so it only sees pushed files.
5. For the CLI path: macOS, Linux or WSL (the `nebius` CLI supports Ubuntu and macOS, not plain Windows), plus `jq`.
   On Windows without WSL, use the web console path in step 2 and run `deploy.sh` from Git Bash.

## 2. One-time cloud setup

### Option A: CLI

1. Install the CLI and check it:
   ```bash
   curl -sSL https://artifacts.nebius.cloud/cli/install.sh | bash
   exec -l $SHELL
   nebius version
   ```
2. Get your project ID: in the [web console](https://console.nebius.com), open the project list, click `...` next to the project, then **Copy project ID**.
3. Log in (a browser window opens):
   ```bash
   nebius profile create \
     --profile postulo \
     --endpoint api.nebius.cloud \
     --federation-endpoint auth.nebius.com \
     --parent-id <PROJECT_ID>
   nebius profile list
   ```
4. Create the VM (from the repo root):
   ```bash
   PROJECT_ID=<PROJECT_ID> bash deploy/nebius/create-vm.sh
   ```
   Defaults: `cpu-d3` / `2vcpu-8gb`, Ubuntu 24.04 (`ubuntu24.04-driverless`), 50 GiB `network_ssd`, user `postulo`, key `~/.ssh/id_ed25519.pub`, first subnet in the project, dynamic public IP.
   Change any of them with environment variables, e.g. `SSH_USER=faizan STATIC_IP=true PROJECT_ID=... bash deploy/nebius/create-vm.sh`.
   The script waits until Docker is installed, then prints the public IP. Running it again only prints the IP.

### Option B: web console

1. Go to **Compute → Virtual machines → Create resource → Virtual machine**.
2. Choose a platform **without GPUs** (`cpu-d3`, preset 2 vCPU / 8 GB) and an **Ubuntu 24.04** boot image; set the disk to about 50 GiB.
3. **Network**: keep the default subnet and turn on **Public IP address**.
4. **Access**: under **Username and SSH key**, click **Create** and paste your public key (the user name cannot be `root` or `admin`).
5. Create the VM, copy its public IP, then install Docker by hand:
   ```bash
   ssh <user>@<VM_IP>
   sudo apt-get update && sudo apt-get install -y ca-certificates curl git
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list
   sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker $USER && exit
   ```

### Firewall

Each Nebius network has a default security group that allows all inbound and outbound traffic, so ports 22, 80 and 443 work out of the box. If your network uses a custom security group, add an ingress rule: **Networking → Virtual Networks → Security groups →** your group **→ Create security rule**, direction ingress, action allow, source `0.0.0.0/0`, protocol TCP, ports `80` and `443` (and `22` for SSH).

## 3. Configure variables

```bash
cp deploy/nebius/.env.production.example deploy/nebius/.env.production   # git-ignored
```

Edit `deploy/nebius/.env.production`:

| Variable | What to put | Where to get it | Required |
|---|---|---|---|
| `PUBLIC_URL` | `http://<VM_IP>` or `https://<domain>`, no trailing slash | Output of `create-vm.sh` or the console; for a domain, point its DNS A record at the VM IP first | Yes |
| `NEBIUS_API_KEY` | Token Factory key | Token Factory console → API keys | Yes |
| `TAVILY_API_KEY` | `tvly-...` | https://app.tavily.com | Yes |
| `MOCK_MODE` | `false` for real searches (`true` = fake data) | — | Yes |
| `NEMOTRON_MODEL`, `NEMOTRON_FAST_MODEL`, `NEMOTRON_VISION_MODEL` | Keep the defaults unless your key lacks them | `cd backend && uv run python scripts/list_models.py` | No |
| `OCR_ENABLED` | `true` or `false` | — | No |
| `LOG_LEVEL`, `MAX_POSTINGS`, `MAX_TAVILY_CREDITS_PER_RUN`, `MAX_LLM_CALLS_PER_RUN`, `RECENT_DAYS` | Keep the defaults | — | No |
| `DATABASE_URL` | Keep `sqlite+aiosqlite:///./data/postulo.db` (lands in the `postulo-data` volume) | — | No |

Do not set `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` or `SITE_ADDRESS`. `deploy.sh` derives them from `PUBLIC_URL`.

## 4. Deploy

From your laptop (Git Bash, macOS, Linux or WSL), in the repo root:

```bash
bash deploy/nebius/deploy.sh --host postulo@<VM_IP> --env-file deploy/nebius/.env.production
```

The script copies the settings to the VM (mode 600), clones the repo into `~/postulo`, writes `~/postulo/.env`, runs
`docker compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml up -d --build`, waits for `/health` and prints the URL.
The first build takes several minutes (the Next.js build is the slow part).

Private repo? Add your key to ssh-agent (`ssh-add`) and run with `--repo git@github.com:faizan94/postulo.git --forward-agent`.

Open `PUBLIC_URL` in the browser. API docs: `PUBLIC_URL/docs`.

## 5. Update / redeploy

Push your changes, then run the same command again:

```bash
bash deploy/nebius/deploy.sh --host postulo@<VM_IP>                         # keep the .env on the VM
bash deploy/nebius/deploy.sh --host postulo@<VM_IP> --env-file deploy/nebius/.env.production   # also replace settings
```

It pulls `main` (`--branch` to change), rebuilds and restarts. The database is kept. Changing `PUBLIC_URL` always needs this full run, because the frontend must be rebuilt.

## 6. View logs

```bash
ssh postulo@<VM_IP>
cd ~/postulo
docker compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml logs -f --tail 100 backend   # or frontend, caddy
```

Tip: `alias dc='docker compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml'`.

## 7. Back up the SQLite database

The database is `/app/data/postulo.db` inside the `postulo-data` volume. It holds users' CV text, so keep backups private.

```bash
ssh postulo@<VM_IP> 'cd ~/postulo && dc() { docker compose -f docker-compose.yml -f deploy/nebius/docker-compose.prod.yml "$@"; } &&
  dc exec -T backend python -c "import sqlite3; s=sqlite3.connect(\"/app/data/postulo.db\"); d=sqlite3.connect(\"/app/data/backup.db\"); s.backup(d); d.close()" &&
  dc cp backend:/app/data/backup.db ./postulo-backup.db && dc exec -T backend rm /app/data/backup.db'
scp postulo@<VM_IP>:postulo/postulo-backup.db ./postulo-backup-$(date +%F).db
```

The Python `backup()` call makes a consistent copy while the app runs (the DB uses WAL mode, so do not just copy the file).

## 8. Tear down

1. Optional: back up the database (step 7).
2. Delete the VM: console **Compute → Virtual machines →** `postulo-vm` **→ Delete**, or
   ```bash
   nebius compute instance delete --id <INSTANCE_ID>
   ```
   Get the ID with `nebius compute instance get-by-name --parent-id <PROJECT_ID> --name postulo-vm --format json | jq -r .metadata.id`.
   This deletes the VM's managed disks too, and the database with them.
3. In the console, check **Compute → Disks** and the network's public IP allocations for leftovers (a static IP you reserved keeps billing until deleted).

## 9. Costs

You pay for the VM while it runs, its boot disk, and a static public IP if you chose one. Model calls are billed by Token Factory and searches by Tavily, as in local runs. A `2vcpu-8gb` CPU VM is one of the smallest presets. See current prices at https://nebius.com/prices and delete the VM when the demo is over.

## 10. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| **502 from Caddy** | Backend or frontend is not up yet or crashed. Run `dc ps` and `dc logs backend frontend`. The frontend starts only after the backend is healthy; the first build is slow. |
| **CORS error in the browser console** | `CORS_ORIGINS` does not equal the exact URL in the address bar (scheme, host, no slash). Fix `PUBLIC_URL` and rerun `deploy.sh`. If you open the app by IP while `PUBLIC_URL` is your domain (or the reverse), the origins differ. |
| **Blank page or "failed to fetch", requests go to `localhost:8000`** | `NEXT_PUBLIC_API_URL` was wrong when the frontend was built (it is baked into the JS bundle). Set `PUBLIC_URL` and rerun `deploy.sh` (it rebuilds). Check in DevTools → Network which host the `/api/...` calls use. |
| **Site does not load at all / timeout on port 80** | A custom security group blocks 80/443 (see Firewall in step 2), or the VM has no public IP. Test from the VM: `curl -i http://127.0.0.1/health`. If that works, it is the network. |
| **HTTPS certificate errors with a domain** | DNS A record must point to the VM IP and ports 80 and 443 must be open. See `dc logs caddy`. |
| **`503 missing_api_key`** | A key is empty in `~/postulo/.env` on the VM, or `MOCK_MODE` is wrong. Fix it, then `dc up -d backend`. |
| **`permission denied` on docker** | Log out and back in (the `docker` group applies on the next login). `deploy.sh` falls back to `sudo docker`. |
| **`!reset` error from compose** | Compose is older than 2.24.4. Install the `docker-compose-plugin` from Docker's apt repo (cloud-init does this). |
