# Deploy Postulo on Nebius AI Cloud

One **Serverless AI** endpoint. nginx fronts FastAPI and Next.js behind a managed HTTPS URL. Nemotron stays on **Token Factory**.

```
Browser ──HTTPS──► Nebius endpoint :8080 (nginx)
                      ├─ /api, /health, /docs  → FastAPI :8000
                      └─ /                     → Next.js :3000
                                                  └─ Token Factory + Tavily
```

## Prerequisites

1. Nebius CLI installed and logged in ([install](https://docs.nebius.com/cli/install))
2. Docker Desktop (builds `linux/amd64` images)
3. `jq`
4. Repo-root `.env` with `NEBIUS_API_KEY`, `TAVILY_API_KEY` and `MOCK_MODE=false`
5. Local config: `deploy/nebius/.env.nebius`, copied from `.env.nebius.example` (optional; the defaults work)

## Deploy

```bash
cp deploy/nebius/.env.nebius.example deploy/nebius/.env.nebius   # once; set PROJECT_ID if needed
./deploy/nebius/build-push.sh      # build + push to Nebius Container Registry
./deploy/nebius/deploy-endpoint.sh # create or replace the Serverless AI endpoint
```

Or: `make nebius-build` then `make nebius-endpoint`.

The script prints the managed URL.

```bash
nebius ai endpoint logs "$(cat deploy/nebius/.state/endpoint_id)"
./deploy/nebius/destroy-endpoint.sh
```

## Notes

- Endpoint auth is `--auth none`. The app keeps its own login token.
- The frontend is built with an empty `NEXT_PUBLIC_API_URL`, so the browser calls same-origin `/api/…` through nginx.
- The registry image path uses the registry id **without** the `registry-` prefix.
- SQLite lives on the endpoint disk. Replacing the endpoint clears it.
- To update the app, re-run `build-push.sh`, then `deploy-endpoint.sh`.
