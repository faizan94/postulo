# Reference: `mathcrypto/ai-agent-orchestrator`

> Source: https://github.com/mathcrypto/ai-agent-orchestrator (one commit, `a550238` "agent orchestrator", reviewed 18 Oct 2026).
> This note records what that repo is, which of its ideas Postulo took, and which it left out and why.

## 1. What the repo is

It's a **daily AI content pipeline** (not job search) built on **LangChain Deep Agents**. A lead agent delegates to three sub-agents through Deep Agents' `task` tool and writes Markdown files to `output/{date}/`.

```
Lead orchestrator (OpenAI AGENT_MODEL, sub-agents inherit it)
  ├─ task → daily-researcher (+ Tavily, topic=news, time_range=week)  ⎫ parallel
  ├─ task → events-scout     (+ Tavily, topic=general, time_range=week) ⎭
  └─ task → blog-writer      (no tools)
       → news-brief.md, paris-events.md, blog-ideas.md, drafts/draft-1.md, digest.md
```

| Part | File | What it does |
|---|---|---|
| Lead agent | `src/orchestrator/agent.py` | `create_deep_agent(...)` with three sub-agent specs (`name`, `description`, `system_prompt`, `tools`) and a `FilesystemBackend` |
| Model | `src/orchestrator/models.py` | One cached `ChatOpenAI` (`AGENT_MODEL`, default `gpt-4o-mini`, temperature 0.2), shared by every agent |
| Search tool | `src/orchestrator/tools/search.py` | Factory that builds `langchain_tavily.TavilySearch` with `max_results`, `topic` and `time_range`, and fails fast without `TAVILY_API_KEY` |
| Prompts | `src/orchestrator/prompts/*.py` | One module per agent, each with the same sections: **Scope → Tools → Hard rules (anti-hallucination) → Return value** (a Markdown template) |
| CLI | `src/orchestrator/cli.py` | `python -m orchestrator run --date YYYY-MM-DD`. It wipes `output/{date}/`, invokes the lead, **checks which required files are missing, and re-prompts for only those steps** (up to 4 rounds, `recursion_limit=150`) |
| Config | `.env.example`, `pyproject.toml` | `OPENAI_API_KEY`, `AGENT_MODEL`, `TAVILY_API_KEY`. Deps: `deepagents`, `langchain-openai`, `langchain-tavily`, `python-dotenv`. Hatchling build, `orchestrator` console script |

## 2. What Postulo absorbed

| Pattern from the repo | Where it lives in Postulo | Postulo's version |
|---|---|---|
| **Prompts as a package, one module per agent, fixed section layout** | `backend/app/agents/prompts/` (`profile.py`, `score.py`) | Each prompt follows Scope → Hard rules → Return value. Agents import prompts and never inline them, so whoever tunes prompts edits one place |
| **Anti-hallucination hard rules** ("use only facts from the results, never invent URLs/dates") | Same prompt files | Adapted for CVs and postings: only skills the CV supports, only requirements in the posting text, quote verbatim or don't claim a quote, null instead of guessing |
| **Completeness loop**: check the output and re-run only the missing part | `backend/app/agents/orchestrator.py` (`MIN_POSTINGS`, `WIDER`, `MAX_ROUNDS`) | If fewer than 5 postings survive verification, the orchestrator runs a top-up round with a wider location (Berlin → Germany → World) and skips URLs it has already seen. This answers the team's "results may be weak" concern (idea.md §6) |
| **Parallel phase-1 sub-agents** | `search_agent.py`, `verify_agent.py`, `score_agent.py` | `asyncio.gather` across queries, company checks, liveness checks and scoring, with semaphores to stay inside rate limits |
| **Tool factory with explicit search params and a fail-fast key check** | `backend/app/services/tavily_client.py` | `search_depth`, `time_range` and `include_domains` (ATS sites) are always set explicitly. A missing key raises `MissingAPIKeyError`, which becomes a clean HTTP 503 rather than a `RuntimeError` |
| **CLI with a dated output folder** | `backend/app/cli.py` (`uv run python -m app run cv.pdf ...`) | Writes `output/{date}/profile.json`, `results.json` and `briefing.md` (Postulo's equivalent of `digest.md`). Use it to tune prompts without the UI and to cache demo runs as a backup |
| **`.gitignore` entries** (`output/`, caches) | Root `.gitignore` | Same entries, plus Node and Next.js entries |

## 3. What Postulo left out, and why

| Not taken | Reason |
|---|---|
| **LangChain Deep Agents** (`create_deep_agent`, the `task` tool, `FilesystemBackend`) | Postulo's graph is fixed (search → verify → score), as idea.md §5 decided ("plan the graph first"). A plain async pipeline is easier to debug in a 5-hour build, has deterministic cost, and makes the "own research loop" obvious to Deep Research track judges (TECH.md §3) |
| **OpenAI models** (`ChatOpenAI`, `gpt-4o-mini`) | The sponsor stack is Nemotron on Nebius Token Factory. Postulo uses the `openai` SDK only as an OpenAI-compatible client pointed at `NEBIUS_BASE_URL` |
| **A single shared model at temperature 0.2** | Postulo splits `NEMOTRON_MODEL` (reasoning on, for scoring) from `NEMOTRON_FAST_MODEL`, and uses the Nemotron-recommended sampling (`temperature=1.0`, `top_p=0.95`) with a `chat_template_kwargs` reasoning toggle |
| **`python-dotenv` plus module-level `load_dotenv`** | Replaced by `pydantic-settings`, which validates types and loads defaults and `.env` in one place (`app/config.py`) |
| **Markdown as the agent-to-agent format** | Postulo passes typed Pydantic models between agents and returns JSON to the frontend. Markdown appears only in the CLI's `briefing.md` |
| **Wiping the output folder on each run** | The Postulo CLI overwrites its three files but keeps other runs, so cached demo results survive |

## 4. If the team wants Deep Agents later

The repo's structure maps onto Postulo almost one to one. To try it:

1. `uv add deepagents langchain-openai langchain-tavily`
2. Build the model against Nebius instead of OpenAI:
   ```python
   from langchain_openai import ChatOpenAI
   model = ChatOpenAI(
       model=settings.nemotron_model,
       base_url=settings.nebius_base_url,
       api_key=settings.nebius_api_key,
       temperature=1.0,
       extra_body={"chat_template_kwargs": {"enable_thinking": True}},
   )
   ```
3. Register `search`, `verify` and `score` as sub-agents, using the prompts from `app/agents/prompts/` as their `system_prompt`. Expose the existing Python functions (`search_postings`, `check_live`, `check_company`) as tools.
4. Keep `run_job_search()` as the API entry point so the frontend and tests don't change.

Do this only after the fixed pipeline works end to end. It costs more tokens and is less predictable, which is risky on demo day.
