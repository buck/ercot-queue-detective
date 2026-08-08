# ERCOT Queue Detective

**Live:** https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/

Every power plant proposed in Texas — from a 5-megawatt battery to a 1.5-gigawatt gas plant — first appears in one place: the ERCOT Generator Interconnection Status queue. It's a monthly Excel file, buried on ERCOT's website, listing 1,800+ projects. It's the earliest signal of what will actually be built — years before permits, press releases, or news coverage.

This site downloads that file every month, diffs it against the prior month, and surfaces what changed: new entrants, projects that advanced through studies, capacity revisions, target-date slips, and withdrawals. There's a map (colored by fuel, sized by capacity), a "This Month's Movers" scoreboard, per-project timelines for all 1,827 projects, a natural-language "Ask" tab, and a JSON API for anyone who wants to query it directly.

## What's on the site

- **Interactive map** of all 1,827 projects. Colored by fuel, sized by MW, clustered at low zoom. Click any dot for the full project card.
- **AI / data-center-flavored developer classification.** Projects whose interconnecting entity matches a curated list (*CleanAI, Kalnin Ventures, Palomino Alpha, Bullock Data Center, Liberty Data Center I*) or contains the phrase "Data Center" get a **gold ring** on the map and can be isolated with a sidebar filter toggle. This is *soft evidence, not proof* — the queue does not disclose end-customers — but when developers named "Data Center, LLC" file 1.4 GW gas plants, the pattern is worth surfacing. Documented in the site's glossary.
- **This Month's Movers scoreboard.** Every project that entered, withdrew, advanced through a study phase, slipped its target online date, or changed capacity in the June → July diff. Filterable by change type. Shows the interconnecting entity so you can spot patterns across a single developer.
- **Ask (beta).** Natural-language questions about the queue, answered by `gpt-4.1-mini` running server-side in a Cloudflare Worker. The Worker pre-computes slip magnitudes and dedupes the entity list before passing to the model, so the LLM doesn't do date arithmetic. Best at aggregation and month-over-month comparisons.
- **Per-project timeline pages** — one for each of the 1,827 projects, with full change history, POI location, milestone dates, and a link back to the map.
- **Mobile-first.** Sidebar becomes a slide-in drawer on phones; MapLibre tuned for touch input (larger dots, wider tap tolerance, double-tap zoom disabled to prevent accidental zooms).
- **Deep-link URL params** for reviewers and demos:
  - `?filter=ai-dc` — pre-checks the AI/DC filter toggle
  - `?focus=<INR>` — flies the map to a specific project and opens its card
  - Combine, e.g. [`/?filter=ai-dc&focus=28INR0509`](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/?filter=ai-dc&focus=28INR0509) opens Jack County with Kalnin's Thunder Bird 2 selected.
- **JSON API.** Every dataset the site consumes is available as public JSON — see below.

## What's in the queue right now (July 2026 snapshot)

- **440 GW** of proposed generation — roughly five times Texas's peak summer demand
- **1,827 projects**: 898 batteries, 623 solar, 161 wind, 135 gas
- **30 new projects entered** the queue this month (11.2 GW)
- **31 projects withdrew**
- **126 projects slipped their target online date** (24.3 GW affected)

## The story of this month

The signature of AI-driven load growth is showing up in the queue as gas plants filed by developers with data-center-flavored names.

**New in July — 9 gas plants, 4.5 GW total, both operators data-center-flavored:**

- **Kalnin Ventures** — two identical 1,273 MW gas plants in Jack County. [Thunder Bird 1](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/30INR0110/) · [Thunder Bird 2](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/28INR0509/) · [see on map](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/?filter=ai-dc&focus=28INR0509)
- **Palomino Alpha** — five identical 400 MW gas plants in Guadalupe County ("Alpha Power Phase 1–5"). [see on map](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/?filter=ai-dc&focus=28INR0532)

**Already in the queue and on-theme:**

- **CleanAI, LLC** — two gas plants (Three Canes Gas P1 & P2) in Freestone County, MW undisclosed. [see on map](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/?filter=ai-dc&focus=27INR0651)
- **Bullock Data Center** — 1.4 GW gas in Hill County ([Bullock Gas](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/33INR0005/)). Entered the queue in June and completed its screening study by July 29.
- **Liberty Data Center I** — a second 1.4 GW gas plant at the same Hill County site.

Meanwhile, [Lost Pines Power Park](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/30INR0052/) — an 880 MW gas plant — pushed its target online date from December 2030 to June 2033. A two-and-a-half-year slip in a single monthly report.

Explore the full pattern: [all AI/DC-flavored projects on the map](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/?filter=ai-dc).

## Data source

Raw data comes from the [ERCOT Generator Interconnection Status Report](https://www.ercot.com/gridinfo/resource), a public monthly Excel workbook. This project downloads it, parses the "Large Gen" and "Small Gen" sheets, stores everything in SQLite, and diffs consecutive snapshots. Not affiliated with or endorsed by ERCOT.

The current database contains **31 monthly snapshots** (Jan 2024 – Jul 2026), yielding **10,428 diffs** and **8,233 field-level change events** across the queue's ~28 months of covered history.

## Architecture

```
data/raw/              ERCOT GIS Excel snapshots (one per month)
data/db/               SQLite database (built from snapshots)
etl.py                 Idempotent loader: Excel → SQLite → derived tables
api.py                 FastAPI JSON API (for local development)
web/                   Astro static site + MapLibre GL JS
web/public/api/        Static JSON exported from the API for production
web/public/_worker.js  Cloudflare Worker: proxies /api/ask to OpenAI, serves static assets otherwise
.github/workflows/     Monthly cron: download → ETL → export → rebuild → deploy
```

**Backend:** Python 3.11+ + pandas + SQLite. Four tables: `gis_snapshot` (raw monthly rows), `projects` (current state), `project_history` (flattened change log), `diffs` (precomputed month-over-month deltas with typed change categories: `NEW`, `WITHDRAWN`, `STATUS_ADVANCED`, `STATUS_REVERTED`, `COD_SLIPPED`, `COD_ADVANCED`, `CAPACITY_CHANGED`, `OWNERSHIP_CHANGED`).

**Frontend:** Astro with `output: 'static'`. MapLibre GL JS (from CDN) rendering OpenStreetMap tiles + a GeoJSON layer with clustering. 1,828 pre-rendered pages: the map + one per project INR.

**Ask (LLM) path:** browser → Cloudflare Worker route `/api/ask` → OpenAI `gpt-4.1-mini`. All of the queue data (movers, unique entities, per-project fields) is loaded into the prompt each request — it fits comfortably in the 1M-token context window.

**Hosting:** Cloudflare (Worker with static-asset binding). Deploys automatically from `master` via the connected repo.

## Local development

```bash
# 1. Set up the Python environment
uv sync

# 2. Download GIS snapshots (populates data/raw/)
.venv/bin/python download_gis.py

# 3. Run the ETL — builds data/db/ercot_queue.db
.venv/bin/python etl.py

# 4. Start the API (development)
.venv/bin/uvicorn api:app --port 8000 --reload

# 5. Regenerate the static JSON files
curl -s "http://localhost:8000/api/projects?limit=5000" > web/public/api/projects.json
curl -s "http://localhost:8000/api/summary"             > web/public/api/summary.json
curl -s "http://localhost:8000/api/movers?limit=200"    > web/public/api/movers.json
curl -s "http://localhost:8000/api/filters"             > web/public/api/filters.json

# 6. Build & serve the static site
cd web
npm install
npm run build
npm run preview
```

## JSON API

Everything you see on the site is available as JSON. Freely usable for non-commercial reporting, research, and analysis.

```
GET  /api/summary                              # dashboard stats
GET  /api/projects?fuel=SOL&min_mw=100         # filtered project list
GET  /api/projects/{inr}                       # single project + change history
GET  /api/movers?change_type=NEW               # this month's biggest movers
GET  /api/filters                              # dropdown values
POST /api/ask   { "question": "..." }          # natural-language query (Worker → OpenAI)
```

### Example: biggest new gas plants this month
```bash
curl /api/movers?change_type=NEW | \
  jq '.movers[] | select(.fuel=="GAS") | {name: .project_name, mw: .capacity_mw, entity: .interconnecting_entity}'
```

### Example: every COD slip above 500 MW
```bash
curl "/api/projects?change_type=COD_SLIPPED&min_mw=500&changed_since=2026-06-01"
```

### Example: full change history for a project
```bash
curl /api/projects/33INR0005 | jq '.diffs'
```

## Refresh cadence

Rebuilt monthly by a GitHub Actions cron (7th of each month, a few days after ERCOT typically publishes). Also runnable on-demand via `workflow_dispatch`.

## Scope

This project focuses narrowly on the ERCOT GIS queue. Deliberately out of scope: cross-source entity resolution (permit LLC ↔ queue INR ↔ press release), PUCT/FERC/TCEQ ingestion, and any people/organization enrichment. Those are separate problems.

The "AI / data-center flavored" classification is a curated developer-name heuristic, not a customer disclosure. The queue does not report end-user identity for any project. Treat the flag as a lead, not a fact.

## Built

Candid Intelligence Hackathon, Houston, August 2026. Python + SQLite + FastAPI + Astro + MapLibre GL JS + OpenAI. Deployed on Cloudflare.

Public data, used under ERCOT's open data policy. Not affiliated with or endorsed by ERCOT.
