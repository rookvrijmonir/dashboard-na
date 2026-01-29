import streamlit as st
import pandas as pd
import json
import os
import sys
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file for local development
from etl.fetch_hubspot import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Data Beheer - Nationale Apotheek",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Data Beheer")
st.markdown("Beheer je dashboard data: refresh vanuit HubSpot of wissel tussen eerdere runs.")

# Paths
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
RUNS_FILE = DATA_DIR / "runs.json"


def _fs_is_writable(path: Path = DATA_DIR) -> bool:
    """Check if the filesystem at *path* is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok")
        probe.unlink()
        return True
    except (OSError, PermissionError):
        return False


def _get_work_dirs() -> tuple[Path, Path]:
    """Return (data_dir, cache_dir) that are guaranteed writable.

    On a writable filesystem the normal project dirs are used.
    On a read-only filesystem (Streamlit Cloud) we fall back to /tmp.
    """
    if _fs_is_writable(DATA_DIR):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR, CACHE_DIR

    tmp_root = Path(tempfile.mkdtemp(prefix="coach_dashboard_"))
    tmp_data = tmp_root / "data"
    tmp_cache = tmp_root / "etl" / "cache"
    tmp_data.mkdir(parents=True, exist_ok=True)
    tmp_cache.mkdir(parents=True, exist_ok=True)
    return tmp_data, tmp_cache


def load_runs() -> dict:
    """Load run history from JSON."""
    if RUNS_FILE.is_file():
        try:
            with open(RUNS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback: try GCS
    try:
        from gcs_storage import download_runs_json_data, gcs_available
        if gcs_available():
            data = download_runs_json_data()
            if data:
                return data
    except Exception:
        pass

    return {"runs": [], "selected": None}


def save_runs(runs_data: dict, sync_gcs: bool = False):
    """Save run history to JSON locally, optionally to GCS."""
    # Try local write
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(RUNS_FILE, "w") as f:
            json.dump(runs_data, f, indent=2, default=str)
    except (OSError, PermissionError):
        pass

    # GCS upload only when explicitly requested (e.g. after ETL run)
    if sync_gcs:
        try:
            from gcs_storage import upload_runs_json_bytes, gcs_available
            if gcs_available():
                upload_runs_json_bytes(runs_data)
        except Exception:
            pass


def scan_existing_runs() -> list:
    """Scan data folder for existing run directories."""
    runs = []
    if not DATA_DIR.is_dir():
        return runs

    # Look for directories with run_id pattern (YYYYMMDD_HHMMSS)
    for d in DATA_DIR.iterdir():
        if not d.is_dir():
            continue
        if len(d.name) != 15 or "_" not in d.name:
            continue

        try:
            # Parse datetime from folder name
            date_str = d.name[:8]  # YYYYMMDD
            time_str = d.name[9:]  # HHMMSS
            dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")

            # Check for required files
            eligibility_file = d / "coach_eligibility.xlsx"
            enums_file = d / "enums.xlsx"

            if not eligibility_file.is_file():
                continue

            # Get coach count
            try:
                df = pd.read_excel(eligibility_file, sheet_name="Coaches")
                coach_count = len(df)
            except Exception:
                coach_count = None

            # Get folder size
            total_size = sum(f.stat().st_size for f in d.glob("*") if f.is_file())

            runs.append({
                "run_id": d.name,
                "folder": str(d),
                "datetime": dt.isoformat(),
                "datetime_display": dt.strftime("%d-%m-%Y %H:%M:%S"),
                "date_display": dt.strftime("%d-%m-%Y"),
                "time_display": dt.strftime("%H:%M:%S"),
                "size_kb": round(total_size / 1024, 1),
                "coach_count": coach_count,
                "has_enums": enums_file.is_file()
            })
        except Exception:
            continue

    # Sort by datetime, newest first
    runs.sort(key=lambda x: x["run_id"], reverse=True)
    return runs


def sync_runs_file():
    """Sync runs.json with actual folders in data directory."""
    runs_data = load_runs()

    if _fs_is_writable(DATA_DIR):
        scanned = scan_existing_runs()
        runs_data["runs"] = scanned

        # Ensure selected run still exists
        if runs_data["selected"]:
            valid_ids = [r["run_id"] for r in scanned]
            if runs_data["selected"] not in valid_ids:
                runs_data["selected"] = scanned[0]["run_id"] if scanned else None
        elif scanned:
            runs_data["selected"] = scanned[0]["run_id"]

        save_runs(runs_data)

    return runs_data


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud."""
    if Path("/mount/src").exists():
        return True
    if os.environ.get("HOME") == "/home/appuser":
        return True
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        return True
    return False


def get_hubspot_pat() -> str:
    """Get HUBSPOT_PAT from Streamlit secrets or environment."""
    try:
        pat = st.secrets.get("HUBSPOT_PAT", "")
        if pat and not pat.startswith("pat-xx-"):
            return pat
    except Exception:
        pass
    return os.environ.get("HUBSPOT_PAT", "")


def check_env_file() -> bool:
    """Check if HUBSPOT_PAT is available (via secrets or .env)."""
    pat = get_hubspot_pat()
    if pat and not pat.startswith("pat-xx-"):
        return True
    return False


def _step_html(step_num: int, total: int, text: str, state: str = "pending") -> str:
    """Return styled HTML for a step indicator.

    state: 'done', 'active', 'pending'
    """
    if state == "done":
        icon = "&#x2705;"  # green check
        color = "#28a745"
    elif state == "active":
        icon = "&#x1F504;"  # arrows
        color = "#0d6efd"
    else:
        icon = "&#x2B1C;"  # white square
        color = "#6c757d"

    return (
        f"<div style='padding:2px 0; color:{color}; font-size:0.95em;'>"
        f"{icon} <b>Stap {step_num}/{total}:</b> {text}</div>"
    )


def run_etl_with_progress(refresh_all: bool = True):
    """Run ETL scripts with progress updates in Streamlit.

    Works both locally and on Streamlit Cloud by using writable tmp
    directories as fallback and persisting output to GCS.
    """
    from etl.fetch_hubspot import (
        Config, Workflow, ensure_dirs, load_dotenv, utc_now_run_id,
        CACHE_DIR as FETCH_CACHE_DIR, DATA_DIR as FETCH_DATA_DIR
    )
    from etl.calculate_metrics import (
        calculate_for_run,
        load_or_fetch_owners,
        DATA_DIR as METRICS_DATA_DIR
    )
    import logging
    import gcs_storage

    TOTAL_STEPS = 6

    load_dotenv()

    pat = get_hubspot_pat().strip()
    if not pat:
        st.error("HUBSPOT_PAT niet gevonden! Voeg toe via Streamlit secrets of .env bestand.")
        return None

    run_id = utc_now_run_id()

    logger = logging.getLogger(f"etl_{run_id}")
    logger.setLevel(logging.INFO)

    cfg = Config(
        pat=pat,
        aangebracht_door_value=os.environ.get("AANGEBRACHT_DOOR_VALUE", "Nationale Apotheek").strip() or "Nationale Apotheek",
    )

    # Determine writable directories
    work_data, work_cache = _get_work_dirs()
    on_cloud = is_streamlit_cloud()
    has_gcs = gcs_storage.gcs_available()

    # Ensure PAT is in os.environ so calculate_metrics.hs_headers() works
    # (on Cloud it lives in st.secrets, not os.environ)
    os.environ["HUBSPOT_PAT"] = pat

    # Monkey-patch module-level paths so ETL writes to writable dirs
    import etl.fetch_hubspot as _fh
    import etl.calculate_metrics as _cm
    _fh.CACHE_DIR = work_cache
    _fh.DATA_DIR = work_data
    _fh.LOG_DIR = work_data / "_logs"
    _cm.CACHE_DIR = work_cache
    _cm.DATA_DIR = work_data

    progress_bar = st.progress(0)
    status_area = st.empty()
    details_container = st.container()

    # Build step tracker — mutable list so we can update states
    steps = [
        {"text": "Cache ophalen", "state": "pending"},
        {"text": "Contacten laden", "state": "pending"},
        {"text": "Deal-koppelingen laden", "state": "pending"},
        {"text": "Deal details ophalen", "state": "pending"},
        {"text": "Metrics berekenen", "state": "pending"},
        {"text": "Opslaan naar cloud", "state": "pending"},
    ]

    def _render_steps(extra: str = ""):
        html = "".join(
            _step_html(i + 1, TOTAL_STEPS, s["text"], s["state"])
            for i, s in enumerate(steps)
        )
        if extra:
            html += f"<div style='margin-top:4px;'>{extra}</div>"
        status_area.markdown(html, unsafe_allow_html=True)

    try:
        # ── Step 1: Download cache from GCS (on Cloud or when cache is empty) ──
        steps[0]["state"] = "active"
        _render_steps()
        progress_bar.progress(3)

        cache_downloaded = []
        if has_gcs and (on_cloud or not any((work_cache / f).is_file() for f in gcs_storage.CACHE_FILES)):
            try:
                cache_downloaded = gcs_storage.download_cache_files(work_cache)
            except Exception:
                pass

        steps[0]["state"] = "done"
        steps[0]["text"] = f"Cache ophalen ({len(cache_downloaded)} bestanden)"
        _render_steps()

        # Prepare workflow
        wf = Workflow(cfg, run_id, logger)
        # Override output dir to writable location
        run_output = work_data / run_id
        run_output.mkdir(parents=True, exist_ok=True)
        wf.run_output_dir = run_output

        with details_container:
            st.info(f"Output folder: `data/{run_id}/`")

        # ── Step 2: Contacts ──
        steps[1]["state"] = "active"
        _render_steps()
        progress_bar.progress(10)
        contacts = wf._load_or_fetch_contacts(refresh=refresh_all)
        steps[1]["state"] = "done"
        steps[1]["text"] = f"{len(contacts)} contacten geladen"
        _render_steps()

        # ── Step 3: Associations ──
        steps[2]["state"] = "active"
        _render_steps()
        progress_bar.progress(30)
        contact_ids = [str(c.get("id")) for c in contacts if c.get("id")]
        links = wf._load_or_fetch_associations(contact_ids, refresh=refresh_all)
        unique_deals = set()
        for ids in links.values():
            unique_deals.update(ids)
        steps[2]["state"] = "done"
        steps[2]["text"] = f"{len(unique_deals)} deal-koppelingen"
        _render_steps()

        # ── Step 4: Deals ──
        steps[3]["state"] = "active"
        _render_steps()
        progress_bar.progress(50)
        deals = wf._load_or_fetch_deals(refresh=refresh_all)
        steps[3]["state"] = "done"
        steps[3]["text"] = f"{len(deals)} deals opgehaald"
        _render_steps()

        # Save enums (part of deals step)
        wf._dump_enums(deals, refresh=refresh_all)

        # Upload cache to GCS after fetching
        if has_gcs:
            try:
                gcs_storage.upload_cache_files(work_cache)
            except Exception:
                pass

        # ── Step 5: Calculate metrics ──
        steps[4]["state"] = "active"
        _render_steps()
        progress_bar.progress(70)

        output_path = calculate_for_run(run_id, refresh_owners=refresh_all)

        # Get coach count
        try:
            df_out = pd.read_excel(output_path, sheet_name="Coaches")
            coach_count = len(df_out)
        except Exception:
            coach_count = "?"

        steps[4]["state"] = "done"
        steps[4]["text"] = f"{coach_count} coaches verwerkt"
        _render_steps()
        progress_bar.progress(85)

        # ── Step 6: Upload to GCS ──
        steps[5]["state"] = "active"
        _render_steps()
        progress_bar.progress(90)

        if has_gcs:
            try:
                gcs_storage.upload_run(run_id, run_output)
            except Exception as e:
                with details_container:
                    st.warning(f"GCS run upload overgeslagen: {e}")

        # Build run metadata entry
        try:
            dt = datetime.strptime(run_id, "%Y%m%d_%H%M%S")
        except ValueError:
            dt = datetime.now()

        total_size = sum(f.stat().st_size for f in run_output.glob("*") if f.is_file())
        new_entry = {
            "run_id": run_id,
            "folder": str(work_data / run_id),
            "datetime": dt.isoformat(),
            "datetime_display": dt.strftime("%d-%m-%Y %H:%M:%S"),
            "date_display": dt.strftime("%d-%m-%Y"),
            "time_display": dt.strftime("%H:%M:%S"),
            "size_kb": round(total_size / 1024, 1),
            "coach_count": coach_count if isinstance(coach_count, int) else None,
            "has_enums": (run_output / "enums.xlsx").is_file(),
        }

        # Update runs.json
        runs_data = load_runs()
        # Remove existing entry with same run_id (if any)
        runs_data["runs"] = [r for r in runs_data["runs"] if r["run_id"] != run_id]
        runs_data["runs"].insert(0, new_entry)
        runs_data["selected"] = run_id
        save_runs(runs_data, sync_gcs=True)

        steps[5]["state"] = "done"
        steps[5]["text"] = "Opgeslagen naar cloud"
        _render_steps()
        progress_bar.progress(100)

        with details_container:
            st.success(f"Output: `data/{run_id}/coach_eligibility.xlsx`")

        return run_id

    except Exception as e:
        st.error(f"Fout tijdens ETL: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

    finally:
        # Restore original module paths
        _fh.CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
        _fh.DATA_DIR = PROJECT_ROOT / "data"
        _fh.LOG_DIR = PROJECT_ROOT / "etl" / "logs"
        _cm.CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
        _cm.DATA_DIR = PROJECT_ROOT / "data"


# Main UI
st.markdown("---")

# Detect environment
on_cloud = is_streamlit_cloud()

# Sync runs on page load
runs_data = sync_runs_file()

# Section 1: Current Selection
st.markdown("## 📊 Actieve Dataset")

if runs_data["runs"]:
    # Create dropdown options
    run_options = {
        f"{r['datetime_display']} - {r['coach_count'] or '?'} coaches ({r['size_kb']} KB)": r["run_id"]
        for r in runs_data["runs"]
    }

    # Find current selection
    current_labels = list(run_options.keys())
    current_values = list(run_options.values())

    try:
        current_index = current_values.index(runs_data["selected"])
    except (ValueError, TypeError):
        current_index = 0

    selected_label = st.selectbox(
        "Selecteer dataset",
        options=current_labels,
        index=current_index,
        help="Kies welke dataset het dashboard moet gebruiken"
    )

    new_selected = run_options[selected_label]

    if new_selected != runs_data["selected"]:
        runs_data["selected"] = new_selected
        save_runs(runs_data)
        st.success("Dataset gewijzigd!")
        st.rerun()

    # Show current selection details
    current_run = next((r for r in runs_data["runs"] if r["run_id"] == runs_data["selected"]), None)
    if current_run:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Datum", current_run["date_display"])
        with col2:
            st.metric("Tijd", current_run["time_display"])
        with col3:
            st.metric("Coaches", current_run["coach_count"] or "?")
        with col4:
            st.metric("Grootte", f"{current_run['size_kb']} KB")

        st.caption(f"Folder: `data/{current_run['run_id']}/`")
else:
    st.warning("Geen datasets gevonden. Gebruik de knop hieronder om data op te halen.")

# Section 2: Refresh Data
st.markdown("---")
st.markdown("## 🔄 Data Vernieuwen")

# Check prerequisites
env_ok = check_env_file()

if not env_ok:
    st.error("""
    **Geen HubSpot token gevonden!**

    **Lokaal:** Maak een `.env` bestand in de project root met:
    ```
    HUBSPOT_PAT=pat-xx-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    ```

    **Streamlit Cloud:** Voeg toe aan Secrets (TOML):
    ```toml
    HUBSPOT_PAT = "pat-xx-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    ```
    """)
else:
    st.success("HubSpot configuratie gevonden")

    if on_cloud:
        st.info("Draait op Streamlit Cloud — data wordt opgeslagen in Google Cloud Storage.")

    st.markdown("""
    Klik op de knop om verse data op te halen uit HubSpot.
    Elke run wordt opgeslagen zodat je kunt vergelijken.
    """)

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("🔄 Data Ophalen", type="primary", use_container_width=True):
            st.markdown("---")
            st.markdown("### Voortgang")

            result = run_etl_with_progress(refresh_all=True)

            if result:
                st.balloons()
                st.success(f"Nieuwe dataset aangemaakt: `{result}`")
                time.sleep(2)
                st.rerun()

    with col2:
        st.info("""
        **Wat gebeurt er?**
        1. Cache ophalen (GCS)
        2. Contacten ophalen (Nationale Apotheek)
        3. Deal koppelingen ophalen
        4. Deal details ophalen
        5. Metrics berekenen
        6. Opslaan naar cloud (GCS)

        **Output:** `data/YYYYMMDD_HHMMSS/`
        """)

# Section 3: Run History
st.markdown("---")
st.markdown("## 📜 Beschikbare Runs")

if runs_data["runs"]:
    for run in runs_data["runs"]:
        is_selected = run["run_id"] == runs_data["selected"]
        icon = "✅" if is_selected else "📁"

        with st.expander(f"{icon} {run['datetime_display']} - {run['coach_count'] or '?'} coaches", expanded=is_selected):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**Run ID:** `{run['run_id']}`")
                st.markdown(f"**Folder:** `data/{run['run_id']}/`")

            with col2:
                st.markdown(f"**Coaches:** {run['coach_count'] or 'Onbekend'}")
                st.markdown(f"**Grootte:** {run['size_kb']} KB")

            with col3:
                if not is_selected:
                    if st.button("Selecteer", key=f"select_{run['run_id']}"):
                        runs_data["selected"] = run["run_id"]
                        save_runs(runs_data)
                        st.rerun()

                    # Hide delete button on Streamlit Cloud (read-only filesystem)
                    if not on_cloud:
                        if st.button("🗑️", key=f"delete_{run['run_id']}", help="Verwijder deze run"):
                            folder_path = Path(run["folder"])
                            if folder_path.is_dir():
                                shutil.rmtree(folder_path)
                                st.success(f"Verwijderd: {run['run_id']}")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.markdown("*Actief*")

    st.caption(f"Totaal: {len(runs_data['runs'])} runs")
else:
    st.info("Nog geen runs beschikbaar. Haal eerst data op.")

# Section 4: Folder Structure Info
st.markdown("---")
with st.expander("Folder Structuur"):
    st.markdown("""
    ```
    data/
    ├── runs.json              # Run configuratie
    ├── mapping.xlsx           # Stage mapping (gedeeld)
    ├── 20260121_195256/       # Run folder
    │   ├── coach_eligibility.xlsx
    │   ├── deals_flat.csv
    │   └── enums.xlsx
    └── 20260122_103000/       # Andere run
        ├── coach_eligibility.xlsx
        ├── deals_flat.csv
        └── enums.xlsx
    ```

    Elke run heeft zijn eigen folder met:
    - `coach_eligibility.xlsx` - Coach metrics en eligibility
    - `deals_flat.csv` - Deals voor Week Monitor
    - `enums.xlsx` - Pipeline en stage configuratie

    **Cloud Storage:** Alle runs worden ook opgeslagen in
    `gs://coach-dashboard-data/` zodat ze beschikbaar zijn
    op Streamlit Cloud.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>🔄 <b>Data Beheer - Coach Dashboard</b></p>
    <p>💊 Nationale Apotheek</p>
</div>
""", unsafe_allow_html=True)
