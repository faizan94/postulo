# CLAUDE.md

Guidance for Claude Code (and other AI coding agents) working in this repo.

## Hard rules (read first)

- **Never commit.** Do not run `git commit`, `git push`, `git merge`, `git rebase`, or open PRs. Commits are made by a person only. Leave changes in the working tree and say what changed.
- **No worktrees.** Do not create or use git worktrees (`git worktree`, `EnterWorktree`, `isolation: "worktree"`) or switch branches. Work directly in this checkout; we are on a short hackathon clock.
- **No real secrets in files.** API keys go only in the local `.env` (gitignored). `.env.example` holds placeholders only.

## What this is

Postulo: an AI job-application agent. CV PDF + preferences go in; 5-10 verified, scored job postings come out, each skill tagged have / related / missing_nice / missing_must (emerald / sky / amber / rose), with a match score and a company score. MVP only, no auto-applying. See [README.md](README.md) for the full picture.

Stack: NVIDIA Nemotron on Nebius Token Factory (OpenAI-compatible, via the `openai` SDK), Tavily search, FastAPI backend (uv), Next.js 16 frontend (npm).

## Commands

```bash
# backend (from backend/)
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                      # must pass without API keys
uv run ruff check . && uv run ruff format --check .
uv run mypy app

# frontend (from frontend/)
npm run dev
npm run lint && npm run typecheck && npm run build

# everything
docker compose up --build          # needs .env (copy from .env.example)
```

Before saying a change is done: backend changes -> pytest + ruff; frontend changes -> lint + build.

## Layout

Plan and decision log: [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md) and [docs/PHASE2_PLAN.md](docs/PHASE2_PLAN.md) (Phase 2 wins where they differ). If code and plan disagree, fix one of them.

- `backend/app/agents/orchestrator.py`: the search state machine (plan -> discover -> quiet checks -> widen -> requirements -> match -> company score -> rank). Results are saved and streamed as they come.
- `backend/app/agents/`: `planner.py`, `discover.py` (Tavily finds boards; board APIs give open jobs), `requirements.py`, `profile.py`, `llm_gate.py` (every LLM call goes through it; rules take over on failure). Prompts live in `agents/prompts/`, never inline.
- `backend/app/domain/`: pure logic (evidence quote checks, glossary, places, titles, years, rule-based extraction, matching). `backend/app/scoring/`: fixed formulas. Both are unit-tested without I/O.
- `backend/app/services/`: `llm.py` (Nebius, `reasoning="off"|"on"|"medium"`), `tavily_client.py` (raw API, cached), `ats.py` (Greenhouse/Lever/Ashby), `intake/` (PDF, docx, text, cleaning), `fakes.py` (mock mode).
- `backend/app/schemas/`: API shapes. **`frontend/src/lib/types.ts` mirrors them; change both together.**
- `backend/app/db/`: SQLite via async SQLAlchemy; tables created on startup.
- `frontend/src/app/`: routes; `frontend/src/features/`: screens' building blocks; `frontend/src/components/ui/`: shadcn/ui.

## Conventions

- Expected failures raise `PostuloError` subclasses (`app/errors.py`) and become `{"error": {code, message}}` JSON. Missing keys -> 503, never a crash.
- Every new endpoint or agent behaviour needs a mock-mode path so the frontend works without keys, plus a test that runs without network. Mock mode = fake Tavily and boards (`services/fakes.py`) over a real SQLite DB.
- Settings come only from `app/config.py` (pydantic-settings); add new env vars there **and** to `.env.example` and the README env table.
- Python: ruff (line length 100), type hints, async I/O. TypeScript: strict, Tailwind classes, no new UI libraries without asking.
- Next.js 16 has breaking changes from older versions: read `frontend/AGENTS.md` and the docs in `frontend/node_modules/next/dist/docs/` before using unfamiliar APIs.
- `NEXT_PUBLIC_API_URL` is inlined at build time and is the browser-facing URL (`http://localhost:8000`), not the compose service name.
