# Postulo backend

FastAPI service: name login, CV versions, and the search pipeline (plan -> discover -> quiet checks -> requirements -> match -> rank).
It is managed with [uv](https://docs.astral.sh/uv/).

## Run

```bash
uv sync                                              # create .venv, install deps from uv.lock
uv run uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
```

Settings come from `../.env` (repo root) and then `./.env`, and real environment variables override both. With `MOCK_MODE=true`, no keys are needed.

## Test, lint, typecheck

```bash
uv run pytest            # no API keys or network needed
uv run ruff check .
uv run ruff format .
uv run mypy app
```

## Scripts

```bash
uv run python scripts/list_models.py      # Nemotron IDs on Token Factory
```

## Layout

| Path | What it does |
|---|---|
| `app/main.py` | App factory, lifespan (DB, event bus, runner, stale-run cleanup), error handler |
| `app/api/routes/` | `auth`, `me`, `places`, `cv`, `searches` (incl. live stream), `postings`, `how`, `health` |
| `app/agents/orchestrator.py` | The search state machine; saves and streams results as they come |
| `app/agents/discover.py` | Tavily -> company boards -> board APIs -> quiet checks |
| `app/agents/requirements.py` | Nemotron Lightning extraction (batched, quotes verified, cached) + rules fallback |
| `app/agents/profile.py`, `planner.py`, `llm_gate.py` | CV profile, query planning, the single LLM gate (budget + fallback) |
| `app/domain/` | Pure logic: evidence checks, glossary, places, titles, years, rule extraction, matching |
| `app/scoring/` | Match score, company score, rank key, skill summary, Gap ROI |
| `app/services/` | `llm.py`, `tavily_client.py`, `ats.py`, `html_text.py`, `intake/`, `fakes.py` |
| `app/db/` | SQLite engine (WAL, FKs), tables, repos |

## Errors

Every expected failure becomes JSON in the form `{"error": {"code", "message"}}`:

| Code | HTTP | When |
|---|---|---|
| `missing_api_key` | 503 | `NEBIUS_API_KEY` or `TAVILY_API_KEY` is unset while `MOCK_MODE=false` |
| `upstream_error` | 502 | Nebius or Tavily failed: bad key, unknown model ID, rate limit, timeout, invalid JSON |
| `bad_input` | 400 | Wrong file type, too large, encrypted, a scan without OCR, or invalid input |
| `unauthorized` | 401 | Missing or expired session token |
| `not_found` | 404 | Unknown resource or another user's |

## Docker

```bash
docker build -t postulo-backend .
docker run --rm -p 8000:8000 --env-file ../.env postulo-backend
```

The image uses `python:3.12-slim` with uv and installs dependencies from the lockfile (`--frozen --no-dev`). It runs as non-root user `appuser` and has a `/health` healthcheck.
