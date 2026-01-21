import streamlit as st
import pandas as pd
import json
import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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


def load_runs() -> dict:
    """Load run history from JSON."""
    if RUNS_FILE.is_file():
        try:
            with open(RUNS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"runs": [], "selected": None}


def save_runs(runs_data: dict):
    """Save run history to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RUNS_FILE, "w") as f:
        json.dump(runs_data, f, indent=2, default=str)


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
            except:
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
        except Exception as e:
            continue

    # Sort by datetime, newest first
    runs.sort(key=lambda x: x["run_id"], reverse=True)
    return runs


def sync_runs_file():
    """Sync runs.json with actual folders in data directory."""
    runs_data = load_runs()
    scanned = scan_existing_runs()

    # Update runs list
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


def check_env_file() -> bool:
    """Check if .env file exists with HUBSPOT_PAT."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return False

    with open(env_path, "r") as f:
        content = f.read()
        if "HUBSPOT_PAT=" in content and "pat-xx-" not in content:
            return True
    return False


def run_etl_with_progress(refresh_all: bool = True):
    """Run ETL scripts with progress updates in Streamlit."""
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

    # Setup
    load_dotenv()

    pat = os.environ.get("HUBSPOT_PAT", "").strip()
    if not pat:
        st.error("❌ HUBSPOT_PAT niet gevonden in .env bestand!")
        return None

    run_id = utc_now_run_id()

    # Create a simple logger that doesn't interfere with Streamlit
    logger = logging.getLogger(f"etl_{run_id}")
    logger.setLevel(logging.INFO)

    cfg = Config(
        pat=pat,
        aangebracht_door_value=os.environ.get("AANGEBRACHT_DOOR_VALUE", "Nationale Apotheek").strip() or "Nationale Apotheek",
    )

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    details_container = st.container()

    try:
        wf = Workflow(cfg, run_id, logger)

        with details_container:
            st.info(f"📁 Output folder: `data/{run_id}/`")

        # Step 1: Contacts
        status_text.markdown("**Stap 1/5:** Contacten ophalen uit HubSpot...")
        progress_bar.progress(10)
        contacts = wf._load_or_fetch_contacts(refresh=refresh_all)
        with details_container:
            st.success(f"✓ {len(contacts)} contacten geladen")

        # Step 2: Associations
        status_text.markdown("**Stap 2/5:** Contact-deal koppelingen ophalen...")
        progress_bar.progress(30)
        contact_ids = [str(c.get("id")) for c in contacts if c.get("id")]
        links = wf._load_or_fetch_associations(contact_ids, refresh=refresh_all)
        unique_deals = set()
        for ids in links.values():
            unique_deals.update(ids)
        with details_container:
            st.success(f"✓ {len(unique_deals)} unieke deals gevonden")

        # Step 3: Deals
        status_text.markdown("**Stap 3/5:** Deal details ophalen...")
        progress_bar.progress(50)
        deals = wf._load_or_fetch_deals(refresh=refresh_all)
        with details_container:
            st.success(f"✓ {len(deals)} deals geladen")

        # Step 4: Enums
        status_text.markdown("**Stap 4/5:** Pipeline configuratie ophalen...")
        progress_bar.progress(65)
        enums_path = wf._dump_enums(deals, refresh=refresh_all)
        with details_container:
            st.success(f"✓ Pipeline enums opgeslagen")

        # Step 5: Calculate metrics
        status_text.markdown("**Stap 5/5:** Metrics berekenen...")
        progress_bar.progress(80)

        output_path = calculate_for_run(run_id, refresh_owners=refresh_all)

        progress_bar.progress(100)
        status_text.markdown("**Voltooid!**")

        # Get coach count from output
        try:
            df = pd.read_excel(output_path, sheet_name="Coaches")
            coach_count = len(df)
        except:
            coach_count = "?"

        with details_container:
            st.success(f"✓ {coach_count} coaches verwerkt")
            st.success(f"✓ Output: `data/{run_id}/coach_eligibility.xlsx`")

        # Sync runs file and select new run
        runs_data = sync_runs_file()
        runs_data["selected"] = run_id
        save_runs(runs_data)

        return run_id

    except Exception as e:
        st.error(f"❌ Fout tijdens ETL: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


# Main UI
st.markdown("---")

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
        st.success(f"✓ Dataset gewijzigd!")
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

        st.caption(f"📁 Folder: `data/{current_run['run_id']}/`")
else:
    st.warning("⚠️ Geen datasets gevonden. Gebruik de knop hieronder om data op te halen.")

# Section 2: Refresh Data
st.markdown("---")
st.markdown("## 🔄 Data Vernieuwen")

# Check prerequisites
env_ok = check_env_file()

if not env_ok:
    st.error("""
    ❌ **Geen HubSpot token gevonden!**

    Maak een `.env` bestand in de project root met:
    ```
    HUBSPOT_PAT=pat-xx-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    ```
    """)
else:
    st.success("✓ HubSpot configuratie gevonden")

    st.markdown("""
    Klik op de knop om verse data op te halen uit HubSpot.
    Elke run wordt opgeslagen in een aparte map zodat je kunt vergelijken.
    """)

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("🔄 Data Ophalen", type="primary", use_container_width=True):
            st.markdown("---")
            st.markdown("### Voortgang")

            result = run_etl_with_progress(refresh_all=True)

            if result:
                st.balloons()
                st.success(f"✅ Nieuwe dataset aangemaakt: `{result}`")
                time.sleep(2)
                st.rerun()

    with col2:
        st.info("""
        **Wat gebeurt er?**
        1. Contacten ophalen (Nationale Apotheek)
        2. Deal koppelingen ophalen
        3. Deal details ophalen
        4. Pipeline configuratie laden
        5. Metrics berekenen en opslaan

        **Output:** `data/YYYYMMDD_HHMMSS/`
        """)

# Section 3: Run History
st.markdown("---")
st.markdown("## 📜 Beschikbare Runs")

if runs_data["runs"]:
    # Show as nice cards/table
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
with st.expander("ℹ️ Folder Structuur"):
    st.markdown("""
    ```
    data/
    ├── runs.json              # Run configuratie
    ├── mapping.xlsx           # Stage mapping (gedeeld)
    ├── 20260121_195256/       # Run folder
    │   ├── coach_eligibility.xlsx
    │   └── enums.xlsx
    └── 20260122_103000/       # Andere run
        ├── coach_eligibility.xlsx
        └── enums.xlsx
    ```

    Elke run heeft zijn eigen folder met:
    - `coach_eligibility.xlsx` - Coach metrics en eligibility
    - `enums.xlsx` - Pipeline en stage configuratie
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>🔄 <b>Data Beheer - Coach Dashboard</b></p>
    <p>💊 Nationale Apotheek</p>
</div>
""", unsafe_allow_html=True)
