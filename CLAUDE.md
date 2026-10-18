# CLAUDE.md

Guidance for Claude Code (and other AI coding agents) working in this repo.

## Hard rules (read first)

- **Never commit.** Do not run `git commit`, `git push`, `git merge`, `git rebase`, or open PRs. Commits are made by a person only. Leave changes in the working tree and say what changed.
- **No worktrees.** Do not create or use git worktrees (`git worktree`, `EnterWorktree`, `isolation: "worktree"`) or switch branches. Work directly in this checkout; we are on a short hackathon clock.
- **No real secrets in files.** API keys go only in the local `.env` (gitignored). `.env.example` holds placeholders only.

## What this is

Postulo: an AI job-application agent. CV PDF + preferences go in; 5-10 verified, scored job postings come out, each skill tagged gold (match) / orange (gap worth covering) / red (important gap). MVP only, no auto-applying. See [README.md](README.md) for the full picture.

Stack: NVIDIA Nemotron on Nebius Token Factory (OpenAI-compatible, via the `openai` SDK), Tavily search, FastAPI backend (uv), Next.js 16 frontend (npm).

## Commands

```bash
# backend (from backend/)
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                      # must pass without API keys
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run python -m app run cv.pdf --location Berlin --mock   # pipeline CLI -> output/{date}/

# frontend (from frontend/)
npm run dev
npm run lint && npm run typecheck && npm run build

# everything
docker compose up --build          # needs .env (copy from .env.example)
```

Before saying a change is done: backend changes -> pytest + ruff; frontend changes -> lint + build.

## Layout

- `backend/app/agents/orchestrator.py`: profile extraction + search -> verify -> score loop (widens location if fewer than 5 verified).
- `backend/app/agents/{search,verify,score}_agent.py`: the sub-agents. Prompts live in `backend/app/agents/prompts/`, never inline.
- `backend/app/services/`: `llm.py` (Nebius client, `reasoning="off"|"on"|"medium"` via `chat_template_kwargs`), `tavily_client.py`, `cv_parser.py`.
- `backend/app/models/schemas.py`: API shapes. **`frontend/src/lib/types.ts` mirrors it; change both together.**
- `backend/app/agents/mock_data.py`: data returned when `MOCK_MODE=true`.
- `frontend/src/components/PostuloFlow.tsx`: the upload -> preferences -> results flow.

## Conventions

- Expected failures raise `PostuloError` subclasses (`app/errors.py`) and become `{"error": {code, message}}` JSON. Missing keys -> 503, never a crash.
- Every new endpoint or agent behaviour needs a mock-mode path so the frontend works without keys, plus a test that runs without network.
- Settings come only from `app/config.py` (pydantic-settings); add new env vars there **and** to `.env.example` and the README env table.
- Python: ruff (line length 100), type hints, async I/O. TypeScript: strict, Tailwind classes, no new UI libraries without asking.
- Next.js 16 has breaking changes from older versions: read `frontend/AGENTS.md` and the docs in `frontend/node_modules/next/dist/docs/` before using unfamiliar APIs.
- `NEXT_PUBLIC_API_URL` is inlined at build time and is the browser-facing URL (`http://localhost:8000`), not the compose service name.
