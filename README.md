# Postulo

> **Open, recent jobs that fit your CV, with an honest match score and what to learn next.**

Sign in with a name, upload your CV (PDF, Word or pasted text) and Postulo runs your first search automatically:

1. **Plan**: Nemotron 3.5 Super VL writes search queries from your job titles, places and skills.
2. **Discover**: Tavily finds company job boards (Greenhouse, Lever, Ashby).
3. **Quiet checks**: the boards' public APIs say which jobs are still open, how fresh they are and where they are. Closed, stale or wrong-place jobs are dropped silently (judges can see them in "How it works").
4. **Match**: Nemotron 3.5 Lightning extracts each job's requirements with verbatim quotes; code checks every quote and computes the **match score** with a fixed formula. A **company score** comes from public hiring signals.
5. **Learn next**: a skill chart across your matches and Gap ROI, the skill that would lift the most jobs.

If Nemotron is unavailable, grounded rule-based extraction takes over, so the app always works. See [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md) for the plan and decision log.

## Architecture

```
Next.js 16 (shadcn/ui, Recharts, TanStack Query)
   |  REST + live stream (text/event-stream read via fetch)
   v
FastAPI -- SQLite (users, CV versions, searches, posting + company caches)
   |
   +- CV intake: pypdf / python-docx / text -> cleaning (no email, phone, birth date) -> review
   +- Profile: Nemotron Super VL (quotes verified) + glossary rules
   +- Search run (background task, streamed):
        plan (Nemotron) -> Tavily -> board APIs -> quiet checks -> widen in country (<=3 rounds)
        -> requirements (Nemotron Lightning, cached) -> match + score (code) -> company score
        -> rank -> skill summary + Gap ROI
```

With `MOCK_MODE=true`, fake Tavily and job boards run under the real pipeline, so the UI works without keys.

## Tech stack

| Layer | Tech |
|---|---|
| Models | **NVIDIA Nemotron** on **Nebius Token Factory**: `nvidia/Nemotron-3.5-Super-VL` (planning, CV), `nvidia/Nemotron-3_5-Lightning` (requirements) |
| Web data | **Tavily** `/search` (raw API, `include_published_date`, usage counted, cached) + Greenhouse, Lever, Ashby public job-board APIs |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async, SQLite), pypdf, python-docx, httpx, **uv** |
| Frontend | Next.js 16 (App Router, Cache Components), React 19, Tailwind CSS 4, shadcn/ui (Radix), Recharts, lucide-react, TanStack Query, sonner |
| Ops | Docker (non-root, healthchecks, data volume), docker compose |

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

### Deploy on Nebius AI Cloud

Preferred: **Serverless AI** endpoint with nginx (one HTTPS URL for UI + API). Token Factory still serves Nemotron. See [deploy/nebius/README.md](deploy/nebius/README.md).

```bash
./deploy/nebius/build-push.sh       # or: make nebius-build
./deploy/nebius/deploy-endpoint.sh  # or: make nebius-endpoint
```

### Common tasks

| Task | npm (any OS) | make | PowerShell |
|---|---|---|---|
| Tests | `npm test` | `make test` | `cd backend; uv run pytest` |
| Lint | `npm run lint` | `make lint` | `scripts\check.ps1` (runs everything) |
| Frontend build | `npm run build` | `make build` | `cd frontend; npm run build` |
| Docker | `npm run docker:up` | `make docker-up` | `docker compose up --build` |

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
| `NEMOTRON_VISION_MODEL` | `nvidia/Nemotron-3.5-Super-VL` | Vision model for OCR (stretch) |
| `OCR_ENABLED` | `false` | Accept image/scan CVs (stretch) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/postulo.db` | SQLite file; folder is created on startup |
| `MAX_TAVILY_CREDITS_PER_RUN` | `20` | Tavily credit budget per search |
| `MAX_LLM_CALLS_PER_RUN` | `15` | Nemotron call budget per search (rules take over after) |
| `RECENT_DAYS` | `45` | Older postings are dropped quietly |
| `POSTING_RECHECK_HOURS` / `COMPANY_CACHE_DAYS` | `24` / `30` | Cache lifetimes |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL as seen from the browser. It is inlined at frontend build time |

If keys are missing and `MOCK_MODE=false`, the API returns HTTP 503 with `{"error": {"code": "missing_api_key", ...}}`. It does not crash.

## API

All `/api/*` routes except login and places need `Authorization: Bearer <token>`. Full list and shapes: [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md) §5.4 and http://localhost:8000/docs.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Status, mock mode, keys configured, model IDs |
| `POST` | `/api/auth/login` · `/api/auth/logout` | Name-only login, token |
| `GET` / `PUT` / `DELETE` | `/api/me`, `/api/me/settings` | Current user, search defaults, delete my data |
| `GET` | `/api/places?q=` | Fixed places list (city, country, Remote) |
| `POST` / `PUT` / `GET` / `DELETE` | `/api/cv`, `/api/cv/{id}` | Upload or paste, review and confirm, list, delete CV versions |
| `POST` / `GET` | `/api/searches`, `/api/searches/{id}` | Start a search, history, detail (safe to reload) |
| `GET` | `/api/searches/{id}/events` | Live stream (`text/event-stream`, snapshot first) |
| `POST` | `/api/searches/{id}/rerun` | Same inputs, fresh checks |
| `GET` | `/api/postings/{id}?search_id=` | Job detail: full post, apply link, match breakdown, company score |
| `GET` | `/api/how/{search_id}` | Judge view: agent trace, quiet drops, credits used |

## Project structure

```
postulo/
├── backend/app/
│   ├── main.py, config.py, errors.py, events.py (stream bus), runner.py (background searches)
│   ├── api/                 deps.py (auth, DB), presenters.py (rows -> API), routes/
│   ├── db/                  engine.py (SQLite, WAL), tables.py, repos/
│   ├── schemas/             API shapes (frontend/src/lib/types.ts mirrors them)
│   ├── agents/              orchestrator, planner, discover (boards + quiet checks),
│   │                        requirements, profile, llm_gate, prompts/
│   ├── domain/              pure logic: evidence, glossary, places, titles, years, rules, matching
│   ├── scoring/             match_score, company_score, rank, summary (skills + Gap ROI)
│   └── services/            llm.py, tavily_client.py, ats.py (Greenhouse/Lever/Ashby),
│                            html_text.py, intake/ (PDF, docx, text, cleaning), fakes.py (mock)
├── frontend/src/
│   ├── app/                 login, (app)/onboarding, search/[id], search/[id]/job/[postingId],
│   │                        new-search, history, settings, how/[id]
│   ├── components/ui/       shadcn/ui (Radix)
│   ├── features/            auth, cv, search, results, job, shell
│   └── lib/                 api/, sse.ts, types.ts, status.ts, format.ts
└── docs/PHASE1_PLAN.md      the plan and decision log
```

## Where to extend

- **Scanned CVs / photos (stretch)**: `NEMOTRON_VISION_MODEL` + `OCR_ENABLED`; add `services/intake/ocr.py`.
- **More job boards**: add a parser in `backend/app/services/ats.py` and its domain to `ATS_DOMAINS`.
- **Company news signal (stretch)**: Tavily `topic=news` in `agents/` + `scoring/company_score.py`.
- **Skills**: aliases and related groups live in `backend/app/domain/data/glossary.json`.
- **Prompts**: `backend/app/agents/prompts/`.

## Docs

- [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md): Phase 1 plan, decisions, scoring formulas.
- [docs/reference-ai-agent-orchestrator.md](docs/reference-ai-agent-orchestrator.md): what we took from `mathcrypto/ai-agent-orchestrator`, and why.

## Team

| Name | Role |
|---|---|
| _TBD_ | Backend |
| _TBD_ | Frontend |
| _TBD_ | Pitch |

## Hackathon

Built in one day at The Delta Campus (hosted by Nebius; sponsors NVIDIA, Nebius and Tavily).

- **Track:** Agentic Deep Research with Token Factory and Tavily (main), Nemotron Agentic AI (subtrack)
- **Demo:** _link_

## License

[MIT](LICENSE)
