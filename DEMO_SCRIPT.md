# Demo Script — ERCOT Queue Detective

**Live URL:** https://ercot-queue-detective.cloudflare-reg-f0f.workers.dev/

**Target length:** 2 minutes  
**Golden path:** Land → hero fact → map → filter Houston → toggle "this month" → click a big mover → per-project timeline → API call-out

Everything in this script is verified against the current July 2026 snapshot. Numbers to hit are in **bold**.

---

## Opening (15 sec) — the hook

> "There are **440 gigawatts** of proposed power plants waiting to plug into the Texas grid right now. That's roughly **five times** what Texas uses on a hot summer afternoon. Most of them will never get built. The question is which ones will, and why."

> "The ERCOT interconnection queue is where you see that first — years before permits or press releases. This site tracks it, month over month."

*(By this point the map is on screen. Judges are looking at all 1,800+ dots.)*

---

## The map (30 sec) — show, don't tell

*[Point at map]*

> "Every dot is a proposed plant. **Sized by megawatts, colored by fuel** — orange gas, yellow solar, blue wind, purple batteries. Roughly **1,800 projects** in the current snapshot."

*[Zoom to Houston area]*

> "Here's the Houston zone. Lots of big BESS installations along the ship channel — batteries are actually the largest category by project count."

*[Toggle "Changed this month only" checkbox in the sidebar]*

> "Now we're only seeing projects that moved this month: new entries, withdrawn projects, projects that advanced through study, projects that slipped their target online date. About **220 dots** left."

---

## The story of the month (30 sec) — the AI/gas hook

*[Point at the "This month" callout in the sidebar, or click Movers tab and filter to New]*

> "The story this month is **nine new gas plants totaling four and a half gigawatts** — all with names that give the game away."

> "Kalnin Ventures filed **two identical 1,273 MW gas plants** in Jack County. Palomino Alpha filed **five 400 MW plants** in Guadalupe County. And a company literally named **'CleanAI, LLC'** filed two more in Freestone."

> "This is the AI-data-center power buildout showing up in the physical grid. Six months ago these developers weren't in the queue at all."

---

## A specific project (30 sec) — the depth

*[Click a big dot in the Jack County / North Texas area, or open /project/33INR0005/ directly]*

> "Let me show you one project up close. This is **Bullock Gas** — a 1.4 GW gas plant. Look at the owner: **'Bullock Data Center, LLC.'**"

*[Point to the change history section on the project page]*

> "This project first appeared in the queue in **June**. By **July** — one month later — it had already advanced through its screening study **and** pulled its target online date **in by a full year**, from 2033 to 2032. That's unusually fast, and it means someone is aggressively pushing this project forward."

---

## The infrastructure (15 sec) — closing

*[Click the About / API tab]*

> "Everything you're seeing — the diffs, the timelines, every field — is exposed as a **free JSON API**. GitHub Actions rebuilds it from the raw ERCOT file on the 7th of every month. Zero login. It's public data, ours in the sense that anyone can build on top of it."

> "That's ERCOT Queue Detective. **440 GW proposed, tracked and diffed, live URL, monthly refresh, free API.**"

---

## Backup stories (if you have extra time or something breaks)

### The Kalnin twins
> "Kalnin Ventures — a Houston-based investment firm — filed two identical 1,273 MW gas plants side by side in Jack County. Same size, same county, same month. That's roughly the output of one large nuclear reactor, twice, from one filer."

### The Lost Pines slip
*[Open /project/30INR0052/]*
> "Lost Pines Power Park — an 880 MW gas plant — pushed its target online date from **December 2030 to June 2033**. **Two and a half years** in one report. That's the kind of slip that tells you something specific went wrong: permit, financing, off-taker. This site surfaces it in seconds; without it you'd have to read every monthly ERCOT PDF by hand."

### The withdrawal pattern
> "Thirty-one projects were withdrawn this month, five and a half gigawatts of capacity gone from the queue. Batteries dominate the withdrawals — the interconnection process is expensive and small BESS projects churn a lot."

---

## If something goes wrong

| Failure | Fallback |
|---|---|
| Map won't load | Open the **Movers tab** — everything is there in cards |
| Project page 404s | Use the URL bar: `.../project/33INR0005/` (Bullock Gas), `.../project/30INR0110/` (Thunder Bird 1), `.../project/30INR0052/` (Lost Pines) |
| Cloudflare is down | Local: `cd web && npm run preview` then `http://localhost:4322/` |
| Someone asks "how do I get the raw data?" | About tab → JSON API section → all four endpoints listed with curl examples |

---

## Questions judges may ask, with answers

**Q: How is this different from Candid's own product?**  
A: Deliberately narrower. We do GIS only — no cross-source entity resolution, no permit ↔ INR linking, no people. That's Candid's commercial line. This is complementary: a public dashboard on the single most valuable public dataset in Texas grid tracking.

**Q: How would you extend this?**  
A: Same schema pattern extends cleanly to PUCT filings, FERC generator interconnection reports, and TCEQ air permits. The `diffs` table is the interesting primitive — anywhere there's a monthly public snapshot with unique IDs, this approach works. Cross-source entity resolution is the next step but it's a much harder problem, and it's Candid's turf.

**Q: What's the biggest thing you'd fix given more time?**  
A: County-level coordinates for markers are approximate — the map dots sit at county centroids, not actual project locations. ERCOT publishes only the county in the public report; getting to actual coordinates would require cross-referencing the "POI Location" text (which describes the substation) with a substation database like EIA's.

**Q: How do you handle the ERCOT report changing format?**  
A: The ETL locates the header row dynamically (searches for the "INR" cell) rather than hardcoding an offset. If ERCOT changes column names, the rename maps in `etl.py` need updating and that's it. We tested against 31 monthly snapshots spanning 2024–2026 and the format has been stable.

**Q: Why gas plants named "CleanAI" — you sure that's real?**  
A: Verified against the raw ERCOT July 2026 Excel file, row for INR filed this quarter. Filed by "CleanAI, LLC" for two projects called "Three Canes Gas P1" and "Three Canes Gas P2" in Freestone County. Capacity field is blank (developer hasn't disclosed yet — common for early-stage filings). Freestone County has existing coal-to-gas conversion activity and is on major transmission, so the site makes sense for load.
