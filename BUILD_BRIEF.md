# ERCOT GIS Queue Detective — Saturday Build Brief

**Audience:** Claude, cold-started on the laptop Saturday morning 2026-08-08.
**Companion doc:** `Candid_Intelligence_Hackathon_Brief.md` (read first for full domain context).

---

## 1. Situation

- Event: Candid Intelligence hackathon, Sat 2026-08-08, Museum District, Houston. Luma: https://luma.com/m7sk0hyv
- Format: half day, ~5 hours of building.
- Budget: $20 Claude Pro (user's account) + $50 OpenAI API credit (per participant, provided).
- Solo or small ad-hoc team; user owns all technical decisions.
- Machine: laptop, NixOS install, 250 GB SSD. Fallback: SSH over Tailscale to home NixOS desktop.

## 2. User profile (short)

- Deep experience with public-data ETL pipelines: CMS Medicare platform, DoD J-books, EPA, FFIEC, ideabrowser, creainews, houstonspca fosters, houston civicdata (see `CONTEXT.md` in this directory for the relevant patterns).
- Treat as an expert operator, not a beginner. Assume competence on Python, SQLite, Astro/Next, MapLibre, GitHub Actions, Cloudflare.
- NixOS conventions: prefer `python3.withPackages` in `/etc/nixos/configuration.nix` for anything long-running; uv venv for project-scoped scratch.
- Git email: `buck@compact.com` (per feedback memory).
- Editor: VS Code. Not Cursor.

## 3. The build

**Product:** ERCOT GIS Queue Detective — a live, addictive dashboard + JSON API for the ERCOT Generator Interconnection Status (GIS) report, showing month-over-month diffs. Houston-centric map, per-project story pages, "biggest movers this month" leaderboard.

**Post-hackathon intent:** run it publicly, indefinitely, at $0–5/month, as a resource for journalists and researchers. Design decisions should preserve that path.

**Scope discipline — do NOT build:**
- Cross-source entity resolution (permit LLC ↔ queue INR ↔ press release). That's Candid's headline commercial line — stay narrower to keep the public version clearly complementary.
- PUCT, FERC, TCEQ, RRC ingestion. GIS-only.
- People, LinkedIn, conferences, outreach sequences (that's Track 2 — different game).
- Chat/LLM interface unless time permits at H+4:00. The dashboard is the star.

## 4. Legal / IP posture

- **Before signing anything Saturday morning:** screenshot the Luma page and any check-in waiver. Read IP-assignment and license-back clauses carefully.
- Push code to user's *personal* GitHub org from the first commit. Never to a Candid org.
- If asked in judging: *"I reuse an ingest/publish scaffold I've developed across other public-data projects (CMS, DoD J-books, EPA, FFIEC). All ERCOT-specific work is from today."* Casual, transparent.
- If they hand out a broad IP assignment: user's call, but the honest default is skip the prize rather than sign it away.

## 5. Data sources

- **ERCOT Generator Interconnection Status (GIS) report** — monthly Excel workbook, ~30k rows, one row per project unit. Landing area: `https://www.ercot.com/gridinfo/resource` (verify the exact filename on the day). Key columns typically include: INR, Project Name, Interconnecting Entity, County, POI Location, Fuel, Technology, Capacity (MW summer/winter), Screening Study Status, FIS, IA Signed, GIA Signed, Air Permit, Water Availability, COD, and various milestone dates.
- **Prior month's snapshot** — must have at least two snapshots to demo the diff. If ERCOT doesn't publish an archive, use Wayback Machine or download last month's file now and stash it in the repo.
- Optional (only if trivial): ERCOT MORA report for resource-adequacy framing text.
- No scraping needed. Direct file downloads only. Attribute the source clearly.

## 6. Architecture

**Backend — Python + SQLite**
- `uv` venv, `pyproject.toml`. Packages: `pandas`, `openpyxl`, `pyarrow`, `requests`, `python-dateutil`.
- Tables:
  - `gis_snapshot(snapshot_date, inr, ...raw columns...)` — every monthly snapshot appended, keyed by (snapshot_date, inr).
  - `projects(inr, canonical fields, latest_snapshot_date)` — current state per INR.
  - `project_history(inr, event_date, field, old_value, new_value)` — append-only flattened change log.
  - `diffs(from_snapshot, to_snapshot, inr, change_type, detail)` — precomputed per-month diffs (change_type ∈ {NEW, WITHDRAWN, STATUS_ADVANCED, STATUS_REVERTED, COD_SLIPPED, COD_ADVANCED, CAPACITY_CHANGED, OWNERSHIP_CHANGED}).
- ETL is idempotent: load-snapshot → recompute-projects → recompute-diffs.

**Query layer**
- Datasette on the SQLite file → free JSON API + faceted browse. Bind-mounted read-only.
- Or plain FastAPI if more control needed on the map endpoint (`/api/projects?bbox=&fuel=&changed_since=`).

**Frontend — static site + MapLibre**
- Astro (preferred: fast, low ceremony) or Next.js static export.
- MapLibre GL JS + Protomaps or OSM tiles. Do NOT reach for Mapbox unless already comfortable — the free tier is fine but adds an account dependency.
- Views:
  1. **Landing map:** Texas outline, project markers sized by MW, colored by fuel; toggle "show this month's changes only"; sidebar filters (fuel, county, status, capacity range, COD year).
  2. **This month's movers:** scoreboard of new / advanced / withdrawn / COD-slipped, ranked by capacity.
  3. **Project detail** at `/project/[INR]`: header (name, entity, county, MW, fuel, current status), timeline of milestone events, mini-map, raw source data table.
  4. **About / API:** the "for journalists" pitch, refresh cadence, JSON API examples, disclaimer + source attribution.

**Refresh & hosting**
- GitHub Actions cron, monthly (day-of-month 5 or wherever the report lands + a couple days buffer). Also a manual `workflow_dispatch` trigger.
- Job: download latest GIS → run ETL → rebuild static site → deploy.
- Hosting: Cloudflare Pages (free) or Vercel (free). Same repo holds code + SQLite artifact.
- Domain: hold decision until after hackathon; Cloudflare Pages subdomain is fine for the demo.

## 7. Model budget (Pro plan across 5 hours)

The 5-hour build window aligns roughly with one Pro-plan session cap. Burning Opus quota by H+2:00 leaves the demo push crippled. Strategy:

- **Default: Sonnet 4.6.** Routine component code, ETL, SQL, MapLibre config, filter UI, API endpoints, README first draft, refactors. Probably 70–80% of turns.
- **Escalate to Opus 4.7** only for: (a) architecture decisions when something surprises you, (b) prose that has to land (landing-page copy, per-project story framing, demo narrative), (c) debugging genuinely weird data (unknown column semantics, encoding oddities), (d) any moment Sonnet's answer feels shallow or wrong. Budget: ~4–6 substantial Opus turns across the day.
- **Drop to Haiku 4.5** for mechanical work: terminal commands, file renames, simple edits with clear specs, data spot-checks, reading diffs, deploy commands.
- If you catch yourself asking Opus "make this button smaller" — downshift.
- Fast mode = Opus 4.7 with faster output, same quota impact. Turn it off before Haiku-tier work.
- Pre-Saturday scaffolding should be mostly Sonnet (routine setup) with Haiku for shell work — save Opus quota for game day.

## 8. Timeline

### Pre-Saturday (Thursday night → Friday)

- [ ] Laptop: NixOS install done, dev tools working (git, gh, uv, node, sqlite, ripgrep, direnv). Tailscale up. **[haiku]**
- [ ] Confirm SSH-to-home fallback works from a coffee shop / different network. **[no model]**
- [ ] Create personal GitHub repo (`ercot-queue-detective` or similar). **[haiku]**
- [ ] Manually download the two most recent ERCOT GIS reports; save to `data/raw/`. Sanity-check they open. **[haiku]**
- [ ] Scaffold repo: `uv init` (or NixOS python env), Astro create, MapLibre skeleton page, empty SQLite schema file. **[sonnet]**
- [ ] Deploy skeleton to Cloudflare Pages so the deploy path is already proven. **[sonnet]**
- [ ] Do NOT build the actual ETL, diff logic, or map yet — that's Saturday's work. The pre-work is scaffolding only.

### Saturday hour by hour

**H+0:00 — H+0:30 · Setup & data load**
- Confirm venue wifi + phone hotspot both work. Push initial commit. **[no model / haiku]**
- Load both GIS snapshots into SQLite via pandas. Verify row counts, INR uniqueness, dtype coercion. **[sonnet]**
- If GIS columns look weirder than expected (unit variants, merged headers, encoding): **[opus]** for one focused diagnosis turn, then back to sonnet.

**H+0:30 — H+1:30 · ETL + diff**
- Build `projects` canonical table (latest state per INR). **[sonnet]**
- Design `change_type` taxonomy for `diffs` (what counts as STATUS_ADVANCED vs STATUS_REVERTED given GIS milestone columns): **[opus]** for the design turn, since this shapes the whole product.
- Implement the diff computation once the taxonomy is fixed. **[sonnet]**
- Spot-check diffs against 3–5 named projects. **[haiku]**
- Geocode: join county name → county centroid lat/long (bundle a static county centroids CSV in the repo; no live geocoding API). **[haiku]**

**H+1:30 — H+3:00 · Map + filters**
- MapLibre map of Texas. Markers sized by MW, colored by fuel. **[sonnet]**
- Sidebar filters: fuel, county, status, capacity range, changed-this-month toggle. **[sonnet]**
- "This month" banner: `N new · M advanced · K withdrawn · P COD slips`. **[haiku]**
- Click marker → project detail card slides in. **[sonnet]**
- If MapLibre clustering or projection gets weird: **[opus]** for one focused debugging turn.

**H+3:00 — H+4:00 · Story surfaces**
- Per-project permalink `/project/[INR]` with milestone timeline. **[sonnet]**
- "Biggest movers this month" scoreboard, ranked by capacity, filterable by change type. **[sonnet]**
- Landing-page copy that reads like data journalism, not a schema dump. **[opus]** — this is the addictiveness lever; worth the spend.

**H+4:00 — H+4:30 · Polish**
- Loading/empty states, mobile check, keyboard focus. **[haiku]** — mechanical, clear spec.
- README first draft: what it is, sources, refresh cadence, JSON API examples, next-week plan. **[sonnet]**
- README polish pass on the top-of-file pitch. **[opus]** — judges may skim this before the demo.
- Deploy final build. Verify the live URL loads in an incognito window from phone hotspot. **[haiku]**

**H+4:30 — H+5:00 · Demo prep**
- Rehearse 2-minute walkthrough: land → filter Houston area → toggle "this month" → click a big mover → its full timeline. **[no model]**
- Prep 3 concrete stories a judge can see instantly (e.g., "the largest new gas project this month," "a data-center-adjacent load that slipped 18 months"). **[opus]** — narrative framing; this is what wins the room.
- Local screencap / video backup in case venue wifi dies mid-demo. **[haiku]**

### If time runs short (cut order)
1. Drop the per-project timeline page; keep detail as an in-map card only.
2. Drop the sidebar filters beyond fuel + changed-this-month.
3. Drop Datasette; hardcode a `/api/projects.json` static dump.
4. Never drop: the map, the this-month diff view, the deployed public URL.

### If time is spare (stretch order)
1. Simple OpenAI-backed "ask a question" box that translates NL → SQL against the SQLite (rate-limited).
2. RSS feed of this-month changes.
3. Per-county view page.
4. Basic email alert signup (Cloudflare Workers + Resend free tier).

## 9. Cost model (going public afterward)

| Item | Cost |
|---|---|
| Cloudflare Pages hosting | $0 |
| GitHub Actions monthly cron | $0 |
| SQLite storage in repo / R2 | $0 |
| Map tiles (MapLibre + Protomaps/OSM) | $0 |
| Optional LLM "ask" box (rate-limited) | $1–5 / mo |
| Domain | ~$12 / yr |
| **Total ongoing** | **$0–5 / month** |

## 10. Judging alignment (Candid's rubric → build choices)

- **Liveness / robustness** → GH Actions cron, single Excel source, deterministic ETL.
- **Presentation** → the map + this-month-mover framing *is* the "addictive dashboard" ask; monitorthesituation-style feel is the target.
- **Signal quality** → GIS diff is the actual leading indicator of Texas grid buildout; nothing derivative.
- **Depth on the hard part** → stage inference falls out cleanly from GIS milestone columns + diff logic; no hand-waving needed.
- **Extensibility** → same schema pattern extends to PUCT/FERC/TCEQ next week; JSON API means others can build on it.
- **Candid ethos ("owner's engineer at software speed")** → reused scaffold pattern is exactly this.

## 11. Handoff conventions for Saturday's Claude

- Read `Candid_Intelligence_Hackathon_Brief.md` first for the hackathon domain.
- Read `CONTEXT.md` in this directory for user conventions and prior public-data patterns (CMS, DoD, FFIEC, ideabrowser, civicdata) — this replaces the desktop's memory system, which is not on the laptop.
- All operational preferences (Python packaging, git email, NixOS package policy, editor, secrets handling, notifications) are in `CONTEXT.md`. Trust it as the source of truth for user conventions during this build.
