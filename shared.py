"""
Shared module for Coach Dashboard.

Centralises constants, data loading, global sidebar, and exclusion logic
so that every page uses the same filters and data sources.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

EXCLUDE_PATTERNS = ["nabeller"]
EXCLUDE_EXACT = [
    "Rookvrij en Fitter Het Gooi",
    "167331984",
    "UNKNOWN",
    "benVitaal Coaching",
    "SportQube Algemeen",
]

PERIODE_MAP = {
    "1 maand": {"deals": "deals_1m", "winrate": "smoothed_1m", "label": "1 maand", "nabeller": "nabeller_pct_1m", "warme": "warme_aanvraag_1m", "info": "info_aanvraag_1m"},
    "3 maanden": {"deals": "deals_3m", "winrate": "smoothed_3m", "label": "3 maanden", "nabeller": "nabeller_pct_3m", "warme": "warme_aanvraag_3m", "info": "info_aanvraag_3m"},
    "6 maanden": {"deals": "deals_6m", "winrate": "smoothed_6m", "label": "6 maanden", "nabeller": "nabeller_pct_6m", "warme": "warme_aanvraag_6m", "info": "info_aanvraag_6m"},
}

PIPELINE_NABELLER = "38341389"

# Dealstage IDs
STAGES_WARME_AANVRAAG = {"114855767", "81686449"}
STAGES_INFO_AANVRAAG = {"15415582", "116831596"}

STATUS_COLORS = {
    "✅ Goed": "#28a745",
    "⭐ Matig": "#ffc107",
    "❌ Uitsluiten": "#dc3545",
    "⚠️ Uitsluiten": "#dc3545",
    "⚪ Geen data": "#6c757d",
}

# ============================================================================
# DATA PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RUNS_FILE = DATA_DIR / "runs.json"


# ============================================================================
# DATA LOADING
# ============================================================================

def _try_gcs_download_runs_json() -> bool:
    """Try to download runs.json from GCS. Returns True on success."""
    try:
        from gcs_storage import download_runs_json, gcs_available
        if gcs_available():
            return download_runs_json(RUNS_FILE)
    except Exception as e:
        logger.debug("GCS runs.json download failed: %s", e)
    return False


def _try_gcs_download_run(run_id: str) -> bool:
    """Try to download a run from GCS. Returns True on success."""
    try:
        from gcs_storage import download_run, gcs_available
        if gcs_available():
            return download_run(run_id, DATA_DIR / run_id)
    except Exception as e:
        logger.debug("GCS run download failed for %s: %s", run_id, e)
    return False


def get_selected_run_id() -> str | None:
    """Get the currently selected run ID from runs.json.
    Falls back to GCS if local runs.json does not exist."""
    if not RUNS_FILE.is_file():
        _try_gcs_download_runs_json()

    if RUNS_FILE.is_file():
        try:
            with open(RUNS_FILE, "r") as f:
                runs_data = json.load(f)
            return runs_data.get("selected")
        except Exception:
            pass
    return None


def _get_selected_data_file() -> Path | None:
    """Get the path to the selected coach_eligibility.xlsx.
    Falls back to GCS download if local file is missing."""
    run_id = get_selected_run_id()
    if run_id:
        run_file = DATA_DIR / run_id / "coach_eligibility.xlsx"
        if run_file.is_file():
            return run_file
        # Try GCS fallback for selected run
        if _try_gcs_download_run(run_id) and run_file.is_file():
            return run_file

    # Fallback: most recent run folder
    if DATA_DIR.is_dir():
        run_dirs = [
            d for d in DATA_DIR.iterdir()
            if d.is_dir() and len(d.name) == 15 and "_" in d.name
        ]
        if run_dirs:
            run_dirs.sort(key=lambda p: p.name, reverse=True)
            for run_dir in run_dirs:
                f = run_dir / "coach_eligibility.xlsx"
                if f.is_file():
                    return f

    # Legacy fallback
    files = list(DATA_DIR.glob("coach_eligibility_*.xlsx"))
    if files:
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]

    return None


def _get_selected_run_dir() -> Path | None:
    """Get the directory of the selected run.
    Falls back to GCS download if local dir is missing."""
    run_id = get_selected_run_id()
    if run_id:
        run_dir = DATA_DIR / run_id
        if run_dir.is_dir():
            return run_dir
        # Try GCS
        if _try_gcs_download_run(run_id) and run_dir.is_dir():
            return run_dir
    return None


@st.cache_data
def load_coach_data_raw() -> pd.DataFrame:
    """Load raw coach data from Excel with standard excludes applied."""
    file_path = _get_selected_data_file()
    if file_path is None:
        raise FileNotFoundError("No coach_eligibility.xlsx found in data/")
    df = pd.read_excel(file_path, sheet_name="Coaches")

    for pattern in EXCLUDE_PATTERNS:
        df = df[~df["Coachnaam"].str.lower().str.contains(pattern, na=False)]
    df = df[~df["Coachnaam"].isin(EXCLUDE_EXACT)]

    return df


@st.cache_data
def load_deal_class_summary() -> pd.DataFrame:
    """Load deal class summary sheet."""
    file_path = _get_selected_data_file()
    if file_path is None:
        raise FileNotFoundError("No coach_eligibility.xlsx found in data/")
    return pd.read_excel(file_path, sheet_name="DealClassSummary")


@st.cache_data
def load_deals_flat() -> pd.DataFrame | None:
    """Load deals_flat.csv from the selected run.
    Falls back to GCS if local file is missing."""
    run_dir = _get_selected_run_dir()
    if run_dir is None:
        return None

    deals_path = run_dir / "deals_flat.csv"
    if not deals_path.is_file():
        # _get_selected_run_dir already tried GCS, but deals_flat.csv
        # may not have been present in the run at that point.
        # Try explicit download.
        run_id = run_dir.name
        _try_gcs_download_run(run_id)

    if not deals_path.is_file():
        return None

    df = pd.read_csv(deals_path)
    df["created_dt"] = pd.to_datetime(
        df["created_dt"], format="ISO8601", utc=True, errors="coerce"
    )
    df = df.dropna(subset=["created_dt"])
    return df


# ============================================================================
# GLOBAL SIDEBAR
# ============================================================================

def render_global_sidebar() -> dict:
    """
    Render the global sidebar controls (period + coach exclusion).

    Stores selections in st.session_state and returns a dict with:
      - periode_keuze: str
      - deals_col: str
      - winrate_col: str
      - nabeller_col: str
      - warme_col: str
      - info_col: str
      - periode_label: str
      - excluded_coaches: list[str]
    """
    st.sidebar.header("🎯 Filters")

    # --- Period selector ---
    st.sidebar.markdown("### 📅 Periode")
    st.sidebar.markdown("*Kies de periode voor ALLE grafieken en berekeningen*")

    periode_keuze = st.sidebar.radio(
        "Selecteer periode",
        options=list(PERIODE_MAP.keys()),
        index=0,
        horizontal=True,
        key="global_periode",
    )

    pm = PERIODE_MAP[periode_keuze]
    st.sidebar.success(f"📊 Alle data gebaseerd op: **{pm['label']}**")
    st.sidebar.markdown("---")

    # --- Coach exclusion ---
    st.sidebar.markdown("### 🚫 Coaches Uitsluiten")

    try:
        all_coaches = sorted(load_coach_data_raw()["Coachnaam"].unique())
    except FileNotFoundError:
        all_coaches = []

    excluded_coaches = st.sidebar.multiselect(
        "Selecteer coaches om uit te sluiten",
        options=all_coaches,
        default=[],
        help="Deze coaches worden volledig verwijderd uit alle grafieken en berekeningen",
        key="excluded_coaches",
    )

    if excluded_coaches:
        st.sidebar.info(f"🚫 {len(excluded_coaches)} coach(es) uitgesloten")

    st.sidebar.markdown("---")

    # Store in session state for cross-page access
    st.session_state["_global_periode"] = periode_keuze
    st.session_state["_excluded_coaches"] = excluded_coaches

    return {
        "periode_keuze": periode_keuze,
        "deals_col": pm["deals"],
        "winrate_col": pm["winrate"],
        "nabeller_col": pm["nabeller"],
        "warme_col": pm["warme"],
        "info_col": pm["info"],
        "periode_label": pm["label"],
        "excluded_coaches": excluded_coaches,
    }


# ============================================================================
# EXCLUSION HELPERS
# ============================================================================

def apply_global_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Remove coaches listed in session_state excluded_coaches."""
    excluded = st.session_state.get("_excluded_coaches", [])
    if excluded:
        df = df[~df["Coachnaam"].isin(excluded)].copy()
    return df


# ============================================================================
# FILTER BANNER
# ============================================================================

def render_active_filters_banner(
    periode_label: str,
    excluded_coaches: list[str],
    extra_filters: dict[str, str] | None = None,
):
    """
    Show a coloured banner at the top of the page summarising active filters.

    extra_filters: optional dict of label -> value pairs for page-local filters.
    """
    parts = [f"<b>Periode:</b> {periode_label}"]

    if excluded_coaches:
        parts.append(f"<b>Uitgesloten:</b> {len(excluded_coaches)} coach(es)")

    if extra_filters:
        for label, value in extra_filters.items():
            parts.append(f"<b>{label}:</b> {value}")

    filters_html = " &nbsp;|&nbsp; ".join(parts)

    st.markdown(
        f"""<div style='background-color: #e2e3e5; padding: 10px 16px;
        border-radius: 6px; margin-bottom: 12px; font-size: 0.95em;'>
        🔍 {filters_html}
        </div>""",
        unsafe_allow_html=True,
    )


# ============================================================================
# RUN INFO (footer helper)
# ============================================================================

def render_footer(page_icon: str = "💊", page_title: str = "Coach Prestatie Dashboard"):
    """Render a consistent footer with run info."""
    run_id = get_selected_run_id()
    if run_id and len(run_id) == 15:
        data_date = f"{run_id[6:8]}-{run_id[4:6]}-{run_id[:4]}"
        data_time = f"{run_id[9:11]}:{run_id[11:13]}"
        run_info = f"Run: {data_date} {data_time}"
    else:
        run_info = "Run: onbekend"

    st.markdown("---")
    st.markdown(
        f"""<div style='text-align: center; color: gray; font-size: 0.9em;'>
        <p>{page_icon} <b>{page_title}</b></p>
        <p>{run_info} | 🔄 <a href="/Data_Beheer" target="_self">Data Beheer</a></p>
        </div>""",
        unsafe_allow_html=True,
    )
