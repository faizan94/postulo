# Postulo: Phase 1 Plan

> Status: plan only, no code changed yet. Version 2 (18 Oct 2026), revised after an independent review (see §13).
> Sources: `../../idea.md`, `../../TRACKS.md`, `../../TECH.md`, the current code in `backend/` and `frontend/`, and the team decisions in §2.
> Rules from `../CLAUDE.md` still apply: never commit from an agent, every endpoint works in mock mode and has a network-free test, `schemas` and `frontend/src/lib/types.ts` change together, and settings live only in `app/config.py`.

---

## 1. Goal and scope

**One line:** a job seeker signs in with a name and uploads a CV. Postulo runs a first search automatically and shows the open, recent jobs that fit them best. Each job gets a **match score** (how well you fit) and a **company score** (how healthy the employer looks). A skill chart shows what to learn next.

**Tracks (assumed, confirm):** main track is Agentic Deep Research (Token Factory + Tavily); subtrack is Nemotron Agentic AI.

**Time reality:** idea.md plans about 5 hours of build time, and the event has hard stops (opt-in 18:30, demos 20:00). So Phase 1 has a **Core** that must ship and a **Stretch** list we only start when Core works end to end.

| Core (must ship) | Stretch (only if Core is done) | Out (Phase 2+) |
|---|---|---|
| Name login, remembered session | Image and scanned-PDF OCR | Passwords, OAuth |
| CV input: text PDF, `.docx`, pasted text; review screen | Company news signal | Old `.doc`, LinkedIn import |
| Saved CV versions; reuse or upload new | LLM "reflect" step (Core uses rule-based widening) | Cover letters, auto-apply |
| Automatic first search after onboarding | Saved jobs + "closed since you saved it" | Alerts, scheduled searches |
| New search, history, re-run | Usage stats in the judge view | Salary data, city stats |
| LLM query planning (1 call) + rule-based widening | | Dark mode, migrations |
| Board APIs (Greenhouse, Lever, Ashby) + quiet checks | | |
| Match score, company score (hiring + basics), skill chart, Gap ROI | | |
| Job detail: full post text and apply link | | |
| Live progress stream | | |
| "How it works" judge view (agent trace) | | |
| Settings: titles, places, delete data, log out | | |

---

## 2. Decisions log (single source of truth)

If a later doc or code disagrees with this table, this table wins until the team changes it.

| # | Decision | Replaces / changes |
|---|---|---|
| D1 | CV input is a PDF, `.docx`, image or pasted text. Read the PDF text layer first with pypdf; a scan or image goes to Nemotron vision OCR, text only (Stretch). The user reviews and confirms the text before it is used. | Replaces "PDF only" (`cv_parser.py:31`) |
| D2 | "CV" is the one term in the UI, code and prompts. "Resume" and "Lebenslauf" are accepted aliases. A glossary maps skill aliases (`JS` → JavaScript, `K8s` → Kubernetes; `CV` inside a skills list → Computer Vision). | New |
| D3 | Photos and protected attributes never affect anything. The profile has no fields for photo, age, gender, nationality, marital status, health or the person's name. Scoring never sees them. | Removes `name` from `Profile` |
| D4 | Grounding: **LLM proposes, code verifies.** The LLM reads only text we fetched. Every extracted item has a verbatim quote that code checks. Numbers are computed by code. See §6. | New |
| D5 | Quiet checks are hidden from job seekers. Failed postings are dropped silently and logged in the DB. No rejected list or proofs in the user UI. | Removes the "rejected wall" from the UI |
| D6 | Match score is 0–100% from a fixed formula in code (§7.1). The same CV version and posting always give the same score; LLM verdicts are cached so re-runs can't drift. | Replaces LLM-invented 0–5 stars |
| D7 | Company score is 0–100 from **public signals only**: hiring activity and basics (Core), plus news from the last 12 months (Stretch). It shows "Not enough data" instead of guessing. No Glassdoor or kununu scores; we link out only. **(Needs team OK.)** | New |
| D8 | Skill statuses are `have`, `related`, `missing_nice`, `missing_must`, colored emerald, sky, amber and rose, each with an icon. | Replaces gold/orange/red (idea.md §4) |
| D9 | Location is structured (city, country or Remote; several allowed), picked from a fixed list served by `GET /api/places`. Code filters on the job's own location. Widening stays inside the same country and the UI says so. | Replaces fixed Berlin/Germany/World and silent widening to World |
| D10 | Search settings are only places and 1–3 job titles. The free-text "wishes" box is removed (it leaked personal details into Tavily queries and prompts). | Removes `Preferences.prompt` |
| D11 | Onboarding runs the first search automatically with the titles and place suggested from the CV, and saves them as the user's defaults. If the CV has no place, it asks one question first. | New |
| D12 | Storage is SQLite. We store users, sessions, CV versions (cleaned text + profile), searches, results and caches, not the original file or image. Contact details and personal lines are stripped on a best-effort basis. There is a "Delete my data" button. | Replaces "CV is not stored" (UI copy must change) |
| D13 | Login is a name only; the server returns a random token that the browser keeps until logout. Names are trimmed and case-insensitive. **Anyone who knows a name can open that account**, and the UI says so. | New |
| D14 | Job seekers see progress in plain words. Judges get a separate **"How it works" view** with the agent trace (plans, tool calls, decisions, drops). It is reachable from a small footer link, so the main UI stays clean and the tracks' "show the trace" requirement is met. | Replaces the trace in the main UI |
| D15 | Posting text is shown as fetched, converted to plain text, never rewritten by the LLM and never rendered as raw HTML. | New |
| D16 | **One sort key, defined only in `scoring/rank.py`:** thin postings last, then match score (high first), then postings with a known date before unknown, then newest first. The company score is shown beside it; a toggle can sort by company score instead. | New |
| D17 | The planner is bounded. The LLM writes queries as JSON; code runs them and enforces the limits (max 3 rounds, stays in the user's country, budget caps). Widening is rule-based in Core and an LLM choice in Stretch. | Replaces "widen location" as the only adaptation |
| D18 | Mock mode means **fake external services** (LLM, Tavily, board APIs, HTTP) over a **real SQLite database**, so auth, CV versions and history work the same in mock and real mode. | Clarifies the CLAUDE.md mock rule for DB-backed endpoints |

---

## 3. User flow

```
Sign in (name)
   ├─ new user ──► Upload CV ──► Review text ──► (place question if CV has none)
   │                                   └─► defaults saved, first search starts ─┐
   └─ returning user ───────────────► latest search results ◄─────────────────┘
                                          │
            ┌─────────────────────────────┼──────────────────────────────┐
            ▼                             ▼                              ▼
       Job detail                    New search                   History / Settings
   (scores, skills, full post,   (pick CV version or upload   (re-run; titles and places,
    apply link)                   new, titles + places)        CV versions, delete data,
                                                               log out)
```

| Screen | Route | What it shows |
|---|---|---|
| Login | `/login` | A name field and a note: "No password: anyone with your name can open this account." |
| Onboarding | `/onboarding` | 1) Upload (drag and drop) or paste. 2) Review the extracted text (editable). 3) Place question only if the CV has none. Then it starts the search and goes to the results page. |
| Search results | `/search/[id]` | While running: progress in plain words; job cards appear as they are matched (company score shows "…" until ready). Done: skill chart at the top, "Learn next" (Gap ROI), job cards, sort toggle. |
| Job detail | `/search/[id]/job/[postingId]` | Match score with breakdown, company score with sources, skills you have and are missing (color + icon), the full post text with skills highlighted, and the apply button. |
| New search | `/new-search` | CV version picker (by date) or upload new, titles (chips), places (picker), Run. Prefilled from the defaults. |
| History | `/history` | Past searches (date, titles, places) with Open and Re-run. |
| Settings | `/settings` | Default titles and places, CV versions (delete), Delete my data, Log out. |
| How it works | `/how/[id]` | Judge view: agent trace, decisions, dropped postings with reasons, credits and LLM calls used. Linked from the results footer. |

A returning user lands on their latest search. (Stretch: saved jobs are re-checked in the background and closed ones are flagged.)

---

## 4. System flow

```mermaid
flowchart TD
  L[Sign in with a name] -->|new| U[CV: PDF, docx, text; image = stretch]
  L -->|returning| R[Latest results]
  U --> T{Text layer found?}
  T -->|yes| P1[pypdf / python-docx]
  T -->|no| O[Vision OCR, text only - stretch]
  P1 --> RV[User reviews text]
  O --> RV
  RV --> PR[Clean profile + glossary; defaults saved]
  PR --> PL[Plan queries: LLM, JSON]
  PL --> D[Discover: Tavily search on job boards]
  D --> B[Expand via board APIs: Greenhouse, Lever, Ashby]
  B --> Q[Quiet checks: open, fresh, place, real]
  Q -->|fail| X[(Dropped, logged for judge view)]
  Q --> RD[Read full text as plain text]
  RD --> E{5+ good jobs?}
  E -->|no, round < 3| W[Widen inside the country] --> D
  E -->|yes| RQ[Requirements, batched, cached by text]
  RQ --> M[Match by code + cached related verdicts]
  M -->|stream cards| R
  M --> C[Company score: hiring + basics; news = stretch]
  C --> G[Rank, skill summary, Gap ROI]
  G --> R
```

---

## 5. Backend plan (FastAPI, Python 3.12, uv)

### 5.1 Module layout

Small modules with one job each. Pure logic has no I/O, so it is easy to test.

```
backend/app/
  main.py                 app factory, routers, lifespan (create data dir + tables,
                          mark stale 'running' searches as failed), error handler
  config.py               all settings (pydantic-settings)
  errors.py               PostuloError subclasses (+ NotFoundError 404, AuthError 401)
  events.py               per-search event bus with replay buffer (§5.4)
  runner.py               starts searches as asyncio tasks and keeps references to them
  cli.py                  existing CLI, updated to the new pipeline
  api/
    deps.py               get_session (DB), current_user (Bearer token)
    routes/               health, auth, me, places, cv, searches, postings, how
  db/
    engine.py             async engine, session factory; PRAGMA journal_mode=WAL,
                          foreign_keys=ON, busy_timeout=5000
    tables.py             ORM tables (§5.3)
    repos/                users.py, cv_versions.py, searches.py, postings.py,
                          companies.py, match_cache.py
  schemas/                Pydantic API shapes; __init__ re-exports
    common.py auth.py cv.py profile.py search.py posting.py
  services/               talks to the outside world (each has a fake for mock mode)
    llm.py                Nebius client (existing; add schema-validated chat_json,
                          vision messages, call counter)
    tavily_client.py      existing; add country, include_usage, format="text" for extract
    http.py               shared httpx client (timeouts, user agent)
    ats/                  detect.py (URL -> ats, board, job id), greenhouse.py, lever.py, ashby.py
    page_data.py          JSON-LD JobPosting parser (datePosted, validThrough, jobLocation)
    html_text.py          HTML -> plain text (stdlib html.parser + html.unescape)
    intake/               pdf.py, docx.py, clean_text.py, router.py, ocr.py (stretch)
    fakes/                fake_llm.py, fake_tavily.py, fake_ats.py, fake_http.py (mock mode)
  domain/                 pure logic, no I/O
    evidence.py           quote check (normalised substring)
    glossary.py           + data/glossary.json
    places.py             + data/places.json (countries + major cities); match job location
    years.py              total years and seniority band from role dates
  agents/                 pipeline steps, one async function per file
    orchestrator.py       search state machine: emits events, saves results as they come
    profile.py            CV text -> profile with quotes
    planner.py            LLM query planning (Core) + reflect (Stretch)
    discover.py           Tavily search + board expansion (keeps today's URL helpers)
    checks.py             quiet checks (replaces verify_agent.py)
    reader.py             full text from board API, else Tavily extract
    requirements.py       postings -> requirements with quotes (batched, cached by text hash)
    matcher.py            profile x requirements -> statuses (uses match_cache)
    company.py            company signals (cached)
    prompts/              one module per prompt (never inline)
      profile.py plan.py reflect.py requirements.py related.py company_news.py ocr.py
  scoring/                pure functions, heavily unit-tested
    match_score.py company_score.py gap_roi.py skill_summary.py rank.py
```

**Retired or rewritten:**
- **Replaced:** `agents/search_agent.py` (helpers move to `discover.py` and `services/ats/detect.py`; `build_queries` is rewritten because `Preferences.location` and `.prompt` go away), `agents/verify_agent.py` → `checks.py`, `agents/score_agent.py` + `prompts/score.py` → `requirements.py` + `matcher.py` + `scoring/`, `services/cv_parser.py` → `services/intake/`, `models/schemas.py` → `schemas/`, `api/routes/jobs.py` → `routes/searches.py`, `agents/mock_data.py` → `services/fakes/`.
- **Tests that must be rewritten with the code:** `test_agents.py`, `test_orchestrator.py`, `test_cli.py`, `test_mock_endpoints.py`.

### 5.2 New dependencies

| Package | Why | When |
|---|---|---|
| `sqlalchemy[asyncio]` 2.x + `aiosqlite` | Async ORM on SQLite | Core |
| `python-docx` | Read `.docx` | Core |
| `pypdfium2` + `pillow` | Render scanned PDF pages and resize images for OCR | Stretch |

Add them with `uv add` (latest versions).

### 5.3 Database (SQLite, `backend/data/postulo.db`)

The app creates `backend/data/` on startup. Add `data/` to `backend/.gitignore` and mount `backend/data` as a volume in `docker-compose.yml`, so the database survives rebuilds.

| Table | Key columns |
|---|---|
| `users` | `id`, `name_key` (unique, lowercased), `display_name`, `default_titles` (json), `default_places` (json), `created_at` |
| `sessions` | `token_hash` (PK, SHA-256 of the token), `user_id` (FK), `created_at`, `last_seen_at` |
| `cv_versions` | `id`, `user_id` (FK), `label` (file name + date, or "Pasted text"), `source_type` (pdf/docx/image/text), `ocr_used`, `clean_text`, `profile` (json), `status` (draft/confirmed), `created_at`, `confirmed_at` |
| `searches` | `id`, `user_id` (FK), `cv_version_id` (FK), `titles` (json), `places` (json), `status` (queued/running/done/failed), `stage`, `note`, `error`, `trace` (json), `usage` (json: Tavily credits, LLM calls), `created_at`, `finished_at` |
| `search_results` | `search_id` (FK), `posting_id` (FK), `match_score` (nullable), `breakdown` (json), `rank` (set at the end), `created_at`. PK (`search_id`, `posting_id`). Rows are written as soon as each job is matched. |
| `postings` | `id`, `url` (canonical, unique), `ats`, `board_slug`, `external_id`, `company_id` (FK), `title`, `location` (json), `workplace_type`, `posted_at`, `valid_through`, `apply_url`, `full_text` (plain), `text_hash`, `requirements` (json), `requirements_model`, `status` (open/closed/unknown), `first_seen_at`, `last_checked_at`, `check_log` (json) |
| `companies` | `id`, `name`, `domain`, `ats`, `board_slug`, `signals` (json with sources), `score` (nullable), `checked_at` |
| `match_cache` | `cv_version_id` (FK), `requirement_name`, `status` (`related` or `missing`), `cv_quote`. PK (`cv_version_id`, `requirement_name`). This makes D6 hold across re-runs. |
| `saved_jobs` (Stretch) | `user_id`, `posting_id`, `saved_at` |

There are no migrations in Phase 1 (`create_all` on startup). "Delete my data" removes the user's rows. Foreign keys cascade from `users`, so this covers sessions, CV versions, searches, results, match cache and saved jobs. The posting and company caches are not personal and stay.

### 5.4 API (JSON; auth = `Authorization: Bearer <token>` unless marked)

| Method and path | Purpose | Notes |
|---|---|---|
| `GET /health` | Status, keys configured, the three model IDs, `mock_mode` | No auth (exists; add model IDs) |
| `POST /api/auth/login` `{name}` | Find or create the user, return `{token, user}` | No auth. 2–40 chars: letters, digits, space, `-`, `_` |
| `POST /api/auth/logout` | Delete the session | |
| `GET /api/me` | User, defaults, `has_cv`, `latest_search_id` | |
| `PUT /api/me/settings` `{titles, places}` | Save defaults | 1–3 titles, 1–5 places |
| `DELETE /api/me` | Delete my data | |
| `GET /api/places?q=` | Search the fixed places list | No auth; from `domain/data/places.json` |
| `POST /api/cv` (multipart `file` **or** form `text`) | Extract text, return the draft `{cv_version_id, text, ocr_used, warnings}` | 10 MB, 10 pages max. `.doc` rejected; images rejected unless `OCR_ENABLED` |
| `PUT /api/cv/{id}` `{text}` | Confirm the text, build the profile, return `{cv_version, profile, suggested: {titles, place\|null}}` | |
| `GET /api/cv` / `DELETE /api/cv/{id}` | List or delete versions | |
| `POST /api/searches` `{cv_version_id, titles, places}` | Start a search, return `{search_id}` | Also saves titles and places as defaults (D11) |
| `GET /api/searches` | History | |
| `GET /api/searches/{id}` | Status, stage, partial or final results, `skill_summary`, `learn_next`, `note` | Safe to reload at any time (results are saved incrementally) |
| `GET /api/searches/{id}/events` | Live stream (`text/event-stream`) | See below |
| `POST /api/searches/{id}/rerun` | Same inputs, fresh checks; returns a new `search_id` | |
| `GET /api/postings/{id}?search_id=` | Full detail: plain post text, apply URL, match breakdown (for that search), company score + sources | |
| `GET /api/how/{search_id}` | Judge view: trace, drops with reasons, usage | Auth required; owner only |
| `PUT` / `DELETE /api/saved/{posting_id}`, `GET /api/saved` | Saved jobs | Stretch |

**Stream behaviour** (fixes late joins, reloads and restarts):
1. On connect, the server first sends a `snapshot` event (status, stage, results so far).
2. If the search is `done` or `failed`, it sends `done` or `error` and closes.
3. Otherwise it replays the search's buffered events, then streams new ones.
4. The client reads it with `fetch` + a stream reader (`EventSource` can't send the auth header). If the connection drops, it reconnects once, then falls back to polling `GET /api/searches/{id}` every 2 s.

Events (one JSON per `data:` line): `snapshot`, `stage {stage, message}`, `job {card}`, `company {posting_id, company_score}`, `note {message}`, `done {search_id}`, `error {message}`.

On startup, any search left `running` (for example after a `--reload`) is marked `failed` with "Search was interrupted, please re-run". `runner.py` keeps a reference to every task so tasks aren't garbage-collected.

### 5.5 Core shapes (in `schemas/`, mirrored in `types.ts`)

```text
Place        {kind: "city"|"country"|"remote", name, country_code|null}
Evidence     {quote: str}                                  # verbatim, checked by code
SkillItem    {name (canonical), type: tech|soft|domain, evidence, inferred: bool}
Role         {title, company, start "YYYY-MM"|null, end "YYYY-MM"|"present"|null, evidence}
Profile      {headline, summary, skills[SkillItem], roles[Role],
              languages[{name, level|null, evidence}], education[{school, degree|null, evidence}],
              place: Place|null, years_total: float|null (code), seniority (code)|null,
              target_titles[str]}
Requirement  {name (canonical), type: tech|soft|domain|language|years|degree,
              importance: must|nice, level|null, min_years: float|null, evidence}
SkillMatch   {requirement, status: have|related|missing_nice|missing_must, cv_evidence|null}
MatchScore   {value: 0-100|null, must_met "x/y", nice_met "x/y", gates_applied[str], thin: bool}
CompanyScore {value: 0-100|null, band: strong|okay|weak|not_enough_data|pending,
              sources[{title, url, date|null}]}
JobCard      {posting_id, title, company, place, workplace_type, posted_at|null,
              match: MatchScore, company: CompanyScore, top_skills[SkillMatch] (max 6)}
SkillSummary [{skill, user_status: have|related|missing, demand: n_jobs, of: total_jobs, must_count}]
LearnNext    [{skill, jobs_improved, avg_gain_points, unlocks: n_jobs}]   # top 3
```

### 5.6 Search pipeline (`orchestrator.run_search`)

| Step | What happens | Model / tool | Cost |
|---|---|---|---|
| 1. Plan | 3–5 queries from titles, places and top skills, as JSON. If the LLM fails, use the rewritten template queries. | Main model, reasoning on | 1 LLM call |
| 2. Discover | Tavily `/search`: `search_depth="basic"`, ATS `include_domains` (add `jobs.eu.lever.co`), `time_range="month"`, `include_usage=true` (credit counting), plus `country` (lowercase name; a weak boost, since `include_domains` dominates). Ask for result dates with `include_published_date` only if M0 confirms the API accepts it; the installed SDK has no such argument, so it would go through a raw call. | Tavily | 1 credit per query |
| 3. Expand | Parse each URL into (ATS, board, job id). For Greenhouse, Lever (`api.lever.co` and `api.eu.lever.co`) and Ashby, fetch the board's job list once. Keep jobs whose title matches the user's titles (glossary-aware token match) and whose location matches a user place. Max 3 per company. | Board APIs | Free; lists cached 6 h |
| 4. Quiet checks | Cheapest first: dedupe → DB cache (checked less than `POSTING_RECHECK_HOURS` ago) → open status (on the board list, else HTTP + JSON-LD `validThrough` + closed-page markers) → freshness (`posted_at` ≤ `RECENT_DAYS`, from board, JSON-LD or Tavily; unknown dates are allowed) → place filter (D9) → company website (from the board API or the page's links/JSON-LD, **not** a Tavily search). Failures are dropped and logged (D5). | Code + HTTP | Free |
| 5. Read | Plain text from the board API (Ashby `descriptionPlain`; Greenhouse `content` unescaped and converted from HTML; Lever `description` + `lists` + `additional`), else Tavily `/extract` with `format="text"` in batches of 20. **No text means dropped** (it can't be grounded). | Board API / Tavily | 1 credit per 5 URLs |
| 6. Widen | If fewer than 5 good jobs and fewer than 3 rounds: Core uses a fixed rule (city → its country, then related titles from the glossary). Stretch lets the LLM choose `widen_place_in_country`, `add_related_titles` or `stop`, and code validates it. It never leaves the user's country unless Remote was picked. | Code (Core) | 0 |
| 7. Requirements | Postings without cached requirements (by `text_hash`), **5 per call**: requirements with quotes, checked by code. German postings get English canonical names and keep the original quote. | Fast model | ~1 call per 5 new postings |
| 8. Match | Glossary exact or alias match → `have`. Pairs not found in `match_cache` go to **one batched call** that may answer `related` only with a CV quote. Verdicts are saved to `match_cache`. Then the score (§7.1). Each job card is saved and streamed as soon as it is scored. | Code + fast model | ≤1 call per search, 0 on re-runs |
| 9. Company | For the top 10 companies: hiring (board list size and newest date) + basics (website, size if stated). Stretch: Tavily news for the top 5 only (`topic="news"`, `time_range="year"`), all articles classified in one batched call with quotes. Cached `COMPANY_CACHE_DAYS`. Cards update through `company` events. | Code (+ Tavily + fast model in Stretch) | Core 0; Stretch ≤5 credits + 1 call |
| 10. Rank and summarise | `scoring/rank.py` (D16), keep the top `MAX_POSTINGS`, compute `SkillSummary` and `LearnNext`, set ranks, send `done`. | Code | 0 |

**Budget** (settings): `MAX_TAVILY_CREDITS_PER_RUN=20`, `MAX_LLM_CALLS_PER_RUN=15`. Typical first run: 3–5 searches per round × up to 3 rounds + about 2 extract credits (+5 news in Stretch) ≈ 8–20 credits. LLM calls: 1 profile + 1 plan + about 3 requirements batches + 1 related (+1 news) ≈ 6–7. If a budget runs out, the pipeline skips to ranking with what it has. Measure the real numbers in M3.

### 5.7 CV intake (`services/intake/`)

| Input | Path |
|---|---|
| PDF with text | pypdf. If the text is under 100 characters per page on average, it's treated as a scan. |
| Scanned PDF (Stretch) | pypdfium2 renders up to 5 pages, then vision OCR. Without OCR, reply "This looks like a scan. Upload a text PDF or .docx, or paste the text." |
| `.docx` | python-docx (paragraphs + tables). |
| PNG/JPG/WebP (Stretch) | Pillow resizes the longest side to 2000 px or less, then vision OCR. |
| Pasted text | Up to 20,000 chars. |
| `.doc`, other | Rejected: "Save it as PDF or .docx." |

The OCR prompt (Stretch) returns the CV text only, never describes photos or people, and keeps the original language. `clean_text.py` strips emails, phone numbers and lines starting with personal labels (`Geburtsdatum`, `Date of birth`, `Familienstand`, `Staatsangehörigkeit`, `Nationality` and so on), best effort. The user sees the cleaned text and can edit it.

### 5.8 Settings (`app/config.py` + `.env.example` + README table)

- **Existing:** `NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, `NEMOTRON_MODEL`, `NEMOTRON_FAST_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `TAVILY_API_KEY`, `MOCK_MODE`, `MAX_POSTINGS`, `CORS_ORIGINS`, `LOG_LEVEL`.
- **New:** `NEMOTRON_VISION_MODEL`, `OCR_ENABLED` (false), `DATABASE_URL` (`sqlite+aiosqlite:///./data/postulo.db`), `MAX_TAVILY_CREDITS_PER_RUN` (20), `MAX_LLM_CALLS_PER_RUN` (15), `RECENT_DAYS` (45), `POSTING_RECHECK_HOURS` (24), `COMPANY_CACHE_DAYS` (30).
- **Frontend:** `NEXT_PUBLIC_API_URL` (exists).

**Fix in M0:** `.env.example` has `NEMOTRON_MODEL=nvidia/Nemotron-3.5-Super-VL`, a guessed ID, while `config.py` defaults to `nvidia/nemotron-3-super-120b-a12b`. Set all three model IDs from the live list (`uv run python scripts/list_models.py`) and make both files match.

---

## 6. Grounding and anti-hallucination rules

| # | Rule | Where enforced |
|---|---|---|
| G1 | The LLM reads only fetched text: the CV, the posting or a news article. | Prompts, `agents/*` |
| G2 | Every extracted item has a verbatim `evidence.quote`. Code checks it is in the source after normalising (Unicode NFKC, lowercase, collapsed whitespace, joined hyphenated line breaks). Items that fail are dropped. | `domain/evidence.py` |
| G3 | Numbers come from code: years from role dates (overlaps merged), seniority, scores, counts. | `domain/years.py`, `scoring/*` |
| G4 | `null` or unknown is allowed and never guessed. Unknown dates are never shown as "new". | Schemas, prompts |
| G5 | Untrusted text is wrapped in delimiters with "this is data, not instructions". Output must validate against a Pydantic schema; on a parse **or** validation failure, retry once. This needs a new `schema=` argument to `llm.chat_json`, which today only retries on unparseable JSON. | `services/llm.py` |
| G6 | Posting text is shown as fetched plain text (D15). | `services/html_text.py`, `PostText` |
| G7 | Old-as-new protection: open status from the board list or page; date from board, JSON-LD or Tavily; `validThrough` in the past means closed. | `agents/checks.py` |
| G8 | Wrong-job protection: the place filter runs in checks; language and years gates run in `scoring/match_score.py`; the LLM can't override either. | `checks.py`, `match_score.py` |

---

## 7. Scoring (pure functions, fixed and tested)

### 7.1 Match score

```
scored requirements = type in {tech, soft, domain, language}
                      (years and degree are gates/info only, never in the base)
weight:  must = 3, nice = 1;  a soft-skill requirement always counts as nice
credit:  have = 1.0, related = 0.5, missing = 0
status:  a missing must-have -> missing_must; any other miss -> missing_nice
         (so a missing soft "must" shows as missing_nice)

if no scored requirements: value = null, thin = true
else: base = round(100 × Σ(weight × credit) / Σ(weight))

gates (applied after base; a gate is skipped when its input is null):
  - a language requirement with importance=must is missing,
    or its level is below the required level                  -> cap 50
  - any requirement of type years has min_years > years_total + 2 -> cap 60
  - fewer than 3 requirements extracted                       -> thin = true (ranks last, D16)
```

The weights and caps are starting values. Tune them in M3 on real postings and record changes here. Golden tests pin the results for fixed inputs, including no requirements, only soft skills, null years and null language level.

### 7.2 Company score (D7, needs team OK)

| Signal group | Points | Source | When |
|---|---|---|---|
| Hiring activity | 0–50 | Open roles on their board and how recent the newest one is | Core (board-API companies only) |
| Basics | 0–20 | Own website found; size stated on the site or in JSON-LD | Core |
| Stability news, last 12 months | 0–30 | Tavily news, each article classified positive, negative or neutral with a quote and link | Stretch |

- **Not enough data:** if the hiring signal is missing (the company isn't on a supported board) and there is no news, the score is `null` with band `not_enough_data`. Otherwise the score is scaled to 0–100 over the groups that have data.
- **Bands:** 70+ strong, 40–69 okay, below 40 weak.
- **Display:** while it is still computing, the band is `pending`. Sources are listed on the job detail page.

### 7.3 Skill summary and Gap ROI

- **Skill summary:** for each canonical skill in the shown jobs, how many jobs ask for it, how many as a must-have, and the user's own status (`have`, `related` or `missing`). Sorted by demand and labelled "in these N jobs".
- **Gap ROI:** for each missing skill of type tech, domain or language (**not** years or degree), re-run the match score as if it were `have`. Report the jobs improved, the average gain in points, and how many jobs lose a cap. Show the top 3 as "Learn next"; mark languages "takes longer". No LLM call.

---

## 8. Frontend plan

### 8.1 Stack

This keeps what exists and adds the most widely used React UI pieces. **New UI libraries need the team's OK per `CLAUDE.md`.**

| Part | Choice | Status |
|---|---|---|
| Framework | Next.js 16 (App Router), React 19, TypeScript strict | Exists |
| Styling | Tailwind CSS 4 | Exists |
| Components | shadcn/ui (Radix-based, copied into `components/ui/`) | New |
| Charts | Recharts via shadcn's chart component | New |
| Icons | lucide-react | New |
| Server state | TanStack Query v5 | New |
| Toasts | sonner | New |

**Next.js 16 notes** (from `node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md`):
- **Async params:** `params` and `searchParams` are async in server components. Our pages are client components and use `useParams()`.
- **No proxy needed:** `middleware` is now `proxy`, but we don't need it, because the token lives in `localStorage`, which `proxy` can't read. Route guarding is client-side.
- **Linting:** `next lint` is gone (we already call `eslint`).
- **Bundler:** Turbopack is the default.

### 8.2 Folder structure

```
frontend/src/
  app/
    layout.tsx                    fonts, QueryProvider, AuthProvider, Toaster
    page.tsx                      redirect: token ? latest search or onboarding : /login
    login/page.tsx
    (app)/layout.tsx              client guard + top bar (logo, New search, History, Settings)
    (app)/onboarding/page.tsx
    (app)/search/[id]/page.tsx
    (app)/search/[id]/job/[postingId]/page.tsx
    (app)/new-search/page.tsx
    (app)/history/page.tsx
    (app)/settings/page.tsx
    (app)/how/[id]/page.tsx       judge view (trace)
  components/ui/                  shadcn: button, card, badge, input, dialog, sheet, tabs,
                                  progress, skeleton, tooltip, select, command, chart
  features/
    auth/      AuthProvider.tsx, useAuth.ts, LoginForm.tsx
    cv/        CvDropzone.tsx, CvPasteBox.tsx, CvReview.tsx, CvVersionPicker.tsx
    search/    SearchForm.tsx, TitlesInput.tsx, PlacesInput.tsx (uses /api/places),
               useSearchStream.ts, ProgressPanel.tsx
    results/   SkillChart.tsx, LearnNext.tsx, JobCard.tsx, MatchScoreRing.tsx,
               CompanyScoreBadge.tsx, SkillChip.tsx, StatusLegend.tsx, SortToggle.tsx, EmptyState.tsx
    job/       JobDetail.tsx, ScoreBreakdown.tsx, SkillGroups.tsx, PostText.tsx,
               ApplyButton.tsx, CompanySources.tsx
    history/   HistoryList.tsx
    settings/  SettingsForm.tsx, CvVersionList.tsx, DeleteDataDialog.tsx
    how/       TraceTimeline.tsx (built from today's AgentTrace), DroppedList.tsx, UsageStats.tsx
  lib/
    api/       client.ts (base URL, auth header, errors -> ApiError), auth.ts, me.ts,
               places.ts, cv.ts, searches.ts, postings.ts, how.ts
    sse.ts     parses the text/event-stream body read via fetch
    types.ts   mirrors backend schemas (change together)
    format.ts  dates ("3 days ago"), scores, places
    status.ts  one map: status -> color, icon, label (used everywhere)
```

Today's `lib/api.ts` is deleted (the new `lib/api/` folder replaces it). `PostuloFlow`, `PostingCard`, `SkillChip`, `StarScore` and `VerifiedBadges` are replaced; `AgentTrace` moves into `features/how/`.

### 8.3 Visual design (white and modern)

| Token | Tailwind | Used for |
|---|---|---|
| Background | `white` | All pages |
| Surface | `zinc-50` | Sections, chart panels |
| Border | `zinc-200` | Cards, inputs |
| Text | `zinc-900` / `zinc-600` / `zinc-400` | Primary / secondary / hints |
| Primary | `indigo-600`, hover `indigo-700` | Main buttons, links, focus rings |
| `have` | `emerald-500` (bg `emerald-50`, text `emerald-700`), lucide `Check` | Skills you have |
| `related` | `sky-500` (bg `sky-50`, text `sky-700`), lucide `Shuffle` | Close match |
| `missing_nice` | `amber-500` (bg `amber-50`, text `amber-700`), lucide `AlertTriangle` | Nice-to-have gap |
| `missing_must` | `rose-500` (bg `rose-50`, text `rose-700`), lucide `X` | Must-have gap |
| Company band | strong `emerald`, okay `amber`, weak `rose`, not enough data `zinc`, pending skeleton | Company badge |

- **Cards:** `rounded-xl`, 1 px `zinc-200` border, `shadow-sm` at most. Buttons are shadcn defaults (indigo primary, white outline secondary).
- **Charts:** white background, `zinc-100` gridlines, no gradients or 3D, bars in the status colors.
- **Skill chart:** horizontal bars, one per skill. The length is demand ("6 of 8 jobs"), the color is your status, and a darker segment is the must-have share.
- **Match score:** a small radial ring (Recharts `RadialBarChart`) with the % in the middle.
- **Accessibility:** status is never shown by color alone (icon + label). Text meets WCAG AA contrast on white. Everything works by keyboard. Light theme only.

### 8.4 Data flow

- **Auth:** `AuthProvider` keeps `{token, user}` in `localStorage`. `lib/api/client.ts` adds the `Authorization` header; on a 401 it clears the token and goes to `/login`.
- **Server state:** TanStack Query hooks (`useMe`, `useCvVersions`, `useSearch(id)`, `usePosting(id, searchId)`, `useHistory`, `useHow(id)`).
- **Live search:** `useSearchStream(id)` applies `snapshot`, then `job` and `company` events into the query cache for `useSearch(id)`, shows `stage` text, and refetches on `done`. Reconnect and polling work as in §5.4.

---

## 9. Testing and verification

| Layer | Tests (no network; fakes from `services/fakes/`) |
|---|---|
| Pure logic | `match_score` golden cases (incl. no requirements, only soft, null years, null level, both caps), `company_score` (bands, not enough data, pending), `gap_roi` (excludes years/degree), `skill_summary`, `rank` (the D16 order), `years` (overlapping roles), `places`, `glossary` (CV vs Computer Vision), `evidence` (German text, line breaks) |
| Intake | text PDF, scan detected, `.docx`, `.doc` rejected, image rejected when OCR is off, `clean_text` strips email, phone and date-of-birth lines |
| Services | ATS URL detection (incl. EU Lever), JSON-LD parsing, HTML to text, Tavily params, Lever `lists` concatenation |
| Pipeline | Orchestrator with fakes: closed or stale jobs dropped silently and logged, widening stays in country, budgets stop work cleanly, LLM failure falls back to templates, re-run gives identical scores (match cache) |
| Stream | snapshot on connect, replay after a late join, immediate close when done, stale `running` marked failed on startup |
| API | every endpoint in mock mode over a temp SQLite DB; 401 without a token; same name gives the same user; delete my data cascades; rerun creates a new search |
| Fairness | deterministic: `clean_text` and the profile mapping drop personal lines, and scoring has no input from them. Manual check in M3: one real CV with two different photos (as images, Stretch) or two different personal-data blocks gives the same skills and scores |
| Frontend | `npm run lint`, `npm run typecheck`, `npm run build`; click through the whole flow in mock mode |

**Done means:** pytest, ruff and mypy green; frontend lint, typecheck and build green; mock-mode click-through works; one real run works with keys (§10 M3).

---

## 10. Build order (fits about 5–6 hours)

Lanes: **BE-A** = backend data and API, **BE-B** = backend pipeline, **FE** = frontend. Times are from the start of the build.

| Milestone | Time | Lane | Tasks | Done when |
|---|---|---|---|---|
| **M0 Contracts and skeleton** | 0:00–0:45 | All | Keys in `.env`; list models and fix the three IDs; check `include_published_date` on the live Tavily API; write `schemas/` + `types.ts`; DB engine + tables; `services/fakes/`; **orchestrator skeleton + `events.py` + `runner.py` that stream fake job cards end to end** (BE-B owns) | `POST /api/searches` + events stream fake cards in mock mode |
| **M1 Vertical slice** | 0:45–2:30 | BE-A | auth, me/settings, places, CV endpoints, intake (PDF, docx, text, clean_text), `profile` agent with evidence, `glossary`, `places`, `years` | Login → CV → profile works (fake + one real call) |
| | | BE-B | ATS clients, `page_data`, `html_text`, `discover`, `checks`, `reader`, caches, rule-based widening | Real run returns open, fresh, in-place postings with plain text |
| | | FE | shadcn setup + theme, layouts, login, onboarding (upload, review, place question), results page with progress + job cards | Login → onboarding → live cards on mock |
| **M2 Matching and screens** | 2:30–4:00 | BE-B | `requirements` (batched), `matcher` + `match_cache`, `match_score`, `rank`, `skill_summary`, `gap_roi`, company score (hiring + basics) | Golden tests pass; re-run gives identical scores |
| | | BE-A | searches history/rerun/detail, postings detail, how endpoint, delete my data | All Core endpoints tested |
| | | FE | skill chart, Learn next, job detail (scores, skill groups, post text with highlights, apply), new search, history, settings, how-it-works view | Full Core flow on mock |
| **M3 Real data and tuning** | 4:00–5:00 | All | `MOCK_MODE=false`; 3 test CVs (EN PDF, DE PDF, docx); tune weights and prompts; measure credits and calls; warm caches for the demo | Real run within budget; top 5 checked by hand |
| **M4 Demo ready** | 5:00–5:45 | All | Empty and error states, bug fixes, backup video, pitch with the architecture slide | Rehearsed twice; video recorded |
| **Stretch** | only if M2 is done on time | Any | OCR (images, scans), company news, LLM reflect, saved jobs + closed-since, usage stats in the how view | Each behind its own flag; Core still green |

**If late, cut inside Core in this order:** company basics (keep hiring only) → Gap ROI (keep the skill chart) → history page (keep re-run on the results page) → LLM planning (templates only).

**Infrastructure tasks (M0):**
- **Git and Docker:** `data/` in `backend/.gitignore`; a `backend/data` volume in `docker-compose.yml`.
- **Docs:** README env table updated.

---

## 11. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Nemotron 3.5 Super VL or Lightning not on Token Factory (unverified) | Use what `/v1/models` lists; OCR stays off without a vision model. |
| `include_published_date` not accepted | Board and JSON-LD dates first; unknown dates allowed and never shown as new. |
| Closed-job responses of Greenhouse and Lever undocumented | "Not in the board list" means closed; check the single-job response live in M1 and note it here. |
| German postings extract poorly | Keep original quotes, output English names, test on DE postings in M3. |
| Slow live demo | Warm caches before the demo; cards stream as they are matched; budgets cap work. |
| Name-only login exposes data | Personal lines stripped (D12), visible notice, delete button. |
| SQLite locking | WAL, `busy_timeout`, one session per task, short transactions. |
| `--reload` kills running searches | Marked failed on startup; the user re-runs. |

---

## 12. Open questions (team)

1. **Company score from public signals only** (D7). Default: yes.
2. **New UI libraries:** shadcn/ui, Recharts, lucide-react, TanStack Query and sonner. `CLAUDE.md` asks for approval.
3. **Tracks:** main Deep Research, subtrack Nemotron Agentic? Default: yes.
4. **Demo length and code freeze:** ask the organisers.

---

## 13. Review log

Version 1 was checked by an independent reviewer against the code, the project notes and the Next.js 16 docs. Version 2 fixes all findings:

- **Schedule:** cut to Core + Stretch to fit about 5–6 h.
- **Ownership:** the orchestrator, event bus and fakes now belong to M0; `profile`, `glossary` and `places` moved into M1.
- **Judge view:** the trace is a Core "How it works" page, because the tracks require it.
- **Stream:** snapshot, replay, incremental saves, stale-run cleanup and task references.
- **Repeatable scores:** a match cache keeps re-runs identical (D6).
- **Budgets:** company website no longer costs Tavily; batching; news limited to the top 5.
- **Formula edge cases:** null and zero cases, `min_years`, gates separate from the base, soft must-haves.
- **Mock mode:** fakes over a real DB (D18).
- **Text sources:** Lever `lists`, Greenhouse HTML, `format="text"`, the EU Lever domain.
- **Streaming and company score:** cards stream after matching, with a `pending` company band.
- **Missing endpoints:** places, onboarding saves defaults, CV rename dropped.
- **Tavily SDK:** it has no `include_published_date`; `include_usage` is used for credit counting.
- **Module list:** evidence module added, retired files and tests listed, `lib/api.ts` clash fixed.
- **Infrastructure:** gitignore, volume, PRAGMAs, no dev-panel build arg needed.
- **Existing code:** `chat_json` gets a schema argument, the settings list is complete, `/health` reports models.
- **Sort and Gap ROI:** one sort key (D16); Gap ROI excludes years and degree; `SkillSummary.user_status`.
- **Tests and milestones:** an honest fairness test and consistent milestone names.
