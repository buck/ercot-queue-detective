#!/usr/bin/env python3
"""
ERCOT GIS Queue Detective — FastAPI JSON API
Run: uvicorn api:app --reload
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

DB_PATH = Path("data/db/ercot_queue.db")

app = FastAPI(title="ERCOT Queue Detective", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# /api/projects — filterable project list with coordinates
# ---------------------------------------------------------------------------

@app.get("/api/projects")
def list_projects(
    fuel: Optional[str] = Query(None, description="Fuel code: SOL, WIN, GAS, OTH, etc."),
    county: Optional[str] = Query(None),
    cdr_zone: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="GIM Study Phase substring"),
    min_mw: Optional[float] = Query(None),
    max_mw: Optional[float] = Query(None),
    changed_since: Optional[str] = Query(None, description="ISO date, e.g. 2026-06-01"),
    change_type: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None, description="LARGE or SMALL"),
    limit: int = Query(5000, le=10000),
):
    clauses = []
    params: list = []

    if fuel:
        clauses.append("p.fuel = ?")
        params.append(fuel.upper())
    if county:
        clauses.append("p.county = ?")
        params.append(county)
    if cdr_zone:
        clauses.append("p.cdr_zone = ?")
        params.append(cdr_zone)
    if status:
        clauses.append("p.gim_study_phase LIKE ?")
        params.append(f"%{status}%")
    if min_mw is not None:
        clauses.append("p.capacity_mw >= ?")
        params.append(min_mw)
    if max_mw is not None:
        clauses.append("p.capacity_mw <= ?")
        params.append(max_mw)
    if source_type:
        clauses.append("p.source_type = ?")
        params.append(source_type.upper())

    if changed_since or change_type:
        join = "INNER JOIN diffs d ON p.inr = d.inr AND d.to_snapshot = p.latest_snapshot_date"
        if changed_since:
            clauses.append("d.to_snapshot >= ?")
            params.append(changed_since)
        if change_type:
            clauses.append("d.change_type = ?")
            params.append(change_type.upper())
    else:
        join = ""

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT DISTINCT p.inr, p.project_name, p.gim_study_phase, p.phase_ordinal,
               p.interconnecting_entity, p.poi_location, p.county, p.lat, p.lon, p.cdr_zone,
               p.projected_cod, p.fuel, p.fuel_label, p.technology, p.capacity_mw,
               p.source_type, p.latest_snapshot_date, p.ia_signed,
               p.construction_start, p.construction_end,
               p.ss_started, p.ss_complete, p.fis_requested, p.fis_approved
        FROM projects p
        {join}
        {where}
        ORDER BY p.capacity_mw DESC NULLS LAST
        LIMIT ?
    """
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return JSONResponse({"count": len(rows), "projects": rows_to_list(rows)})


# ---------------------------------------------------------------------------
# /api/projects/{inr} — single project detail
# ---------------------------------------------------------------------------

@app.get("/api/projects/{inr}")
def get_project(inr: str):
    with get_db() as conn:
        proj = conn.execute("SELECT * FROM projects WHERE inr = ?", (inr,)).fetchone()
        if not proj:
            return JSONResponse({"error": "not found"}, status_code=404)

        history = conn.execute(
            """SELECT event_date, field, old_value, new_value
               FROM project_history WHERE inr = ?
               ORDER BY event_date""",
            (inr,),
        ).fetchall()

        diffs = conn.execute(
            """SELECT from_snapshot, to_snapshot, change_type, detail
               FROM diffs WHERE inr = ?
               ORDER BY to_snapshot""",
            (inr,),
        ).fetchall()

        snap = conn.execute(
            """SELECT * FROM gis_snapshot WHERE inr = ?
               ORDER BY snapshot_date DESC LIMIT 1""",
            (inr,),
        ).fetchone()

    return {
        "project": dict(proj),
        "history": rows_to_list(history),
        "diffs": rows_to_list(diffs),
        "latest_snapshot": dict(snap) if snap else None,
    }


# ---------------------------------------------------------------------------
# /api/movers — top movers in the latest diff period
# ---------------------------------------------------------------------------

@app.get("/api/movers")
def get_movers(
    change_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    with get_db() as conn:
        latest = conn.execute(
            "SELECT MAX(snapshot_date) FROM snapshots"
        ).fetchone()[0]
        prev = conn.execute(
            "SELECT MAX(snapshot_date) FROM snapshots WHERE snapshot_date < ?", (latest,)
        ).fetchone()[0]

        if not prev:
            return {"from_snapshot": None, "to_snapshot": latest, "movers": []}

        clauses = ["d.from_snapshot = ?", "d.to_snapshot = ?"]
        params: list = [prev, latest]
        if change_type:
            clauses.append("d.change_type = ?")
            params.append(change_type.upper())

        sql = f"""
            SELECT d.inr, d.change_type, d.detail,
                   p.project_name, p.fuel, p.fuel_label, p.county, p.capacity_mw,
                   p.lat, p.lon, p.gim_study_phase, p.interconnecting_entity
            FROM diffs d
            LEFT JOIN projects p ON d.inr = p.inr
            WHERE {' AND '.join(clauses)}
            ORDER BY p.capacity_mw DESC NULLS LAST
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()

    return {
        "from_snapshot": prev,
        "to_snapshot": latest,
        "movers": rows_to_list(rows),
    }


# ---------------------------------------------------------------------------
# /api/summary — dashboard stats
# ---------------------------------------------------------------------------

@app.get("/api/summary")
def get_summary():
    with get_db() as conn:
        latest = conn.execute(
            "SELECT MAX(snapshot_date) FROM snapshots"
        ).fetchone()[0]
        prev = conn.execute(
            "SELECT MAX(snapshot_date) FROM snapshots WHERE snapshot_date < ?", (latest,)
        ).fetchone()[0]

        total_mw = conn.execute(
            "SELECT SUM(capacity_mw) FROM projects WHERE source_type = 'LARGE'"
        ).fetchone()[0]
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

        fuel_breakdown = conn.execute(
            """SELECT fuel_label, COUNT(*) as n, SUM(capacity_mw) as total_mw
               FROM projects WHERE source_type = 'LARGE'
               GROUP BY fuel_label ORDER BY total_mw DESC"""
        ).fetchall()

        diff_counts = {}
        if prev:
            for ct in ["NEW", "WITHDRAWN", "STATUS_ADVANCED", "STATUS_REVERTED",
                       "COD_SLIPPED", "COD_ADVANCED", "CAPACITY_CHANGED", "OWNERSHIP_CHANGED"]:
                n = conn.execute(
                    "SELECT COUNT(*) FROM diffs WHERE from_snapshot=? AND to_snapshot=? AND change_type=?",
                    (prev, latest, ct),
                ).fetchone()[0]
                diff_counts[ct] = n

        snapshots = conn.execute(
            "SELECT snapshot_date, row_count FROM snapshots ORDER BY snapshot_date"
        ).fetchall()

    return {
        "latest_snapshot": latest,
        "prev_snapshot": prev,
        "total_projects": total_projects,
        "total_large_gen_mw": round(total_mw or 0, 1),
        "fuel_breakdown": rows_to_list(fuel_breakdown),
        "this_month_changes": diff_counts,
        "snapshots": rows_to_list(snapshots),
    }


# ---------------------------------------------------------------------------
# /api/filters — distinct filter values for the UI
# ---------------------------------------------------------------------------

@app.get("/api/filters")
def get_filters():
    with get_db() as conn:
        fuels = [r[0] for r in conn.execute(
            "SELECT DISTINCT fuel, fuel_label FROM projects WHERE fuel IS NOT NULL ORDER BY fuel_label"
        ).fetchall()]
        zones = [r[0] for r in conn.execute(
            "SELECT DISTINCT cdr_zone FROM projects WHERE cdr_zone IS NOT NULL ORDER BY cdr_zone"
        ).fetchall()]
        counties = [r[0] for r in conn.execute(
            "SELECT DISTINCT county FROM projects WHERE county IS NOT NULL ORDER BY county"
        ).fetchall()]
        phases = [r[0] for r in conn.execute(
            "SELECT DISTINCT gim_study_phase FROM projects WHERE gim_study_phase IS NOT NULL ORDER BY gim_study_phase"
        ).fetchall()]
    return {
        "fuels": fuels,
        "cdr_zones": zones,
        "counties": counties,
        "gim_phases": phases,
    }
