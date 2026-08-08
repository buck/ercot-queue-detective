#!/usr/bin/env python3
"""
ERCOT GIS Queue Detective — ETL
Idempotent: load-snapshot → recompute-projects → recompute-diffs
"""

import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/db/ercot_queue.db")
CENTROIDS_CSV = Path("data/county_centroids.csv")

# GIM Study Phase → ordinal (higher = more advanced)
PHASE_ORDER = {
    "SS Started, FIS Started, No IA": 1,
    "SS Completed, FIS Not Started, No IA": 2,
    "SS Completed, FIS Not Started, IA": 3,
    "SS Completed, FIS Started, No IA": 4,
    "SS Completed, FIS Started, IA": 5,
    "SS Completed, FIS Completed, No IA": 6,
    "SS Completed, FIS Completed, IA": 7,
}

FUEL_LABELS = {
    "SOL": "Solar",
    "WIN": "Wind",
    "GAS": "Gas",
    "NUC": "Nuclear",
    "OTH": "Other/BESS",
    "WAT": "Hydro",
    "OIL": "Oil/Other",
    "COA": "Coal",
}


# ---------------------------------------------------------------------------
# Filename → snapshot date
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def snapshot_date_from_filename(path: Path) -> date | None:
    stem = path.stem.lower()
    # e.g. gis_report_july2026  /  gis_report_july_2026  /  gis_report_april_2022_corrected
    m = re.search(r"([a-z]+)_?(\d{4})", stem)
    if not m:
        return None
    month_str, year_str = m.group(1), m.group(2)
    month = _MONTH_MAP.get(month_str)
    if not month:
        return None
    return date(int(year_str), month, 1)


# ---------------------------------------------------------------------------
# Excel parsing
# ---------------------------------------------------------------------------

def _find_header_row(df_raw: pd.DataFrame) -> int | None:
    """Return 0-indexed row where 'INR' appears in column 0."""
    for i, row in df_raw.iterrows():
        if str(row.iloc[0]).strip() == "INR":
            return i
    return None


def _parse_large_gen(xl: pd.ExcelFile, snap_date: date) -> pd.DataFrame:
    df_raw = xl.parse("Project Details - Large Gen", header=None)
    hdr = _find_header_row(df_raw)
    if hdr is None:
        return pd.DataFrame()
    df = xl.parse("Project Details - Large Gen", header=hdr)
    # Drop sub-header rows: keep only rows where INR matches pattern
    df = df[df["INR"].astype(str).str.match(r"\d+INR", na=False)].copy()
    df = df.rename(columns={
        "Capacity (MW)": "capacity_mw",
        "GIM Study Phase": "gim_study_phase",
        "Interconnecting Entity": "interconnecting_entity",
        "Project Name": "project_name",
        "POI Location": "poi_location",
        "County": "county",
        "CDR Reporting Zone": "cdr_zone",
        "Projected COD": "projected_cod",
        "Fuel": "fuel",
        "Technology": "technology",
        "Screening Study Started": "ss_started",
        "Screening Study Complete": "ss_complete",
        "FIS Requested": "fis_requested",
        "FIS Approved": "fis_approved",
        "Economic Study Required": "economic_study_required",
        "IA Signed": "ia_signed",
        "Air Permit": "air_permit",
        "GHG Permit": "ghg_permit",
        "Water Availability": "water_availability",
        "Construction Start": "construction_start",
        "Construction End": "construction_end",
        "Approved for Energization": "approved_energization",
        "Approved for Synchronization": "approved_synchronization",
        "Comment": "comment",
        "INR": "inr",
    })
    df["source_type"] = "LARGE"
    df["snapshot_date"] = snap_date.isoformat()
    return df


def _parse_small_gen(xl: pd.ExcelFile, snap_date: date) -> pd.DataFrame:
    df_raw = xl.parse("Project Details - Small Gen", header=None)
    hdr = _find_header_row(df_raw)
    if hdr is None:
        return pd.DataFrame()
    df = xl.parse("Project Details - Small Gen", header=hdr)
    df = df[df["INR"].astype(str).str.match(r"\d+INR", na=False)].copy()
    df = df.rename(columns={
        "Capacity (MW)": "capacity_mw",
        "Model Ready Date": "gim_study_phase",  # Small Gen uses Model Ready Date
        "Interconnecting Entity": "interconnecting_entity",
        "Project Name": "project_name",
        "POI Location": "poi_location",
        "County": "county",
        "CDR Reporting Zone": "cdr_zone",
        "Projected COD": "projected_cod",
        "Fuel": "fuel",
        "Technology": "technology",
        "INR": "inr",
    })
    df["source_type"] = "SMALL"
    df["snapshot_date"] = snap_date.isoformat()
    return df


def _coerce_date_col(series: pd.Series) -> pd.Series:
    def _safe(v):
        if pd.isna(v):
            return None
        if isinstance(v, (datetime, pd.Timestamp)):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        try:
            return pd.to_datetime(v).date().isoformat()
        except Exception:
            return None
    return series.map(_safe)


DATE_COLS = [
    "projected_cod", "ss_started", "ss_complete", "fis_requested", "fis_approved",
    "economic_study_required", "ia_signed", "air_permit", "ghg_permit",
    "water_availability", "construction_start", "construction_end",
    "approved_energization", "approved_synchronization",
]


def load_file(path: Path, snap_date: date) -> pd.DataFrame:
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheets = xl.sheet_names
    frames = []
    if "Project Details - Large Gen" in sheets:
        frames.append(_parse_large_gen(xl, snap_date))
    if "Project Details - Small Gen" in sheets:
        frames.append(_parse_small_gen(xl, snap_date))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)

    # Coerce date columns
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = _coerce_date_col(df[col])

    # For gim_study_phase: coerce only Timestamp/datetime cells (Small Gen Model Ready Date),
    # leave plain strings (Large Gen phase text) untouched
    if "gim_study_phase" in df.columns:
        df["gim_study_phase"] = df["gim_study_phase"].apply(
            lambda v: _coerce_date_col(pd.Series([v])).iloc[0]
            if isinstance(v, (datetime, pd.Timestamp))
            else v
        )

    # Coerce capacity
    if "capacity_mw" in df.columns:
        df["capacity_mw"] = pd.to_numeric(df["capacity_mw"], errors="coerce")

    # Clean text
    for col in ["county", "fuel", "technology", "cdr_zone", "project_name", "interconnecting_entity"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", None)

    # Final sweep: convert any remaining Timestamp/datetime to ISO strings so SQLite is happy
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: v.date().isoformat() if isinstance(v, (datetime, pd.Timestamp)) else v
            )

    return df


# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS gis_snapshot (
    snapshot_date   TEXT NOT NULL,
    inr             TEXT NOT NULL,
    source_type     TEXT,
    project_name    TEXT,
    gim_study_phase TEXT,
    interconnecting_entity TEXT,
    poi_location    TEXT,
    county          TEXT,
    cdr_zone        TEXT,
    projected_cod   TEXT,
    fuel            TEXT,
    technology      TEXT,
    capacity_mw     REAL,
    ss_started      TEXT,
    ss_complete     TEXT,
    fis_requested   TEXT,
    fis_approved    TEXT,
    economic_study_required TEXT,
    ia_signed       TEXT,
    air_permit      TEXT,
    ghg_permit      TEXT,
    water_availability TEXT,
    construction_start TEXT,
    construction_end   TEXT,
    approved_energization TEXT,
    approved_synchronization TEXT,
    comment         TEXT,
    PRIMARY KEY (snapshot_date, inr)
);

CREATE TABLE IF NOT EXISTS projects (
    inr                    TEXT PRIMARY KEY,
    project_name           TEXT,
    gim_study_phase        TEXT,
    phase_ordinal          INTEGER,
    interconnecting_entity TEXT,
    poi_location           TEXT,
    county                 TEXT,
    lat                    REAL,
    lon                    REAL,
    cdr_zone               TEXT,
    projected_cod          TEXT,
    fuel                   TEXT,
    fuel_label             TEXT,
    technology             TEXT,
    capacity_mw            REAL,
    source_type            TEXT,
    latest_snapshot_date   TEXT,
    ia_signed              TEXT,
    construction_start     TEXT,
    construction_end       TEXT,
    approved_synchronization TEXT,
    ss_started             TEXT,
    ss_complete            TEXT,
    fis_requested          TEXT,
    fis_approved           TEXT
);

CREATE TABLE IF NOT EXISTS project_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inr         TEXT NOT NULL,
    event_date  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT
);

CREATE TABLE IF NOT EXISTS diffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    from_snapshot   TEXT NOT NULL,
    to_snapshot     TEXT NOT NULL,
    inr             TEXT NOT NULL,
    change_type     TEXT NOT NULL,
    detail          TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_date TEXT PRIMARY KEY,
    row_count     INTEGER,
    loaded_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshot_date ON gis_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_project_county ON projects(county);
CREATE INDEX IF NOT EXISTS idx_project_fuel ON projects(fuel);
CREATE INDEX IF NOT EXISTS idx_diffs_to_snapshot ON diffs(to_snapshot);
CREATE INDEX IF NOT EXISTS idx_diffs_inr ON diffs(inr);
CREATE INDEX IF NOT EXISTS idx_history_inr ON project_history(inr);
"""


def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.commit()


# ---------------------------------------------------------------------------
# Upsert snapshot
# ---------------------------------------------------------------------------

SNAPSHOT_COLS = [
    "snapshot_date", "inr", "source_type", "project_name", "gim_study_phase",
    "interconnecting_entity", "poi_location", "county", "cdr_zone", "projected_cod",
    "fuel", "technology", "capacity_mw", "ss_started", "ss_complete", "fis_requested",
    "fis_approved", "economic_study_required", "ia_signed", "air_permit", "ghg_permit",
    "water_availability", "construction_start", "construction_end",
    "approved_energization", "approved_synchronization", "comment",
]


def upsert_snapshot(conn: sqlite3.Connection, df: pd.DataFrame, snap_date: date):
    snap_str = snap_date.isoformat()
    # Check if already loaded
    row = conn.execute(
        "SELECT snapshot_date FROM snapshots WHERE snapshot_date = ?", (snap_str,)
    ).fetchone()
    if row:
        print(f"  [skip] {snap_str} already loaded")
        return

    # Align columns
    for col in SNAPSHOT_COLS:
        if col not in df.columns:
            df[col] = None
    df_insert = df[SNAPSHOT_COLS].copy()
    df_insert = df_insert.where(pd.notna(df_insert), None)

    rows = [tuple(r) for r in df_insert.itertuples(index=False)]
    placeholders = ", ".join(["?"] * len(SNAPSHOT_COLS))
    conn.executemany(
        f"INSERT OR REPLACE INTO gis_snapshot ({', '.join(SNAPSHOT_COLS)}) VALUES ({placeholders})",
        rows,
    )
    conn.execute(
        "INSERT INTO snapshots VALUES (?, ?, ?)",
        (snap_str, len(rows), datetime.utcnow().isoformat()),
    )
    conn.commit()
    print(f"  [load] {snap_str}: {len(rows)} rows")


# ---------------------------------------------------------------------------
# Rebuild projects table
# ---------------------------------------------------------------------------

def rebuild_projects(conn: sqlite3.Connection, centroids: dict[str, tuple[float, float]]):
    conn.execute("DELETE FROM projects")
    # Get latest snapshot date
    latest = conn.execute(
        "SELECT snapshot_date FROM snapshots ORDER BY snapshot_date DESC LIMIT 1"
    ).fetchone()
    if not latest:
        return
    snap_str = latest[0]

    df = pd.read_sql(
        "SELECT * FROM gis_snapshot WHERE snapshot_date = ?", conn, params=(snap_str,)
    )
    if df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        county = str(r.get("county") or "").strip()
        lat, lon = centroids.get(county, (None, None))
        phase = str(r.get("gim_study_phase") or "").strip()
        phase_ord = PHASE_ORDER.get(phase, 0)
        fuel = str(r.get("fuel") or "").strip()
        rows.append((
            r["inr"], r.get("project_name"), phase, phase_ord,
            r.get("interconnecting_entity"), r.get("poi_location"),
            county, lat, lon, r.get("cdr_zone"), r.get("projected_cod"),
            fuel, FUEL_LABELS.get(fuel, fuel),
            r.get("technology"), r.get("capacity_mw"),
            r.get("source_type"), snap_str,
            r.get("ia_signed"), r.get("construction_start"),
            r.get("construction_end"), r.get("approved_synchronization"),
            r.get("ss_started"), r.get("ss_complete"),
            r.get("fis_requested"), r.get("fis_approved"),
        ))

    conn.executemany(
        """INSERT INTO projects VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    print(f"  [projects] {len(rows)} projects from {snap_str}")


# ---------------------------------------------------------------------------
# Diff computation
# ---------------------------------------------------------------------------

def _phase_ordinal(phase: str | None) -> int:
    return PHASE_ORDER.get(str(phase or "").strip(), 0)


def compute_diffs(conn: sqlite3.Connection):
    conn.execute("DELETE FROM diffs")
    conn.execute("DELETE FROM project_history")

    dates = [
        r[0]
        for r in conn.execute(
            "SELECT snapshot_date FROM snapshots ORDER BY snapshot_date"
        ).fetchall()
    ]
    if len(dates) < 2:
        print("  [diffs] need at least 2 snapshots — skipping")
        return

    all_diffs = []
    all_history = []

    for i in range(1, len(dates)):
        from_d, to_d = dates[i - 1], dates[i]
        old = pd.read_sql(
            "SELECT * FROM gis_snapshot WHERE snapshot_date = ?", conn, params=(from_d,)
        ).set_index("inr")
        new = pd.read_sql(
            "SELECT * FROM gis_snapshot WHERE snapshot_date = ?", conn, params=(to_d,)
        ).set_index("inr")

        old_inrs = set(old.index)
        new_inrs = set(new.index)

        # NEW
        for inr in new_inrs - old_inrs:
            r = new.loc[inr]
            all_diffs.append((
                from_d, to_d, inr, "NEW",
                f"{r.get('project_name')} | {r.get('fuel')} | {r.get('capacity_mw')} MW",
            ))

        # WITHDRAWN
        for inr in old_inrs - new_inrs:
            r = old.loc[inr]
            all_diffs.append((
                from_d, to_d, inr, "WITHDRAWN",
                f"{r.get('project_name')} | {r.get('fuel')} | {r.get('capacity_mw')} MW",
            ))

        # Changes in projects that exist in both snapshots
        for inr in old_inrs & new_inrs:
            o, n = old.loc[inr], new.loc[inr]

            # Status change
            old_phase, new_phase = o.get("gim_study_phase"), n.get("gim_study_phase")
            if old_phase != new_phase:
                old_ord, new_ord = _phase_ordinal(old_phase), _phase_ordinal(new_phase)
                if new_ord > old_ord:
                    ct = "STATUS_ADVANCED"
                elif new_ord < old_ord:
                    ct = "STATUS_REVERTED"
                else:
                    ct = "STATUS_ADVANCED"  # changed but same level
                all_diffs.append((from_d, to_d, inr, ct, f"{old_phase} → {new_phase}"))
                all_history.append((inr, to_d, "gim_study_phase", str(old_phase), str(new_phase)))

            # COD change
            old_cod, new_cod = o.get("projected_cod"), n.get("projected_cod")
            if old_cod and new_cod and old_cod != new_cod:
                try:
                    od, nd = pd.to_datetime(old_cod), pd.to_datetime(new_cod)
                    if nd > od:
                        ct = "COD_SLIPPED"
                    else:
                        ct = "COD_ADVANCED"
                    all_diffs.append((from_d, to_d, inr, ct, f"{old_cod} → {new_cod}"))
                    all_history.append((inr, to_d, "projected_cod", old_cod, new_cod))
                except Exception:
                    pass

            # Capacity change
            old_mw, new_mw = o.get("capacity_mw"), n.get("capacity_mw")
            try:
                old_mw_f, new_mw_f = float(old_mw or 0), float(new_mw or 0)
                if abs(old_mw_f - new_mw_f) > 0.05:
                    all_diffs.append((
                        from_d, to_d, inr, "CAPACITY_CHANGED",
                        f"{old_mw_f:.1f} → {new_mw_f:.1f} MW",
                    ))
                    all_history.append((inr, to_d, "capacity_mw", str(old_mw_f), str(new_mw_f)))
            except (TypeError, ValueError):
                pass

            # Ownership change
            old_ie, new_ie = o.get("interconnecting_entity"), n.get("interconnecting_entity")
            if (
                old_ie and new_ie
                and str(old_ie).strip() != str(new_ie).strip()
                and str(old_ie).strip() not in ("nan", "None")
                and str(new_ie).strip() not in ("nan", "None")
            ):
                all_diffs.append((
                    from_d, to_d, inr, "OWNERSHIP_CHANGED",
                    f"{old_ie} → {new_ie}",
                ))
                all_history.append((inr, to_d, "interconnecting_entity", str(old_ie), str(new_ie)))

    if all_diffs:
        conn.executemany(
            "INSERT INTO diffs (from_snapshot, to_snapshot, inr, change_type, detail) VALUES (?,?,?,?,?)",
            all_diffs,
        )
    if all_history:
        conn.executemany(
            "INSERT INTO project_history (inr, event_date, field, old_value, new_value) VALUES (?,?,?,?,?)",
            all_history,
        )
    conn.commit()
    print(f"  [diffs] {len(all_diffs)} diffs, {len(all_history)} history events")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_centroids() -> dict[str, tuple[float, float]]:
    df = pd.read_csv(CENTROIDS_CSV)
    return {row["county"]: (row["lat"], row["lon"]) for _, row in df.iterrows()}


def main(files: list[Path] | None = None):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    centroids = load_centroids()

    if files is None:
        # Default: all files in raw dir, sorted by date
        files = sorted(RAW_DIR.glob("GIS_Report_*.xlsx"))

    loaded = 0
    for path in files:
        snap_date = snapshot_date_from_filename(path)
        if snap_date is None:
            print(f"  [skip] cannot parse date from {path.name}")
            continue
        print(f"Loading {path.name} → {snap_date}")
        df = load_file(path, snap_date)
        if df.empty:
            print(f"  [warn] empty dataframe for {path.name}")
            continue
        upsert_snapshot(conn, df, snap_date)
        loaded += 1

    print(f"\nLoaded {loaded} snapshots. Rebuilding derived tables...")
    rebuild_projects(conn, centroids)
    compute_diffs(conn)
    print("\nDone.")
    conn.close()


if __name__ == "__main__":
    # Accept optional list of filenames as args
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        paths = None
    main(paths)
