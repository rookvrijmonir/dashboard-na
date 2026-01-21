#!/usr/bin/env python3
"""
Refresh Coach Dashboard Data

One-command script to fetch fresh data from HubSpot and calculate metrics.

Usage:
    python refresh_data.py              # Use cached data where possible
    python refresh_data.py --refresh    # Refresh all data from HubSpot

Requirements:
    - .env file with HUBSPOT_PAT=your_token
    - pip install requests pandas openpyxl
"""

import subprocess
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"


def run_script(script_path: Path, args: list = None) -> tuple:
    """Run a Python script and return (success, output)."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0, result.stdout


def update_runs_json(run_id: str):
    """Update runs.json to include new run and select it."""
    runs_file = DATA_DIR / "runs.json"

    if runs_file.is_file():
        with open(runs_file, "r") as f:
            runs_data = json.load(f)
    else:
        runs_data = {"runs": [], "selected": None}

    # Check if run already exists
    existing_ids = [r["run_id"] for r in runs_data["runs"]]
    if run_id not in existing_ids:
        runs_data["runs"].insert(0, {
            "run_id": run_id,
            "folder": str(DATA_DIR / run_id),
            "datetime": f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}T{run_id[9:11]}:{run_id[11:13]}:{run_id[13:15]}",
            "datetime_display": f"{run_id[6:8]}-{run_id[4:6]}-{run_id[:4]} {run_id[9:11]}:{run_id[11:13]}:{run_id[13:15]}",
            "date_display": f"{run_id[6:8]}-{run_id[4:6]}-{run_id[:4]}",
            "time_display": f"{run_id[9:11]}:{run_id[11:13]}:{run_id[13:15]}",
            "coach_count": None,
            "has_enums": True
        })

    runs_data["selected"] = run_id

    with open(runs_file, "w") as f:
        json.dump(runs_data, f, indent=2)


def main():
    # Check for .env
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        print("ERROR: No .env file found!")
        print(f"Create {env_file} with:")
        print("  HUBSPOT_PAT=your_hubspot_token")
        sys.exit(1)

    # Parse args
    refresh_all = "--refresh" in sys.argv or "-r" in sys.argv
    refresh_arg = ["--refresh", "all"] if refresh_all else []

    # Step 1: Fetch from HubSpot
    fetch_script = PROJECT_ROOT / "etl" / "fetch_hubspot.py"
    if not fetch_script.is_file():
        print(f"ERROR: {fetch_script} not found!")
        sys.exit(1)

    success, output = run_script(fetch_script, refresh_arg)
    if not success:
        print("\nERROR: Fetch failed!")
        sys.exit(1)

    # Extract run_id from output
    run_id = None
    for line in output.split("\n"):
        if "Run ID:" in line:
            run_id = line.split("Run ID:")[-1].strip()
            break
        if "Output folder:" in line and "data/" in line:
            # Extract from path like "data/20260121_195256/"
            parts = line.split("data/")[-1].strip().rstrip("/")
            if len(parts) == 15 and "_" in parts:
                run_id = parts
                break

    if not run_id:
        # Try to find latest run folder
        run_dirs = [d for d in DATA_DIR.iterdir()
                    if d.is_dir() and len(d.name) == 15 and "_" in d.name]
        if run_dirs:
            run_dirs.sort(key=lambda p: p.name, reverse=True)
            run_id = run_dirs[0].name

    if not run_id:
        print("\nERROR: Could not determine run_id!")
        sys.exit(1)

    print(f"\nRun ID: {run_id}")

    # Step 2: Calculate metrics
    metrics_script = PROJECT_ROOT / "etl" / "calculate_metrics.py"
    if not metrics_script.is_file():
        print(f"ERROR: {metrics_script} not found!")
        sys.exit(1)

    success, _ = run_script(metrics_script, [run_id])
    if not success:
        print("\nERROR: Metrics calculation failed!")
        sys.exit(1)

    # Update runs.json
    update_runs_json(run_id)

    # Done
    print("\n" + "="*60)
    print("SUCCESS! Data refreshed.")
    print("="*60)
    print(f"\nRun folder: data/{run_id}/")

    run_dir = DATA_DIR / run_id
    if run_dir.is_dir():
        print("Contents:")
        for f in run_dir.iterdir():
            print(f"  - {f.name}")

    print("\nRun the dashboard with:")
    print("  streamlit run dashboard_app.py")


if __name__ == "__main__":
    main()
