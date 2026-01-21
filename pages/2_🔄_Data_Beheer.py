import streamlit as st
import pandas as pd
import json
import os
import sys
import time
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
    """Scan data folder for existing eligibility files and build run list."""
    runs = []
    if not DATA_DIR.is_dir():
        return runs

    for f in DATA_DIR.glob("coach_eligibility_*.xlsx"):
        # Parse filename: coach_eligibility_YYYYMMDD_HHMMSS.xlsx
        try:
            parts = f.stem.split("_")
            if len(parts) >= 4:
                date_str = parts[2]  # YYYYMMDD
                time_str = parts[3]  # HHMMSS

                # Parse datetime
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")

                # Get file stats
                stat = f.stat()

                # Try to get coach count from file
                try:
                    df = pd.read_excel(f, sheet_name="Coaches")
                    coach_count = len(df)
                except:
                    coach_count = None

                runs.append({
                    "filename": f.name,
                    "filepath": str(f),
                    "run_id": f"{date_str}_{time_str}",
                    "datetime": dt.isoformat(),
                    "datetime_display": dt.strftime("%d-%m-%Y %H:%M:%S"),
                    "size_kb": round(stat.st_size / 1024, 1),
                    "coach_count": coach_count
                })
        except Exception as e:
            continue

    # Sort by datetime, newest first
    runs.sort(key=lambda x: x["datetime"], reverse=True)
    return runs


def sync_runs_file():
    """Sync runs.json with actual files in data folder."""
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
        Config, Workflow, ensure_dirs, load_dotenv, utc_now_run_id
    )
    from etl.calculate_metrics import (
        main as calculate_metrics_main,
        load_or_fetch_owners,
        compute_metrics,
        determine_eligibility,
        load_mapping,
        build_default_stage_mapping,
        parse_iso,
        parse_bool_str,
        safe_str,
        PIPELINE_NABELLER,
        STAGE_TIJDELIJK_STOPPEN,
        CACHE_DIR as METRICS_CACHE_DIR,
        OUTPUT_DIR as METRICS_OUTPUT_DIR,
        run_id as metrics_run_id,
        newest_file,
        file_nonempty
    )
    import logging

    # Setup
    ensure_dirs()
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

        # Load enums and create mapping
        enums_file = newest_file("enums_*.xlsx", METRICS_OUTPUT_DIR)
        stages_df = pd.read_excel(enums_file, sheet_name="Stages")

        mapping_path = METRICS_OUTPUT_DIR / "mapping.xlsx"
        if not mapping_path.is_file():
            mapping_df = build_default_stage_mapping(stages_df)
            with pd.ExcelWriter(mapping_path, engine="openpyxl") as w:
                mapping_df.to_excel(w, sheet_name="stage_mapping", index=False)

        stage_map = load_mapping(mapping_path)

        # Process deals
        deals_path = METRICS_CACHE_DIR / "deals_raw.json"
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
        metrics_df = compute_metrics(deals_df)
        final_df = determine_eligibility(metrics_df)

        # Get owners
        owners = load_or_fetch_owners(refresh=refresh_all)
        if owners:
            final_df.insert(1, "Coachnaam", final_df["coach_id"].astype(str).map(lambda x: owners.get(x, "UNKNOWN")))
        else:
            final_df.insert(1, "Coachnaam", "UNKNOWN")

        progress_bar.progress(95)

        # Save output
        output_run_id = metrics_run_id()
        out_path = METRICS_OUTPUT_DIR / f"coach_eligibility_{output_run_id}.xlsx"

        with pd.ExcelWriter(out_path, engine="openpyxl") as w:
            final_df.to_excel(w, sheet_name="Coaches", index=False)
            summary = deals_df.groupby(["pipeline", "class"]).size().reset_index(name="count")
            summary.to_excel(w, sheet_name="DealClassSummary", index=False)
            if owners:
                owners_df = pd.DataFrame([{"coach_id": k, "Coachnaam": v} for k, v in sorted(owners.items())])
                owners_df.to_excel(w, sheet_name="Owners", index=False)

        progress_bar.progress(100)
        status_text.markdown("**Voltooid!**")

        with details_container:
            st.success(f"✓ {len(final_df)} coaches verwerkt")
            st.success(f"✓ Output: {out_path.name}")

        # Sync runs file
        sync_runs_file()

        return out_path.name

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
        f"{r['datetime_display']} ({r['coach_count'] or '?'} coaches, {r['size_kb']} KB)": r["run_id"]
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
        st.success(f"✓ Dataset gewijzigd naar {selected_label}")
        st.rerun()

    # Show current selection details
    current_run = next((r for r in runs_data["runs"] if r["run_id"] == runs_data["selected"]), None)
    if current_run:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Datum", current_run["datetime_display"].split(" ")[0])
        with col2:
            st.metric("Tijd", current_run["datetime_display"].split(" ")[1])
        with col3:
            st.metric("Coaches", current_run["coach_count"] or "?")
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
    Klik op de knop om verse data op te halen uit HubSpot. Dit kan enkele minuten duren
    afhankelijk van de hoeveelheid data.
    """)

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("🔄 Data Ophalen", type="primary", use_container_width=True):
            st.markdown("---")
            st.markdown("### Voortgang")

            result = run_etl_with_progress(refresh_all=True)

            if result:
                st.balloons()
                st.success(f"✅ Data succesvol opgehaald: {result}")
                st.markdown("**Ververs de pagina om de nieuwe dataset te selecteren.**")
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
        """)

# Section 3: Run History
st.markdown("---")
st.markdown("## 📜 Run Geschiedenis")

if runs_data["runs"]:
    history_df = pd.DataFrame(runs_data["runs"])
    history_df = history_df[["datetime_display", "coach_count", "size_kb", "filename"]]
    history_df.columns = ["Datum/Tijd", "Coaches", "Grootte (KB)", "Bestand"]

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )

    # Option to delete old runs
    with st.expander("🗑️ Oude runs verwijderen"):
        st.warning("Let op: verwijderde bestanden kunnen niet worden hersteld!")

        if len(runs_data["runs"]) > 1:
            runs_to_delete = st.multiselect(
                "Selecteer runs om te verwijderen",
                options=[r["filename"] for r in runs_data["runs"][1:]],  # Exclude newest
                help="De nieuwste run kan niet worden verwijderd"
            )

            if runs_to_delete and st.button("🗑️ Verwijderen", type="secondary"):
                for filename in runs_to_delete:
                    filepath = DATA_DIR / filename
                    if filepath.is_file():
                        filepath.unlink()
                        st.success(f"Verwijderd: {filename}")

                sync_runs_file()
                time.sleep(1)
                st.rerun()
        else:
            st.info("Er is maar één run beschikbaar.")
else:
    st.info("Nog geen runs beschikbaar. Haal eerst data op.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>🔄 <b>Data Beheer - Coach Dashboard</b></p>
    <p>💊 Nationale Apotheek</p>
</div>
""", unsafe_allow_html=True)
