# Deploy Postulo on Nebius AI Cloud

**Preferred:** one **Serverless AI** endpoint — nginx fronts FastAPI + Next.js behind a managed HTTPS URL. Nemotron stays on **Token Factory**.

```
Browser ──HTTPS──► Nebius endpoint :8080 (nginx)
                      ├─ /api,/health,/docs  → FastAPI :8000
                      └─ /                   → Next.js :3000
                                              └─ Token Factory + Tavily
```

## Prerequisites

1. Nebius CLI installed and logged in ([install](https://docs.nebius.com/cli/install))
2. Docker Desktop running (builds `linux/amd64` images)
3. `jq`
4. Repo-root `.env` with `NEBIUS_API_KEY` and `TAVILY_API_KEY`
5. Local config: `deploy/nebius/.env.nebius` (see `env.example`)

## Deploy (Serverless AI + nginx)

```bash
./deploy/nebius/build-push.sh      # build + push to Nebius Container Registry
./deploy/nebius/deploy-endpoint.sh # create/replace Serverless AI endpoint
```

Or: `make nebius-build` then `make nebius-endpoint`.

The script prints the managed URL, e.g. `https://….ai.nebiususercontent.com`.

```bash
# logs / tear down
nebius ai endpoint logs "$(cat deploy/nebius/.state/endpoint_id)"
./deploy/nebius/destroy-endpoint.sh
```

### Notes

- Endpoint auth is `--auth none`; the app keeps its own login token.
- Frontend is built with empty `NEXT_PUBLIC_API_URL` so the browser calls same-origin `/api/…` through nginx.
- SQLite is ephemeral on the endpoint disk (fine for a demo). Restart/replace clears it.
- Updating the app: re-run `build-push.sh` then `deploy-endpoint.sh` (recreates the endpoint).

## Alternative: CPU VM + docker compose

Still available if you need a long-lived SSH box:

```bash
./deploy/nebius/create-vm.sh
./deploy/nebius/deploy.sh
./deploy/nebius/destroy.sh
```

If `vpc network create` is denied, set `SUBNET_ID` to the project default subnet in `.env.nebius`.
