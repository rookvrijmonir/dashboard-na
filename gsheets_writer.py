"""
Google Sheets writer for NA_Pool export.

Usage (lokaal):
    export GOOGLE_SA_JSON_PATH=/pad/naar/service_account.json

    Of zet GOOGLE_SA_JSON_PATH in .env file.

    Zorg dat de service account email (uit de JSON) editor toegang heeft tot de Google Sheet.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd

# Default fallback path relative to project root
DEFAULT_SA_PATH = Path(__file__).parent / "secrets" / "service_account.json"


def get_gspread_client():
    """
    Initialize gspread client using service account JSON.

    Tries in order:
      1. GOOGLE_SA_JSON_PATH environment variable (local file path)
      2. secrets/service_account.json fallback (local file)
      3. st.secrets["gcp_service_account"] (Streamlit Cloud)

    Returns:
        gspread.Client or raises an exception with clear message.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Try environment variable first
    sa_path = os.environ.get("GOOGLE_SA_JSON_PATH")

    # Fallback to default path if env var not set
    if not sa_path and DEFAULT_SA_PATH.is_file():
        sa_path = str(DEFAULT_SA_PATH)

    if sa_path:
        if not os.path.isfile(sa_path):
            raise FileNotFoundError(
                f"Service account bestand niet gevonden: {sa_path}\n\n"
                "Controleer of het pad correct is."
            )
        credentials = Credentials.from_service_account_file(sa_path, scopes=scopes)
        return gspread.authorize(credentials)

    # Fallback to Streamlit Cloud secrets
    try:
        import streamlit as st
        sa_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(dict(sa_info), scopes=scopes)
        return gspread.authorize(credentials)
    except Exception:
        pass

    raise EnvironmentError(
        "Google Service Account niet gevonden.\n\n"
        "Lokaal: plaats service_account.json in secrets/ of stel GOOGLE_SA_JSON_PATH in.\n"
        "Streamlit Cloud: voeg gcp_service_account toe aan Settings → Secrets."
    )


def push_to_na_pool(
    df: pd.DataFrame,
    weight: int,
    cap_dag: int,
    cap_week: int,
    sheet_id: str = "1f3fbZasyqt_UwZtXuShHJ8f9H66lUB3KE20vj6OFxwI",
    tab_name: str = "NA_Pool"
) -> Tuple[int, int, List[str]]:
    """
    Push eligible coaches to NA_Pool tab in Google Sheets.

    Args:
        df: DataFrame with selected coaches. Must contain 'coach_id' and 'Coachnaam' columns.
        weight: Weight value for all coaches.
        cap_dag: Daily cap value.
        cap_week: Weekly cap value.
        sheet_id: Google Sheet ID.
        tab_name: Tab name to write to.

    Returns:
        Tuple of (aantal_geschreven, aantal_geskipt, lijst_geskipte_namen)

    Raises:
        EnvironmentError: If GOOGLE_SA_JSON_PATH is not set.
        FileNotFoundError: If service account file doesn't exist.
        gspread.exceptions.SpreadsheetNotFound: If sheet not accessible.
    """
    client = get_gspread_client()

    # Open spreadsheet and worksheet
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(tab_name)

    # Prepare data
    timestamp = datetime.now().isoformat(timespec='seconds')

    rows_to_write = []
    skipped_coaches = []

    for _, row in df.iterrows():
        owner_id = row.get('coach_id')
        coach_naam = row.get('Coachnaam', '')

        # Skip coaches without owner_id
        if pd.isna(owner_id) or owner_id == '' or owner_id is None:
            skipped_coaches.append(coach_naam)
            continue

        # Convert owner_id to string (in case it's numeric)
        owner_id_str = str(int(owner_id)) if isinstance(owner_id, float) else str(owner_id)

        rows_to_write.append([
            owner_id_str,           # owner_id
            coach_naam,             # coach_naam
            "JA",                   # eligible
            weight,                 # weight
            cap_dag,                # cap_dag
            cap_week,               # cap_week
            "",                     # exclude_manual (leeg)
            timestamp,              # laatst_bijgewerkt
            "pushed from local dashboard"  # note
        ])

    if not rows_to_write:
        return 0, len(skipped_coaches), skipped_coaches

    # Clear existing data (row 2+) and write new data in one batch
    # First, get current sheet dimensions
    all_values = worksheet.get_all_values()

    if len(all_values) > 1:
        # Clear rows 2 to end (keep header)
        end_row = len(all_values)
        # Clear by updating with empty values
        clear_range = f"A2:I{end_row}"
        worksheet.batch_clear([clear_range])

    # Write new data starting at row 2
    if rows_to_write:
        # Use batch update for efficiency
        end_row = 1 + len(rows_to_write)
        update_range = f"A2:I{end_row}"
        worksheet.update(update_range, rows_to_write, value_input_option='RAW')

    return len(rows_to_write), len(skipped_coaches), skipped_coaches


def test_connection(sheet_id: str = "1f3fbZasyqt_UwZtXuShHJ8f9H66lUB3KE20vj6OFxwI") -> Dict[str, Any]:
    """
    Test connection to Google Sheets and return sheet info.

    Returns:
        Dict with 'success', 'sheet_title', 'tabs', and optional 'error'.
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)

        return {
            "success": True,
            "sheet_title": spreadsheet.title,
            "tabs": [ws.title for ws in spreadsheet.worksheets()]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
