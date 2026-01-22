#!/usr/bin/env python3
"""
Coach Metrics Calculator for Coach Dashboard

Calculates eligibility metrics from cached HubSpot data.
Adapted from conversie-analyse/metric.py

Inputs:
- etl/cache/deals_raw.json
- data/<run_id>/enums.xlsx

Outputs:
- data/mapping.xlsx (shared across runs)
- etl/cache/owners.json
- data/<run_id>/coach_eligibility.xlsx

Run with: python etl/calculate_metrics.py [run_id]
"""

from __future__ import annotations

import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import pandas as pd
import requests

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
DATA_DIR = PROJECT_ROOT / "data"

# Config
PIPELINE_STATUS_BEGELEIDING = "15413220"
PIPELINE_NABELLER = "38341389"
STAGE_TIJDELIJK_STOPPEN = "15413630"

SMOOTHING_ALPHA = 3
SMOOTHING_BETA = 5

BASE_URL = "https://api.hubapi.com"


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dirs(run_id: str = None) -> Path:
    """Ensure directories exist. Returns run output dir if run_id provided."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if run_id:
        run_dir = DATA_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    return DATA_DIR


def get_latest_run_dir() -> Optional[Path]:
    """Find the most recent run directory."""
    if not DATA_DIR.is_dir():
        return None

    # Look for directories that match run_id pattern (YYYYMMDD_HHMMSS)
    run_dirs = [d for d in DATA_DIR.iterdir()
                if d.is_dir() and len(d.name) == 15 and "_" in d.name]

    if not run_dirs:
        return None

    run_dirs.sort(key=lambda p: p.name, reverse=True)
    return run_dirs[0]


def file_nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 10


def load_dotenv(path: Path = None) -> None:
    if path is None:
        path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


def parse_bool_str(v: Any) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y")


def parse_iso(dt: Any) -> Optional[datetime]:
    if not dt:
        return None
    s = str(dt).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None


def safe_str(v: Any) -> str:
    return "" if v is None else str(v)


def extract_stage_meta(meta_json: Any) -> Tuple[Optional[bool], Optional[float]]:
    if meta_json is None or (isinstance(meta_json, float) and pd.isna(meta_json)):
        return (None, None)
    try:
        if isinstance(meta_json, str):
            d = json.loads(meta_json)
        elif isinstance(meta_json, dict):
            d = meta_json
        else:
            d = json.loads(str(meta_json))
        is_closed = str(d.get("isClosed", "")).lower() == "true"
        prob = d.get("probability")
        prob_f = float(prob) if prob is not None and str(prob).strip() != "" else None
        return (is_closed, prob_f)
    except Exception:
        return (None, None)


# Owners (coach names)

def hs_headers() -> Dict[str, str]:
    pat = os.environ.get("HUBSPOT_PAT", "").strip()
    if not pat:
        return {}
    return {"Authorization": f"Bearer {pat}"}


def fetch_all_owners() -> Dict[str, str]:
    headers = hs_headers()
    if not headers:
        return {}

    session = requests.Session()
    owners: Dict[str, str] = {}
    after = None

    while True:
        params = {"limit": 500}
        if after:
            params["after"] = after
        url = f"{BASE_URL}/crm/v3/owners/"
        r = session.get(url, headers=headers, params=params, timeout=30)
        if r.status_code >= 400:
            return owners

        data = r.json()
        for o in data.get("results", []):
            oid = safe_str(o.get("id") or o.get("ownerId"))
            first = safe_str(o.get("firstName") or o.get("firstname"))
            last = safe_str(o.get("lastName") or o.get("lastname"))
            name = (first + " " + last).strip()
            if oid:
                owners[oid] = name or oid

        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        after = nxt.get("after")
        time.sleep(0.1)

    return owners


def load_or_fetch_owners(cache_path: Path = None, refresh: bool = False) -> Dict[str, str]:
    if cache_path is None:
        cache_path = CACHE_DIR / "owners.json"

    if not refresh and file_nonempty(cache_path):
        try:
            raw = json.load(open(cache_path, "r", encoding="utf-8"))
            if isinstance(raw, dict):
                return {str(k): str(v) for k, v in raw.items()}
        except Exception:
            pass

    owners = fetch_all_owners()
    if owners:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(owners, f, ensure_ascii=False, indent=2)
    return owners


# Mapping logic

def build_default_stage_mapping(stages_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in stages_df.iterrows():
        pipeline_id = safe_str(r.get("pipeline_id"))
        dealstage_id = safe_str(r.get("dealstage_id"))
        stage_label = safe_str(r.get("stage_label"))
        is_closed, prob = extract_stage_meta(r.get("metadata"))

        if pipeline_id == PIPELINE_NABELLER:
            if is_closed and prob == 1.0:
                cls = "NABELLER_HANDOFF"
            elif is_closed and prob == 0.0:
                cls = "LOST"
            else:
                cls = "OPEN"
        else:
            if dealstage_id == STAGE_TIJDELIJK_STOPPEN:
                cls = "LOST"
            else:
                if is_closed and prob == 1.0:
                    cls = "WON"
                elif is_closed and prob == 0.0:
                    cls = "LOST"
                else:
                    cls = "OPEN"

        rows.append({
            "pipeline_id": pipeline_id,
            "dealstage_id": dealstage_id,
            "stage_label": stage_label,
            "is_closed": is_closed,
            "probability": prob,
            "class": cls,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["pipeline_id", "probability", "dealstage_id"], ascending=[True, False, True])
    return df


def load_mapping(mapping_path: Path) -> Dict[Tuple[str, str], str]:
    df = pd.read_excel(mapping_path, sheet_name="stage_mapping")
    mapping: Dict[Tuple[str, str], str] = {}
    for _, r in df.iterrows():
        key = (safe_str(r.get("pipeline_id")), safe_str(r.get("dealstage_id")))
        cls = safe_str(r.get("class")).strip().upper()
        if not cls:
            continue
        mapping[key] = cls
    return mapping


# Metrics

def compute_metrics(deals_df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    periods = {
        "1m": now - timedelta(days=30),
        "3m": now - timedelta(days=90),
        "6m": now - timedelta(days=180),
    }

    out_rows = []
    coach_ids = sorted(set(deals_df["coach_id"].dropna().astype(str).tolist()))

    for coach_id in coach_ids:
        row_base = {"coach_id": coach_id}
        coach_deals_all = deals_df[deals_df["coach_id"] == coach_id]

        for p_name, start_dt in periods.items():
            dd = coach_deals_all[coach_deals_all["created_dt"] >= start_dt]

            total = int(len(dd))
            won = int((dd["class"] == "WON").sum())
            lost = int((dd["class"] == "LOST").sum())
            open_ = int((dd["class"] == "OPEN").sum())

            nabeller_now = int((dd["pipeline"] == PIPELINE_NABELLER).sum())
            handoff = int((dd["class"] == "NABELLER_HANDOFF").sum())

            rate = (won / total * 100.0) if total else 0.0
            smoothed = ((won + SMOOTHING_ALPHA) / (total + SMOOTHING_BETA) * 100.0) if (total + SMOOTHING_BETA) else 0.0
            nabeller_pct = (nabeller_now / total * 100.0) if total else 0.0

            row_base.update({
                f"deals_{p_name}": total,
                f"won_{p_name}": won,
                f"lost_{p_name}": lost,
                f"open_{p_name}": open_,
                f"rate_{p_name}": round(rate, 1),
                f"smoothed_{p_name}": round(smoothed, 1),
                f"nabeller_now_{p_name}": nabeller_now,
                f"nabeller_pct_{p_name}": round(nabeller_pct, 1),
                f"handoff_{p_name}": handoff,
            })

        out_rows.append(row_base)

    return pd.DataFrame(out_rows)


def determine_eligibility(metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = metrics_df.copy()

    eligible_pool = df[df["deals_1m"] > 5]["smoothed_1m"].tolist()
    p50 = 0.0
    if eligible_pool:
        eligible_pool_sorted = sorted(eligible_pool)
        p50 = float(eligible_pool_sorted[len(eligible_pool_sorted) // 2])

    elig = []
    for _, r in df.iterrows():
        total_1m = int(r.get("deals_1m", 0))
        open_1m = int(r.get("open_1m", 0))
        sm_1m = float(r.get("smoothed_1m", 0.0))
        nab_pct = float(r.get("nabeller_pct_1m", 0.0))

        if total_1m == 0:
            label = "Geen data"
        elif nab_pct > 20.0:
            label = "⚠️ Uitsluiten"
        elif sm_1m >= p50 and open_1m >= 5:
            label = "✅ Goed"
        elif sm_1m > 20.0 and 3 <= open_1m <= 9:
            label = "⭐ Matig"
        else:
            label = "❌ Uitsluiten"

        elig.append(label)

    df["eligibility"] = elig
    df["p50_smoothed_1m"] = round(p50, 1)

    order = {"✅ Goed": 0, "⭐ Matig": 1, "⚠️ Uitsluiten": 2, "❌ Uitsluiten": 3, "Geen data": 4}
    df["_sort"] = df["eligibility"].map(lambda x: order.get(x, 99))
    df = df.sort_values(by=["_sort", "rate_1m"], ascending=[True, False]).drop(columns=["_sort"])

    return df


def calculate_for_run(target_run_id: str, refresh_owners: bool = False) -> Path:
    """Calculate metrics for a specific run. Returns path to output file."""
    run_dir = DATA_DIR / target_run_id
    if not run_dir.is_dir():
        raise RuntimeError(f"Run directory not found: {run_dir}")

    enums_path = run_dir / "enums.xlsx"
    if not enums_path.is_file():
        raise RuntimeError(f"Enums file not found: {enums_path}")

    deals_path = CACHE_DIR / "deals_raw.json"
    if not file_nonempty(deals_path):
        raise RuntimeError(f"Missing {deals_path}. Run fetch_hubspot.py first.")

    print(f"Calculating metrics for run: {target_run_id}")
    print(f"Using enums: {enums_path}")

    stages_df = pd.read_excel(enums_path, sheet_name="Stages")

    # Mapping is shared across runs
    mapping_path = DATA_DIR / "mapping.xlsx"
    if not mapping_path.is_file():
        mapping_df = build_default_stage_mapping(stages_df)
        with pd.ExcelWriter(mapping_path, engine="openpyxl") as w:
            mapping_df.to_excel(w, sheet_name="stage_mapping", index=False)
        print(f"Created default mapping: {mapping_path}")

    stage_map = load_mapping(mapping_path)

    deals_raw = json.load(open(deals_path, "r", encoding="utf-8"))

    rows = []
    for d in deals_raw:
        props = d.get("properties", {}) or {}
        deal_id = safe_str(d.get("id"))
        coach_id = safe_str(props.get("hubspot_owner_id"))
        pipeline = safe_str(props.get("pipeline"))
        dealstage = safe_str(props.get("dealstage"))

        created_dt = parse_iso(props.get("createdate"))
        if created_dt is None:
            continue

        cls = stage_map.get((pipeline, dealstage), "")
        if not cls:
            is_lost = parse_bool_str(props.get("hs_is_closed_lost"))
            is_won = parse_bool_str(props.get("hs_is_closed_won"))
            if dealstage == STAGE_TIJDELIJK_STOPPEN:
                cls = "LOST"
            elif pipeline == PIPELINE_NABELLER and is_won:
                cls = "NABELLER_HANDOFF"
            elif is_lost:
                cls = "LOST"
            elif is_won:
                cls = "WON"
            else:
                cls = "OPEN"

        if dealstage == STAGE_TIJDELIJK_STOPPEN:
            cls = "LOST"

        rows.append({
            "deal_id": deal_id,
            "coach_id": coach_id if coach_id else "UNKNOWN",
            "pipeline": pipeline,
            "dealstage": dealstage,
            "class": cls,
            "created_dt": created_dt,
        })

    deals_df = pd.DataFrame(rows)
    if deals_df.empty:
        raise RuntimeError("No deals after parsing deals_raw.json")

    metrics_df = compute_metrics(deals_df)
    final_df = determine_eligibility(metrics_df)

    # Owners enrichment
    owners = load_or_fetch_owners(refresh=refresh_owners)
    if owners:
        final_df.insert(1, "Coachnaam", final_df["coach_id"].astype(str).map(lambda x: owners.get(x, "UNKNOWN")))
    else:
        final_df.insert(1, "Coachnaam", "UNKNOWN")

    # Save to run directory
    out_path = run_dir / "coach_eligibility.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        final_df.to_excel(w, sheet_name="Coaches", index=False)
        summary = deals_df.groupby(["pipeline", "class"]).size().reset_index(name="count")
        summary.to_excel(w, sheet_name="DealClassSummary", index=False)
        if owners:
            owners_df = pd.DataFrame([{"coach_id": k, "Coachnaam": v} for k, v in sorted(owners.items())])
            owners_df.to_excel(w, sheet_name="Owners", index=False)

    print(f"\nOK: wrote {out_path}")
    print(f"Mapping used: {mapping_path}")
    print(f"Coaches: {len(final_df)}")

    # Write deals_flat.csv for Week Monitor
    deals_flat_path = write_deals_flat_csv(deals_df, owners, run_dir)
    print(f"Deals flat: {deals_flat_path}")

    return out_path


def write_deals_flat_csv(deals_df: pd.DataFrame, owners: Dict[str, str], run_dir: Path) -> Path:
    """
    Write a flat CSV of all deals for the Week Monitor.

    Columns:
    - deal_id
    - coach_id
    - Coachnaam
    - created_dt (ISO string)
    - pipeline
    - class (WON/LOST/OPEN/NABELLER_HANDOFF)
    """
    flat_df = deals_df[["deal_id", "coach_id", "pipeline", "class", "created_dt"]].copy()

    # Add coach name
    if owners:
        flat_df["Coachnaam"] = flat_df["coach_id"].map(lambda x: owners.get(str(x), "UNKNOWN"))
    else:
        flat_df["Coachnaam"] = "UNKNOWN"

    # Convert datetime to ISO string
    flat_df["created_dt"] = flat_df["created_dt"].apply(
        lambda dt: dt.isoformat() if pd.notna(dt) else ""
    )

    # Reorder columns
    flat_df = flat_df[["deal_id", "coach_id", "Coachnaam", "created_dt", "pipeline", "class"]]

    out_path = run_dir / "deals_flat.csv"
    flat_df.to_csv(out_path, index=False, encoding="utf-8")

    return out_path


def main() -> None:
    ensure_dirs()
    load_dotenv()

    # Get run_id from command line or find latest
    if len(sys.argv) > 1:
        target_run_id = sys.argv[1]
    else:
        latest_dir = get_latest_run_dir()
        if not latest_dir:
            raise RuntimeError("No run directories found. Run fetch_hubspot.py first.")
        target_run_id = latest_dir.name

    calculate_for_run(target_run_id)


if __name__ == "__main__":
    main()
