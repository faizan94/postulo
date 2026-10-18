# Postulo backend

FastAPI service that runs the agent pipeline: CV → profile → search → verify → score.
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

## CLI

```bash
uv run python -m app cv  path/to/cv.pdf                      # print the extracted profile
uv run python -m app run path/to/cv.pdf --location Germany   # full pipeline → output/{date}/
uv run python -m app run path/to/cv.pdf --mock               # force mock data
uv run python scripts/list_models.py                         # Nemotron IDs on Token Factory
```

## Layout

| Path | What it does |
|---|---|
| `app/main.py` | App factory, CORS, and the `PostuloError` → JSON handler |
| `app/config.py` | `Settings` (pydantic-settings) and the cached `get_settings()` dependency |
| `app/api/routes/` | `GET /health`, `POST /api/cv`, `POST /api/jobs/search` |
| `app/agents/orchestrator.py` | `extract_profile()` and `run_job_search()`, including the widening top-up rounds |
| `app/agents/search_agent.py` | Builds queries, calls Tavily over `ATS_DOMAINS`, parses company and title from ATS URLs |
| `app/agents/verify_agent.py` | HTTP liveness and closed-page markers, Tavily company lookup, and recency (45 days) |
| `app/agents/score_agent.py` | Tavily `/extract` plus a Nemotron JSON call per posting (reasoning on) → `Posting` |
| `app/agents/prompts/` | System prompts (Scope → Hard rules → Return value) |
| `app/services/llm.py` | `LLMClient`: OpenAI SDK pointed at Nebius, the `reasoning="off"\|"on"\|"medium"` toggle, `chat_json()` with tolerant parsing |
| `app/services/tavily_client.py` | `TavilyService`: `search`, `search_jobs`, `extract` |
| `app/services/cv_parser.py` | pypdf text extraction, with size, type and encryption checks |

## Errors

Every expected failure becomes JSON in the form `{"error": {"code", "message"}}`:

| Code | HTTP | When |
|---|---|---|
| `missing_api_key` | 503 | `NEBIUS_API_KEY` or `TAVILY_API_KEY` is unset while `MOCK_MODE=false` |
| `upstream_error` | 502 | Nebius or Tavily failed: bad key, unknown model ID, rate limit, timeout, invalid JSON |
| `bad_input` | 400 | Not a PDF, the file is too large, it's encrypted, or it has no text layer |

## Docker

```bash
docker build -t postulo-backend .
docker run --rm -p 8000:8000 --env-file ../.env postulo-backend
```

The image uses `python:3.12-slim` with uv and installs dependencies from the lockfile (`--frozen --no-dev`). It runs as non-root user `appuser` and has a `/health` healthcheck.
