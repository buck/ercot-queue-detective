# ERCOT Queue Detective

**Live:** https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/

Every power plant proposed in Texas — from a 5-megawatt battery to a 1.5-gigawatt gas plant — first appears in one place: the ERCOT Generator Interconnection Status queue. It's a monthly Excel file, buried on ERCOT's website, listing 1,800+ projects. It's the earliest signal of what will actually be built — years before permits, press releases, or news coverage.

This site downloads that file every month, diffs it against the prior month, and surfaces what changed: new entrants, projects that advanced through studies, capacity revisions, target-date slips, and withdrawals. There's a map (colored by fuel, sized by capacity), a "This Month's Movers" scoreboard, per-project timelines for all 1,827 projects, and a JSON API for anyone who wants to query it directly.

## What's in the queue right now (July 2026 snapshot)

- **440 GW** of proposed generation — roughly five years of the entire state's electricity supply
- **1,827 projects**: 881 batteries, 621 solar, 161 wind, 130 gas
- **30 new projects entered** the queue this month (11.2 GW)
- **31 projects withdrew** (5.6 GW)
- **126 projects slipped their target online date** (24.3 GW affected)

## The story of this month

Nine of this month's new gas plants — 4.5+ GW total — are from developers with data-center-linked names:

- **Kalnin Ventures** filed two identical 1,273 MW gas plants in Jack County ([Thunder Bird 1](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/30INR0110/), [Thunder Bird 2](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/28INR0509/))
- **Palomino Alpha** filed five identical 400 MW gas plants in Guadalupe County ("Alpha Power Phase 1–5")
- A developer literally named **CleanAI, LLC** filed two gas plants ("Three Canes Gas P1/P2") in Freestone County
- [Bullock Gas](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/33INR0005/) — 1.4 GW, owned by "Bullock Data Center, LLC" — entered the queue in June and already advanced through its screening study by July

Meanwhile, [Lost Pines Power Park](https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/project/30INR0052/) — an 880 MW gas plant — pushed its target online date from December 2030 to June 2033. A two-and-a-half-year slip in a single monthly report.

## Data source

Raw data comes from the [ERCOT Generator Interconnection Status Report](https://www.ercot.com/gridinfo/resource), a public monthly Excel workbook. This project downloads it, parses the "Large Gen" and "Small Gen" sheets, stores everything in SQLite, and diffs consecutive snapshots. Not affiliated with or endorsed by ERCOT.

The current database contains **31 monthly snapshots** (Jan 2024 – Jul 2026), yielding **10,428 diffs** and **8,233 field-level change events** across the queue's ~28 months of covered history.

## Architecture

```
data/raw/            ERCOT GIS Excel snapshots (one per month)
data/db/             SQLite database (built from snapshots)
etl.py               Idempotent loader: Excel → SQLite → derived tables
api.py               FastAPI JSON API (for local development)
web/                 Astro static site + MapLibre GL JS
web/public/api/      Static JSON exported from the API for production
.github/workflows/   Monthly cron: download → ETL → export → rebuild → deploy
```

**Backend:** Python 3.13 + pandas + SQLite. Four tables: `gis_snapshot` (raw monthly rows), `projects` (current state), `project_history` (flattened change log), `diffs` (precomputed month-over-month deltas with typed change categories: `NEW`, `WITHDRAWN`, `STATUS_ADVANCED`, `STATUS_REVERTED`, `COD_SLIPPED`, `COD_ADVANCED`, `CAPACITY_CHANGED`, `OWNERSHIP_CHANGED`).

**Frontend:** Astro with `output: 'static'`. MapLibre GL JS (from CDN) rendering OpenStreetMap tiles + a GeoJSON layer with clustering. 1,828 pre-rendered pages: the map + one per project INR.

**Hosting:** Cloudflare (Worker with static-asset binding). Deploys automatically from `master` via the connected repo.

## Local development

```bash
# 1. Set up the Python environment
uv venv
uv pip install -r pyproject.toml

# 2. Download GIS snapshots (populates data/raw/)
.venv/bin/python download_gis.py

# 3. Run the ETL — builds data/db/ercot_queue.db
.venv/bin/python etl.py

# 4. Start the API (development)
.venv/bin/uvicorn api:app --port 8000 --reload

# 5. Regenerate the static JSON files
curl -s "http://localhost:8000/api/projects?limit=5000" > web/public/api/projects.json
curl -s "http://localhost:8000/api/summary" > web/public/api/summary.json
curl -s "http://localhost:8000/api/movers?limit=200" > web/public/api/movers.json
curl -s "http://localhost:8000/api/filters" > web/public/api/filters.json

# 6. Build & serve the static site
cd web
npm install
npm run build
npm run preview
```

## JSON API

Everything you see on the site is available as JSON. Freely usable for non-commercial reporting, research, and analysis.

```
GET /api/summary                              # dashboard stats
GET /api/projects?fuel=SOL&min_mw=100         # filtered project list
GET /api/projects/{inr}                       # single project + change history
GET /api/movers?change_type=NEW               # this month's biggest movers
GET /api/filters                              # dropdown values
```

### Example: biggest new gas plants this month
```bash
curl /api/movers?change_type=NEW | \
  jq '.movers[] | select(.fuel=="GAS") | {name, mw: .capacity_mw, entity: .interconnecting_entity}'
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

## Built

Candid Intelligence Hackathon, Houston, August 2026. Python + SQLite + FastAPI + Astro + MapLibre GL JS. Deployed on Cloudflare.

Public data, used under ERCOT's open data policy. Not affiliated with or endorsed by ERCOT.
