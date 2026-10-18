# Postulo

> **LinkedIn shows you jobs. Postulo tells you which ones are real, why you fit, and what's missing.**

Postulo is an AI job-application agent. You upload a CV (PDF) and say what you're looking for. An **orchestrator agent** splits the work across specialised sub-agents:

1. **Search** looks for recent postings on company career pages and applicant-tracking systems (Greenhouse, Lever, Ashby, Personio, Workday, join.com and others), where many roles appear first or only.
2. **Verify** checks that the company exists, the posting is still live, and it is recent. It flags **ghost jobs**: dead links, closed roles and stale reposts.
3. **Score** reads each posting and tags every required skill:
   - 🟡 **gold**: a match, you have it
   - 🟠 **orange**: a gap worth covering
   - 🔴 **red**: an important gap

You get a briefing of **5-10 verified postings**, each with a star score, the skill breakdown, and a "why" that quotes the posting.

MVP scope: no auto-applying. Cover letters, contacts and CV tweaks come later.

## Architecture

```
                         ┌───────────────────────────── backend (FastAPI) ─────────────────────────────┐
 ┌──────────────┐  PDF   │  POST /api/cv          ┌──────────────┐                                     │
 │  Next.js UI  │ ─────► │  cv_parser (pypdf) ──► │ Orchestrator │──► Profile (skills, years, roles)   │
 │  :3000       │        │                        │  (Nemotron)  │                                     │
 │              │  JSON  │  POST /api/jobs/search └──────┬───────┘                                     │
 │ upload →     │ ─────► │            ┌──────────────────┼──────────────────┐   top-up round if        │
 │ preferences →│        │            ▼                  ▼                  ▼   fewer than 5 verified  │
 │ results      │ ◄───── │   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ (Berlin→DE→World)│
 └──────────────┘ scored │   │ 1. Search      │→│ 2. Verify      │→│ 3. Score       │                  │
                 postings│   │ Tavily /search │ │ HTTP liveness, │ │ Tavily /extract│                  │
                 + trace │   │ ATS domains,   │ │ Tavily company │ │ + Nemotron     │                  │
                         │   │ last month     │ │ lookup, dates  │ │ (reasoning on) │                  │
                         │   └────────────────┘ └────────────────┘ └────────────────┘                  │
                         └──────────────────────────────────────────────────────────────────────────────┘
                              Nemotron via Nebius Token Factory (OpenAI-compatible)  ·  Tavily web search
```

With `MOCK_MODE=true`, the backend returns realistic fake data, so the UI works without any API keys.

## Tech stack

| Layer | Tech |
|---|---|
| Models | **NVIDIA Nemotron** (`nvidia/Nemotron-3.5-Super-VL` main, `nvidia/Nemotron-3_5-Lightning` fast, both live on Token Factory), with a reasoning on/off toggle via `chat_template_kwargs` |
| Inference | **Nebius Token Factory**, an OpenAI-compatible API, called through the `openai` Python SDK |
| Web data | **Tavily** `/search` (ATS domains, `time_range=month`) and `/extract` (full posting text) |
| Backend | Python 3.12, FastAPI, Pydantic v2, pydantic-settings, pypdf, httpx, managed with **uv** |
| Frontend | Next.js 16 (App Router, TypeScript, Tailwind CSS 4, ESLint), npm |
| Ops | Docker (multi-stage, non-root, healthchecks), docker compose |

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.10+. It installs Python 3.12 for you.
  Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Node.js 22+ and npm 10+
- Optional: Docker Desktop
- Optional (for real runs): a Nebius Token Factory API key and a Tavily API key

## Quick start

### Option A: Docker

```bash
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
docker compose up --build
```

Then open the UI at http://localhost:3000 and the API docs at http://localhost:8000/docs.

### Option B: local dev (Windows-friendly)

```bash
npm run setup                   # creates .env, runs uv sync + npm install
```

Then, in two terminals:

```bash
npm run dev:backend             # http://localhost:8000
npm run dev:frontend            # http://localhost:3000
```

On Windows you can also run `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`, which opens both servers in two windows. With `make` (macOS, Linux, Git Bash), run `make setup` and then `make dev`.

### Going live (real searches)

Edit `.env`: set `MOCK_MODE=false` and fill in `NEBIUS_API_KEY` and `TAVILY_API_KEY`. Check which Nemotron IDs your key can use:

```bash
cd backend && uv run python scripts/list_models.py
```

### Common tasks

| Task | npm (any OS) | make | PowerShell |
|---|---|---|---|
| Tests | `npm test` | `make test` | `cd backend; uv run pytest` |
| Lint | `npm run lint` | `make lint` | `scripts\check.ps1` (runs everything) |
| Frontend build | `npm run build` | `make build` | `cd frontend; npm run build` |
| Docker | `npm run docker:up` | `make docker-up` | `docker compose up --build` |

### CLI (no UI)

Run the whole pipeline from the terminal. It writes `output/{date}/profile.json`, `results.json` and `briefing.md`, which makes it useful for tuning prompts and caching demo runs:

```bash
cd backend
uv run python -m app run path/to/cv.pdf --location Berlin --prompt "data roles" --mock
```

## Environment variables

All variables live in `.env` at the repo root (see [.env.example](.env.example)).

| Variable | Default | Purpose |
|---|---|---|
| `MOCK_MODE` | `true` in `.env.example` (the code defaults to `false`) | Return fake data, no API calls |
| `NEBIUS_API_KEY` | — | Token Factory API key |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1/` | OpenAI-compatible base URL |
| `NEMOTRON_MODEL` | `nvidia/Nemotron-3.5-Super-VL` | Main model (planning, CV profile) |
| `NEMOTRON_FAST_MODEL` | `nvidia/Nemotron-3_5-Lightning` | Cheap model for sub-agent steps |
| `TAVILY_API_KEY` | — | Tavily search key (`tvly-...`) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `MAX_POSTINGS` | `10` | Postings returned per search (1-20) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL as seen from the browser. It is inlined at frontend build time |

If keys are missing and `MOCK_MODE=false`, the API returns HTTP 503 with `{"error": {"code": "missing_api_key", ...}}`. It does not crash.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/health` | — | Status, mock mode, which keys are configured, the model ID |
| `POST` | `/api/cv` | multipart: `file` (PDF, ≤10 MB), optional `prompt` | `{profile, cv_text_chars, mock}` |
| `POST` | `/api/jobs/search` | `{profile, preferences: {location: "Berlin"\|"Germany"\|"World", prompt}}` | `{profile, postings[], rejected[], trace[], mock}` |

Interactive docs are at http://localhost:8000/docs. The response shape follows idea.md §9:

```json
{
  "title": "Data Engineer", "company": "...", "url": "...", "posted": "2026-10-10",
  "verified": {"company_exists": true, "posting_live": true, "recent": true},
  "score": 4.5,
  "skills": [{"name": "Python", "status": "gold"}, {"name": "Airflow", "status": "orange"}],
  "why": "Matches 7/9 required skills; quoted requirement: '...'"
}
```

## Project structure

```
postulo/
├── backend/                     FastAPI app (uv)
│   ├── app/
│   │   ├── main.py              app factory, CORS, error handler
│   │   ├── config.py            pydantic-settings (.env)
│   │   ├── errors.py            MissingAPIKeyError / UpstreamError / BadInputError → JSON
│   │   ├── cli.py               `python -m app run cv.pdf`
│   │   ├── api/routes/          health.py, cv.py, jobs.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py  profile extraction + search→verify→score loop
│   │   │   ├── search_agent.py  Tavily queries over ATS domains
│   │   │   ├── verify_agent.py  liveness, company, recency → ghost-job filter
│   │   │   ├── score_agent.py   gold/orange/red skills + star score
│   │   │   ├── prompts/         one system prompt per agent
│   │   │   └── mock_data.py     MOCK_MODE fixtures
│   │   ├── services/            llm.py (Nebius), tavily_client.py, cv_parser.py
│   │   └── models/schemas.py    API data shapes
│   ├── scripts/list_models.py   list Nemotron IDs on Token Factory
│   ├── tests/                   pytest, no API keys needed
│   └── Dockerfile
├── frontend/                    Next.js (npm)
│   ├── src/app/                 layout + page
│   ├── src/components/          PostuloFlow, PostingCard, SkillChip, StarScore, ...
│   ├── src/lib/                 api.ts (fetch client), types.ts (mirrors schemas.py)
│   └── Dockerfile
├── docs/                        design notes and references
├── scripts/                     dev.ps1, check.ps1 (Windows)
├── docker-compose.yml
├── .env.example
├── Makefile · package.json      task runners (make / npm)
└── LICENSE (MIT)
```

## Where to extend

- **Better CV reading**: send the PDF pages as images to Nemotron 3.5 Super VL. See the note in `backend/app/services/cv_parser.py`.
- **More job sources**: add domains to `ATS_DOMAINS` in `backend/app/services/tavily_client.py`.
- **Stricter ghost-job detection**: add markers and rules in `backend/app/agents/verify_agent.py`.
- **Advisor agent** (cover letter, contacts, CV tweaks): add `app/agents/advisor_agent.py` and a prompt in `app/agents/prompts/`, then call it from the orchestrator.
- **Prompt tuning**: everything is in `backend/app/agents/prompts/`. Iterate with the CLI.

## Docs

- [docs/reference-ai-agent-orchestrator.md](docs/reference-ai-agent-orchestrator.md): what we took from `mathcrypto/ai-agent-orchestrator`, and why.

## Team

| Name | Role |
|---|---|
| _TBD_ | Backend |
| _TBD_ | Frontend |
| _TBD_ | Pitch |

## Hackathon

Built in one day at The Delta Campus (hosted by Nebius; sponsors NVIDIA, Nebius and Tavily).

- **Track:** _TBD (Agentic Deep Research or Nemotron Agentic AI)_
- **Demo:** _link_

## License

[MIT](LICENSE)
