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
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_script(script_path: Path, args: list = None) -> bool:
    """Run a Python script and return True if successful."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


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

    if not run_script(fetch_script, refresh_arg):
        print("\nERROR: Fetch failed!")
        sys.exit(1)

    # Step 2: Calculate metrics
    metrics_script = PROJECT_ROOT / "etl" / "calculate_metrics.py"
    if not metrics_script.is_file():
        print(f"ERROR: {metrics_script} not found!")
        sys.exit(1)

    if not run_script(metrics_script):
        print("\nERROR: Metrics calculation failed!")
        sys.exit(1)

    # Done
    print("\n" + "="*60)
    print("SUCCESS! Data refreshed.")
    print("="*60)
    print("\nNew data files in data/:")

    data_dir = PROJECT_ROOT / "data"
    for f in sorted(data_dir.glob("coach_eligibility_*.xlsx"))[-3:]:
        print(f"  - {f.name}")

    print("\nRun the dashboard with:")
    print("  streamlit run dashboard_app.py")


if __name__ == "__main__":
    main()
