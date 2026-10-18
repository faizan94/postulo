# Postulo: Phase 2 (fixes and improvements)

> Started 18 Oct 2026 from team feedback after the first real use. Phase 1 rules still apply
> (`PHASE1_PLAN.md` §2 decisions, grounding rules G1–G8). Where this file differs, it wins.

## 1. What was reported, and the root cause we found

| # | Reported | Root cause (checked) |
|---|---|---|
| R1 | "It finds exactly the same title, not similar ones (AI Engineer should also find ML / prompt / LLM engineering)." | `domain/titles.py` matches every word of the title. Related titles were only used in widening round 3, and the glossary had few AI titles. |
| R2 | "PDF extraction loses information." | The team's real CV became **1,147 lines of ~3 characters** with pypdf's default mode (each word drawn separately). Headings, sections and quotes broke. pypdf `layout` mode and pdfium both rebuild **68 clean lines with the same 319 words** (measured). |
| R3 | "There is no structured summary of what was taken from the CV." | The profile is built and stored, but the UI never shows it. |
| R4 | "Search with no place doesn't work; places are hard." | `places` is required (min 1) and only a fixed list of ~55 places is accepted. City searches drop remote jobs in the same country. |
| R5 | "Search is not open-ended and easy." | The user must enter exact titles as chips; there is no free-text search. |
| R6 | "Some filters don't work properly." | The only result control is a sort toggle; there is no way to filter by work type, match or freshness. The place filter misses common formats ("Remote - Germany" for a Berlin search, "DE" country codes). |

## 2. Decisions (add to PHASE1_PLAN §2)

| # | Decision |
|---|---|
| D19 | **PDF reading picks the best of several extractors** by a quality score (word coverage, line length): pypdf layout mode first, pdfium and plain mode as alternatives, two-column pages split by column. If the best text is still poor, **Nemotron 3.5 Super VL reads the page images** (tested on Token Factory: 1.7 s per page). Images and scans use the same vision path. `OCR_ENABLED` now defaults to **true**. |
| D20 | **Title matching uses role families.** A search for "AI Engineer" also matches its family (Machine Learning Engineer, ML Engineer, LLM Engineer, GenAI Engineer, Applied AI Engineer, AI/ML Engineer, Prompt Engineer, Applied Scientist). Exact-title jobs and family jobs are both kept from round 1; cards say "Related role" for family matches. Ranking stays by match score, so the profile decides what comes first. |
| D21 | **Open search.** One free-text box ("AI engineer, remote, Python") is turned into titles, places and keywords: Nemotron parses it, code validates it, and rules (glossary titles, places list, "remote") are the fallback. The parsed chips stay editable. |
| D22 | **Places are optional.** No place = "Anywhere" (no place filter). Any typed place is accepted: known places are matched structurally, unknown ones by name. Regions "Europe" and "DACH" are added. A city search also accepts **remote jobs in the same country**. |
| D23 | **"What we read from your CV".** A structured profile card (summary, years and seniority, roles, skills grouped by type, languages, education, place) appears after the CV review, on the results page (collapsible) and on a Profile page. The summary is written by Nemotron from the CV only and labelled as an AI summary; every other field keeps its verified quote. |
| D24 | **Result filters** (client-side, instant): work type (Remote / Hybrid / On-site), minimum match (Any / 50% / 75%), posted (Any / 7 / 30 days), title match (All / Exact title only). |
| D25 | **Tokenized form for every comparison** (`domain/normalize.py`). Skills compare by key (case, spaces, dots and hyphens ignored: "REACT" = "React" = "react.js"; "Node JS" = "Node.js"; unknown skills like "Flyte" = "flyte"). Titles compare by normalized tokens (gender marks removed, "Sr."/"Eng" expanded, "Front-End" = "Frontend", German compounds split: "Softwareentwickler" ~ "Software Engineer"; short words like "AI" must match exactly). Places compare by every spelling ("München" = "Muenchen" = "Munchen"). The longest glossary match wins ("React Native" is not "React"). In LLM requirement names, "A/B" means alternatives and "A, B and C" means all of them. Display text never changes. Requirements cache bumped to `v4`. |

## 3. Build order

1. PDF reading (R2) + tests on the team CV and synthetic two-column PDFs.
2. Title families + related flag (R1).
3. Optional and free places, regions, remote-in-country (R4, part of R6).
4. Open search parser + API (R5).
5. Profile card (R3).
6. Result filters (R6).
7. Tests, lint, build, browser re-test with the team CV end to end.
