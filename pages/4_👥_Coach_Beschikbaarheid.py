import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from gsheets_writer import get_gspread_client

st.set_page_config(
    page_title="Coach Beschikbaarheid - Nationale Apotheek",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Coach Beschikbaarheid")
st.markdown("Beheer welke coaches beschikbaar zijn voor Nationale Apotheek leads.")

# ============================================================================
# GOOGLE SHEETS CONNECTION (uses gsheets_writer.get_gspread_client)
# ============================================================================


def get_sheet_url():
    """Get the Google Sheet URL from secrets."""
    try:
        return st.secrets.get("COACH_AVAILABILITY_SHEET_URL", "")
    except Exception:
        return ""


@st.cache_data(ttl=60)  # Cache for 1 minute
def load_availability_from_sheets():
    """Load coach availability from Google Sheets."""
    client = get_gspread_client()
    if not client:
        return None

    sheet_url = get_sheet_url()
    if not sheet_url:
        return None

    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("Beschikbaarheid")
        data = worksheet.get_all_records()

        if not data:
            return pd.DataFrame(columns=[
                "coach_id", "Coachnaam", "na_leads_aan", "afwezig_van",
                "afwezig_tot", "notitie", "laatst_gewijzigd"
            ])

        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Fout bij laden van Sheet: {e}")
        return None


def save_availability_to_sheets(df: pd.DataFrame):
    """Save coach availability to Google Sheets."""
    client = get_gspread_client()
    if not client:
        return False

    sheet_url = get_sheet_url()
    if not sheet_url:
        return False

    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("Beschikbaarheid")

        # Clear and update
        worksheet.clear()

        # Write headers
        headers = df.columns.tolist()
        worksheet.append_row(headers)

        # Write data
        for _, row in df.iterrows():
            worksheet.append_row(row.tolist())

        # Clear cache
        load_availability_from_sheets.clear()

        return True
    except Exception as e:
        st.error(f"Fout bij opslaan naar Sheet: {e}")
        return False


# ============================================================================
# LOAD COACH DATA FROM ELIGIBILITY FILE
# ============================================================================

def load_coaches_from_data():
    """Load coach list from the current data run."""
    data_dir = Path("data")
    runs_file = data_dir / "runs.json"

    if not runs_file.is_file():
        return pd.DataFrame()

    try:
        with open(runs_file, "r") as f:
            runs_data = json.load(f)

        selected_id = runs_data.get("selected")
        if not selected_id:
            return pd.DataFrame()

        file_path = data_dir / selected_id / "coach_eligibility.xlsx"
        if not file_path.is_file():
            return pd.DataFrame()

        df = pd.read_excel(file_path, sheet_name="Coaches")
        # Only keep relevant columns
        cols = ["coach_id", "Coachnaam"]
        available_cols = [c for c in cols if c in df.columns]
        return df[available_cols].drop_duplicates()
    except Exception as e:
        st.error(f"Fout bij laden coach data: {e}")
        return pd.DataFrame()


# ============================================================================
# MAIN UI
# ============================================================================

# Check if Google Sheets is configured
try:
    _gs_client = get_gspread_client()
    _gs_available = _gs_client is not None
except Exception:
    _gs_available = False

sheet_url = get_sheet_url()

if not _gs_available:
    st.warning("""
    ⚠️ **Google Sheets niet geconfigureerd**

    Om coach beschikbaarheid te beheren, moet je Google Sheets koppelen.

    **Setup instructies:**

    1. **Maak een Google Cloud Service Account:**
       - Ga naar [Google Cloud Console](https://console.cloud.google.com/)
       - Maak een project (of gebruik bestaand)
       - Enable de Google Sheets API
       - Maak een Service Account aan
       - Download de JSON key

    2. **Maak een Google Sheet:**
       - Maak een nieuwe Google Sheet
       - Noem het eerste tabblad "Beschikbaarheid"
       - Voeg headers toe: `coach_id | Coachnaam | na_leads_aan | afwezig_van | afwezig_tot | notitie | laatst_gewijzigd`
       - Deel de sheet met het service account email (met Editor rechten)

    3. **Configureer Streamlit Secrets:**
       ```toml
       COACH_AVAILABILITY_SHEET_URL = "https://docs.google.com/spreadsheets/d/xxx/edit"

       [gcp_service_account]
       type = "service_account"
       project_id = "your-project"
       private_key_id = "xxx"
       private_key = "-----BEGIN PRIVATE KEY-----\\nxxx\\n-----END PRIVATE KEY-----\\n"
       client_email = "xxx@xxx.iam.gserviceaccount.com"
       client_id = "123456789"
       auth_uri = "https://accounts.google.com/o/oauth2/auth"
       token_uri = "https://oauth2.googleapis.com/token"
       auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
       client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/xxx"
       ```
    """)

    st.markdown("---")
    st.markdown("### 📋 Preview: Coaches uit huidige data")

    coaches_df = load_coaches_from_data()
    if not coaches_df.empty:
        st.dataframe(coaches_df, use_container_width=True, hide_index=True)
        st.caption(f"Totaal: {len(coaches_df)} coaches in de huidige dataset")
    else:
        st.info("Geen coach data gevonden. Laad eerst data via de Data Beheer pagina.")

elif not sheet_url:
    st.warning("""
    ⚠️ **Google Sheet URL niet ingesteld**

    Voeg de Sheet URL toe aan Streamlit Secrets:
    ```toml
    COACH_AVAILABILITY_SHEET_URL = "https://docs.google.com/spreadsheets/d/xxx/edit"
    ```
    """)

else:
    # Full functionality available
    st.success("✅ Google Sheets gekoppeld")

    # Load data
    availability_df = load_availability_from_sheets()
    coaches_df = load_coaches_from_data()

    if availability_df is None:
        st.error("Kon beschikbaarheid niet laden uit Google Sheets")
        st.stop()

    # Merge coach data with availability
    if not coaches_df.empty:
        # Ensure coach_id is string in both
        coaches_df["coach_id"] = coaches_df["coach_id"].astype(str)
        if not availability_df.empty:
            availability_df["coach_id"] = availability_df["coach_id"].astype(str)

        # Left join to keep all coaches
        merged_df = coaches_df.merge(availability_df, on=["coach_id", "Coachnaam"], how="left")

        # Fill defaults for new coaches
        merged_df["na_leads_aan"] = merged_df["na_leads_aan"].fillna(True)
        merged_df["afwezig_van"] = merged_df["afwezig_van"].fillna("")
        merged_df["afwezig_tot"] = merged_df["afwezig_tot"].fillna("")
        merged_df["notitie"] = merged_df["notitie"].fillna("")
        merged_df["laatst_gewijzigd"] = merged_df["laatst_gewijzigd"].fillna("")
    else:
        merged_df = availability_df

    if merged_df.empty:
        st.info("Geen coaches gevonden. Laad eerst data via de Data Beheer pagina.")
        st.stop()

    # ==================
    # SECTION 1: OVERVIEW
    # ==================
    st.markdown("---")
    st.markdown("## 📊 Overzicht")

    today = date.today()

    # Calculate status for each coach
    def get_status(row):
        if not row.get("na_leads_aan", True):
            return "🔴 NA leads uit"

        afwezig_van = row.get("afwezig_van", "")
        afwezig_tot = row.get("afwezig_tot", "")

        if afwezig_van and afwezig_tot:
            try:
                start = datetime.strptime(str(afwezig_van), "%Y-%m-%d").date()
                end = datetime.strptime(str(afwezig_tot), "%Y-%m-%d").date()
                if start <= today <= end:
                    return "🟡 Afwezig"
            except:
                pass

        return "🟢 Beschikbaar"

    merged_df["status"] = merged_df.apply(get_status, axis=1)

    # Stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        beschikbaar = len(merged_df[merged_df["status"] == "🟢 Beschikbaar"])
        st.metric("🟢 Beschikbaar", beschikbaar)

    with col2:
        afwezig = len(merged_df[merged_df["status"] == "🟡 Afwezig"])
        st.metric("🟡 Afwezig", afwezig)

    with col3:
        na_uit = len(merged_df[merged_df["status"] == "🔴 NA leads uit"])
        st.metric("🔴 NA leads uit", na_uit)

    with col4:
        st.metric("📊 Totaal", len(merged_df))

    # ==================
    # SECTION 2: EDIT TABLE
    # ==================
    st.markdown("---")
    st.markdown("## ✏️ Beschikbaarheid Bewerken")

    st.markdown("""
    Pas de beschikbaarheid van coaches aan. Wijzigingen worden opgeslagen in Google Sheets.

    - **NA leads aan**: Staat deze coach open voor Nationale Apotheek leads?
    - **Afwezig van/tot**: Periode waarin de coach niet beschikbaar is
    - **Notitie**: Optionele toelichting (bijv. "Vakantie" of "Te druk")
    """)

    # Create editable dataframe
    edit_df = merged_df[["coach_id", "Coachnaam", "na_leads_aan", "afwezig_van", "afwezig_tot", "notitie", "status"]].copy()

    # Convert na_leads_aan to boolean for checkbox
    edit_df["na_leads_aan"] = edit_df["na_leads_aan"].apply(lambda x: bool(x) if pd.notna(x) else True)

    edited_df = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        disabled=["coach_id", "Coachnaam", "status"],
        column_config={
            "coach_id": st.column_config.TextColumn("Coach ID", width="small"),
            "Coachnaam": st.column_config.TextColumn("Coach", width="medium"),
            "na_leads_aan": st.column_config.CheckboxColumn("NA leads aan", default=True),
            "afwezig_van": st.column_config.DateColumn("Afwezig van", format="YYYY-MM-DD"),
            "afwezig_tot": st.column_config.DateColumn("Afwezig tot", format="YYYY-MM-DD"),
            "notitie": st.column_config.TextColumn("Notitie", width="medium"),
            "status": st.column_config.TextColumn("Status", width="small"),
        },
        num_rows="fixed"
    )

    # Save button
    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("💾 Opslaan", type="primary", use_container_width=True):
            # Prepare data for saving
            save_df = edited_df[["coach_id", "Coachnaam", "na_leads_aan", "afwezig_van", "afwezig_tot", "notitie"]].copy()
            save_df["laatst_gewijzigd"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Convert dates to strings
            save_df["afwezig_van"] = save_df["afwezig_van"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")
            save_df["afwezig_tot"] = save_df["afwezig_tot"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")

            if save_availability_to_sheets(save_df):
                st.success("✅ Opgeslagen naar Google Sheets!")
                st.rerun()
            else:
                st.error("❌ Opslaan mislukt")

    with col2:
        if st.button("🔄 Vernieuwen", use_container_width=False):
            load_availability_from_sheets.clear()
            st.rerun()

    # ==================
    # SECTION 3: QUICK ACTIONS
    # ==================
    st.markdown("---")
    st.markdown("## ⚡ Snelle Acties")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Coach afwezig melden")

        coach_names = merged_df["Coachnaam"].tolist()
        selected_coach = st.selectbox("Selecteer coach", coach_names, key="absent_coach")

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Van", value=today, key="absent_start")
        with date_col2:
            end_date = st.date_input("Tot", value=today, key="absent_end")

        absent_note = st.text_input("Reden (optioneel)", placeholder="bijv. Vakantie", key="absent_note")

        if st.button("📅 Afwezigheid registreren", use_container_width=True):
            # Update the row
            idx = merged_df[merged_df["Coachnaam"] == selected_coach].index[0]

            save_df = merged_df[["coach_id", "Coachnaam", "na_leads_aan", "afwezig_van", "afwezig_tot", "notitie"]].copy()
            save_df.loc[idx, "afwezig_van"] = start_date.strftime("%Y-%m-%d")
            save_df.loc[idx, "afwezig_tot"] = end_date.strftime("%Y-%m-%d")
            if absent_note:
                save_df.loc[idx, "notitie"] = absent_note
            save_df["laatst_gewijzigd"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Convert dates to strings
            save_df["afwezig_van"] = save_df["afwezig_van"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")
            save_df["afwezig_tot"] = save_df["afwezig_tot"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")

            if save_availability_to_sheets(save_df):
                st.success(f"✅ {selected_coach} afwezig gemeld van {start_date} tot {end_date}")
                st.rerun()

    with col2:
        st.markdown("### NA leads aan/uit zetten")

        selected_coach_toggle = st.selectbox("Selecteer coach", coach_names, key="toggle_coach")

        coach_row = merged_df[merged_df["Coachnaam"] == selected_coach_toggle].iloc[0]
        current_status = coach_row.get("na_leads_aan", True)

        if current_status:
            st.info(f"📊 {selected_coach_toggle} ontvangt momenteel NA leads")
            if st.button("🔴 NA leads UIT zetten", use_container_width=True):
                idx = merged_df[merged_df["Coachnaam"] == selected_coach_toggle].index[0]

                save_df = merged_df[["coach_id", "Coachnaam", "na_leads_aan", "afwezig_van", "afwezig_tot", "notitie"]].copy()
                save_df.loc[idx, "na_leads_aan"] = False
                save_df["laatst_gewijzigd"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                save_df["afwezig_van"] = save_df["afwezig_van"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")
                save_df["afwezig_tot"] = save_df["afwezig_tot"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")

                if save_availability_to_sheets(save_df):
                    st.success(f"✅ NA leads uitgeschakeld voor {selected_coach_toggle}")
                    st.rerun()
        else:
            st.warning(f"⚠️ {selected_coach_toggle} ontvangt momenteel GEEN NA leads")
            if st.button("🟢 NA leads AAN zetten", use_container_width=True):
                idx = merged_df[merged_df["Coachnaam"] == selected_coach_toggle].index[0]

                save_df = merged_df[["coach_id", "Coachnaam", "na_leads_aan", "afwezig_van", "afwezig_tot", "notitie"]].copy()
                save_df.loc[idx, "na_leads_aan"] = True
                save_df["laatst_gewijzigd"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                save_df["afwezig_van"] = save_df["afwezig_van"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")
                save_df["afwezig_tot"] = save_df["afwezig_tot"].apply(lambda x: str(x) if pd.notna(x) and x != "" else "")

                if save_availability_to_sheets(save_df):
                    st.success(f"✅ NA leads ingeschakeld voor {selected_coach_toggle}")
                    st.rerun()

    # ==================
    # SECTION 4: API ENDPOINT INFO
    # ==================
    st.markdown("---")
    st.markdown("## 🔌 N8N Integratie")

    with st.expander("Hoe koppel ik dit aan N8N?"):
        st.markdown(f"""
        **Google Sheet URL:** `{sheet_url}`

        In N8N kun je de Google Sheets node gebruiken om de beschikbaarheid te lezen:

        1. **Google Sheets node** toevoegen
        2. **Operation:** Read Rows
        3. **Document URL:** De Sheet URL hierboven
        4. **Sheet Name:** `Beschikbaarheid`

        **Filter in N8N:**
        ```javascript
        // Alleen beschikbare coaches
        items.filter(item => {{
            const naLeadsAan = item.json.na_leads_aan === true || item.json.na_leads_aan === "TRUE";
            const today = new Date().toISOString().split('T')[0];
            const afwezigVan = item.json.afwezig_van;
            const afwezigTot = item.json.afwezig_tot;

            // Check of niet afwezig
            let nietAfwezig = true;
            if (afwezigVan && afwezigTot) {{
                nietAfwezig = !(today >= afwezigVan && today <= afwezigTot);
            }}

            return naLeadsAan && nietAfwezig;
        }})
        ```

        Dit geeft je een lijst van coaches die:
        - NA leads aan hebben staan
        - Niet afwezig zijn vandaag
        """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    Coach Beschikbaarheid | Data opgeslagen in Google Sheets
</div>
""", unsafe_allow_html=True)
