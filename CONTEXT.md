# Context for Saturday's Claude — extracted user memory

This file is a project-scoped snapshot of the subset of the user's persistent memory that matters for the ERCOT Queue Detective build. The desktop has a full memory system at `~/.claude/projects/-home-buck/memory/`; on the laptop it will be empty. Read this instead.

---

## User conventions

### System
- **Laptop OS:** NixOS (fresh install pre-hackathon). Config lives in `/etc/nixos/configuration.nix`. Passwordless sudo.
- **Missing tools:** add to `environment.systemPackages` in `configuration.nix` and `sudo nixos-rebuild switch`. Do NOT reach for `nix-shell` — user prefers the declarative path.
- **NixOS installer quirk:** 25.11 ISO needs `NIX_CONFIG=flakes` even to install non-flake configs. User has internalized this; noting for reference.
- **Editor:** VS Code. Not Cursor, not another AI IDE.
- **Remote-access idiom:** user often SSHes in from Windows Terminal. WT eats Ctrl+V — if a keyboard shortcut acts weird over SSH, suspect the terminal client first, not dotfiles.

### Python packaging
- **Default:** `uv`-managed venv per project. Include venv creation/activation in proposals.
- **Exception:** for systemd services on NixOS, use `python3.withPackages` in `configuration.nix`. This hackathon build is *not* a service — stick with `uv`.

### Git
- **Commit email:** `buck@compact.com` (not the account email `anthropic-reg@nbolt.com`).

### Secrets
- Plaintext API keys have historically leaked into `~/.profile`. Don't repeat that. Use gitignored `.env` or the OS keyring for anything sensitive in this project.

### Notifications (only if wiring optional alerts)
- Desktop uses `ntfy.sh/albiii` for cross-device push. Growl is retired.

---

## Reusable patterns from prior public-data projects

The user has shipped several public-data pipelines. The ERCOT build inherits their shapes; don't re-derive from scratch.

### Ideabrowser scraper (working since 2026-07-11)
- Scheduled scrape + Uptime Kuma health monitor.
- **Takeaway:** GH Actions cron + a simple healthcheck ping is a solved pattern here — mirror it.

### FFIEC pipeline
- `ffiec.gov` runs a WAF that blocks `python requests`. Use `curl` via `subprocess` with a normal User-Agent.
- **Takeaway for ERCOT:** if downloading the GIS Excel returns 403/406/1020 or hangs, jump straight to `curl` before assuming the URL moved.

### Houston SPCA fosters scraper
- Cloudflare blocks `axios`; use `curl` via subprocess.
- Same lesson as FFIEC — WAF-fronted public sites need a real-browser-shaped request.

### Houston civicdata (adopt-a-drain)
- PostGIS pipeline: 129,989 storm inlets ingested; change map computed against a 2016 CSV baseline.
- **Takeaway:** the "point features + diff vs prior baseline" shape is *exactly* the ERCOT queue detective pattern. User has done this before; the map + diff view is not a novel problem.

### DoD J-books pipeline
- Phases 1–4 done 2026-07-18. 91.8% link precision on citation resolution.
- **Takeaway:** "messy federal public data → structured DB with every fact traced back to source filing" — the source-citation discipline the ERCOT build should inherit.

### CMS Medicare platform
- 1840-coord dict + Care Compare nursing-home quality data; 22-tool MCP server; PE-SNF demo.
- **Takeaway:** shows the user has already done "public data → structured DB → tool layer for LLM." If the hackathon build gets a stretch "ask a question" box, this is the reference architecture.

---

## Ethos

Experienced operator on public-data ETL. Move fast, reuse patterns, skip fundamentals explanations. Ask before destructive git / filesystem ops on the fresh repo (confirmation cost is low, work-loss cost is high). End-of-turn updates: 1–2 sentences — what changed, what's next.
