import streamlit as st
import pandas as pd
import os
from pathlib import Path

st.set_page_config(
    page_title="NA_Pool Export - Nationale Apotheek",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import shared module (parent dir)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import shared

# ============================================================================
# GLOBAL SIDEBAR
# ============================================================================

ctx = shared.render_global_sidebar()
deals_col = ctx["deals_col"]
winrate_col = ctx["winrate_col"]
nabeller_col = ctx["nabeller_col"]
periode_label = ctx["periode_label"]
excluded_coaches = ctx["excluded_coaches"]

# ============================================================================
# PAGE-LOCAL SIDEBAR CONTROLS
# ============================================================================

st.sidebar.markdown("### 📤 NA_Pool Instellingen")

na_nabeller_threshold = st.sidebar.slider(
    "Nabeller % drempel",
    min_value=5, max_value=50, value=20, step=5,
    help="Coaches met nabeller % boven deze waarde worden uitgesloten",
    key="na_nabeller_threshold",
)

na_min_deals = st.sidebar.slider(
    f"Minimum deals ({periode_label})",
    min_value=1, max_value=30, value=5, step=1,
    help="Coaches met minder deals worden uitgesloten",
    key="na_min_deals",
)

na_top_percentage = st.sidebar.slider(
    "Top % coaches",
    min_value=10, max_value=100, value=100, step=5,
    help="Toon alleen de beste X% coaches op basis van winstpercentage",
    key="na_top_pct",
)

na_laag2_threshold = st.sidebar.slider(
    f"Minimum deals voor 'Goed'",
    min_value=1, max_value=30, value=14, step=1,
    help="Bepaalt Goed vs Matig status voor export",
    key="na_laag2_threshold",
)

# ============================================================================
# TITLE + BANNER
# ============================================================================

st.title("📤 NA_Pool Export")
st.markdown(f"*Push eligible coaches naar Google Sheets (NA_Pool tabblad) - Periode: **{periode_label}***")

extra_filters = {}
if na_nabeller_threshold != 20:
    extra_filters["Nabeller drempel"] = f"{na_nabeller_threshold}%"
if na_min_deals != 5:
    extra_filters["Min deals"] = str(na_min_deals)
if na_top_percentage < 100:
    extra_filters["Top %"] = f"{na_top_percentage}%"
if na_laag2_threshold != 14:
    extra_filters["Laag2 drempel"] = str(na_laag2_threshold)

shared.render_active_filters_banner(periode_label, excluded_coaches, extra_filters)

# ============================================================================
# DATA LOADING
# ============================================================================

try:
    base_df = shared.load_coach_data_raw()
except FileNotFoundError as e:
    st.error(f"❌ {e}")
    st.stop()

base_df = shared.apply_global_exclusions(base_df)

# ============================================================================
# CHECK GOOGLE SA
# ============================================================================

google_sa_path = os.environ.get("GOOGLE_SA_JSON_PATH")
google_sa_fallback = Path("secrets/service_account.json")
_has_streamlit_secret = False
try:
    _has_streamlit_secret = "gcp_service_account" in st.secrets
except Exception:
    pass

na_pool_enabled = bool(google_sa_path or google_sa_fallback.is_file() or _has_streamlit_secret)

if not na_pool_enabled:
    st.warning(
        "⚠️ **Google Service Account niet gevonden.**\n\n"
        "**Lokaal:** Plaats `service_account.json` in de `secrets/` map, of stel in met:\n"
        "```\nexport GOOGLE_SA_JSON_PATH=/pad/naar/service_account.json\n```\n"
        "**Streamlit Cloud:** Voeg `gcp_service_account` toe in Settings → Secrets."
    )

# ============================================================================
# PRE-FILTER: build set for median calculation
# ============================================================================

st.markdown("### ⚠️ Pre-filter samenvatting")

# Add nabeller_pct helper column
base_df["nabeller_pct"] = base_df[nabeller_col].fillna(0) if nabeller_col in base_df.columns else 0

# Pre-filter set for median
na_for_median_df = base_df[
    (base_df["nabeller_pct"] <= na_nabeller_threshold) &
    (base_df[deals_col] >= na_min_deals)
].copy()

# Apply top %
na_top_cutoff = None
if na_top_percentage < 100 and len(na_for_median_df) > 0:
    na_top_cutoff = na_for_median_df[winrate_col].quantile(1 - (na_top_percentage / 100))
    na_for_median_df = na_for_median_df[na_for_median_df[winrate_col] >= na_top_cutoff].copy()

# Dynamic median
na_mediaan = na_for_median_df[winrate_col].median() if len(na_for_median_df) > 0 else 0

# Show pre-filter summary
pf_col1, pf_col2, pf_col3 = st.columns(3)
with pf_col1:
    st.metric("Coaches in base set", len(base_df))
with pf_col2:
    st.metric("Na pre-filters", len(na_for_median_df))
with pf_col3:
    top_info = f" + top {na_top_percentage}%" if na_top_percentage < 100 else ""
    st.metric(f"Mediaan winst% ({periode_label})", f"{na_mediaan:.1f}%",
              help=f"Berekend op {len(na_for_median_df)} coaches na pre-filters{top_info}")

st.markdown("---")

# ============================================================================
# STATUS THRESHOLDS
# ============================================================================

st.markdown("### ⭐ Status Thresholds voor Export")

with st.expander("ℹ️ Hoe wordt status berekend voor export?"):
    st.markdown(f"""
    **De regels (voor {periode_label}):**

    ✅ **Goed** (wordt geëxporteerd) =
    - Minimaal **{na_laag2_threshold}** deals
    - Winstpercentage **≥ {na_mediaan:.1f}%** (mediaan)

    ⭐ **Matig** (wordt geëxporteerd) =
    - Minimaal **{na_laag2_threshold // 2}** deals
    - Winstpercentage **≥ {na_mediaan * 0.8:.1f}%** (80% van mediaan)

    ❌ **Uitsluiten** (wordt NIET geëxporteerd) =
    - Voldoet niet aan bovenstaande criteria

    🚫 **Nabeller te hoog** (wordt NIET geëxporteerd) =
    - Nabeller % > {na_nabeller_threshold}%

    ⚪ **Te weinig deals** (wordt NIET geëxporteerd) =
    - Minder dan {na_min_deals} deals in {periode_label}
    """)

# ============================================================================
# CALCULATE NA STATUS
# ============================================================================

na_base_df = base_df.copy()

def calculate_na_status(row):
    deals = row[deals_col]
    winrate = row[winrate_col]
    nabeller_pct = row.get("nabeller_pct", 0) or 0

    if nabeller_pct > na_nabeller_threshold:
        return "🚫 Nabeller te hoog"
    if deals < na_min_deals:
        return "⚪ Te weinig deals"
    if na_top_cutoff is not None and winrate < na_top_cutoff:
        return f"📉 Buiten top {na_top_percentage}%"
    if deals == 0:
        return "⚪ Geen data"
    if deals >= na_laag2_threshold and winrate >= na_mediaan:
        return "✅ Goed"
    if deals >= (na_laag2_threshold // 2) and winrate >= na_mediaan * 0.8:
        return "⭐ Matig"
    return "❌ Uitsluiten"

na_base_df["na_status"] = na_base_df.apply(calculate_na_status, axis=1)

# Eligible = Goed or Matig
na_eligible_df = na_base_df[na_base_df["na_status"].isin(["✅ Goed", "⭐ Matig"])].copy()

# Exclusion breakdown
na_nabeller_excluded = na_base_df[na_base_df["na_status"] == "🚫 Nabeller te hoog"]
na_too_few_deals = na_base_df[na_base_df["na_status"] == "⚪ Te weinig deals"]
na_below_top_pct = na_base_df[na_base_df["na_status"].str.contains("Buiten top", na=False)]

# Owner ID split
na_with_id = na_eligible_df[na_eligible_df["coach_id"].notna() & (na_eligible_df["coach_id"] != "")]
na_without_id = na_eligible_df[na_eligible_df["coach_id"].isna() | (na_eligible_df["coach_id"] == "")]

# ============================================================================
# SELECTION PREVIEW
# ============================================================================

st.markdown("### 📊 Selectie Preview")

na_status_counts = na_base_df["na_status"].value_counts()

st.markdown("**Status verdeling met huidige thresholds:**")
status_prev_cols = st.columns(min(len(na_status_counts), 4))
for i, (status, count) in enumerate(na_status_counts.items()):
    with status_prev_cols[i % len(status_prev_cols)]:
        is_eligible = status in ["✅ Goed", "⭐ Matig"]
        label = f"{status} {'→ export' if is_eligible else ''}"
        st.metric(label, count)

st.markdown("---")

prev_col1, prev_col2, prev_col3, prev_col4 = st.columns(4)
with prev_col1:
    st.metric("Eligible (Goed + Matig)", len(na_eligible_df))
with prev_col2:
    st.metric("Met owner_id", len(na_with_id))
with prev_col3:
    st.metric("Zonder owner_id (skip)", len(na_without_id))
with prev_col4:
    st.metric("Wordt geschreven", len(na_with_id))

# Exclusion details
if len(na_nabeller_excluded) > 0:
    with st.expander(f"🚫 {len(na_nabeller_excluded)} coach(es) uitgesloten: nabeller % > {na_nabeller_threshold}%"):
        for _, row in na_nabeller_excluded.iterrows():
            st.write(f"- {row['Coachnaam']} (nabeller: {row['nabeller_pct']:.1f}%)")

if len(na_too_few_deals) > 0:
    with st.expander(f"⚪ {len(na_too_few_deals)} coach(es) uitgesloten: < {na_min_deals} deals"):
        for _, row in na_too_few_deals.iterrows():
            st.write(f"- {row['Coachnaam']} ({row[deals_col]} deals)")

if len(na_below_top_pct) > 0:
    with st.expander(f"📉 {len(na_below_top_pct)} coach(es) uitgesloten: buiten top {na_top_percentage}%"):
        for _, row in na_below_top_pct.iterrows():
            st.write(f"- {row['Coachnaam']} (winst: {row[winrate_col]:.1f}%)")

if len(na_without_id) > 0:
    with st.expander(f"⚠️ {len(na_without_id)} coach(es) zonder owner_id worden geskipt"):
        for _, row in na_without_id.iterrows():
            st.write(f"- {row['Coachnaam']} (status: {row['na_status']})")

with st.expander(f"👁️ Preview: {len(na_eligible_df)} eligible coaches"):
    preview_cols = ["Coachnaam", "coach_id", deals_col, winrate_col, "nabeller_pct", "na_status"]
    preview_table = na_eligible_df[preview_cols].copy()
    preview_table = preview_table.sort_values(winrate_col, ascending=False)
    preview_table = preview_table.rename(columns={
        "Coachnaam": "Coach",
        "coach_id": "Owner ID",
        deals_col: "Deals",
        winrate_col: "Winst%",
        "nabeller_pct": "Nabeller%",
        "na_status": "Status",
    })
    st.dataframe(preview_table, use_container_width=True, hide_index=True)

# ============================================================================
# GOOGLE SHEETS PARAMETERS
# ============================================================================

st.markdown("---")
st.markdown("### ⚙️ Google Sheets Parameters")

na_col1, na_col2, na_col3 = st.columns(3)

with na_col1:
    na_cap_dag = st.number_input(
        "cap_dag", min_value=1, max_value=20, value=2, step=1,
        key="na_cap_dag",
        help="Maximum aantal leads per dag per coach",
    )

with na_col2:
    na_cap_week = st.number_input(
        "cap_week", min_value=1, max_value=50, value=14, step=1,
        key="na_cap_week",
        help="Maximum aantal leads per week per coach",
    )

with na_col3:
    na_weight = st.number_input(
        "weight", min_value=1, max_value=10, value=1, step=1,
        key="na_weight",
        help="Gewicht voor lead verdeling",
    )

# ============================================================================
# PUSH BUTTON
# ============================================================================

st.markdown("### 🚀 Push naar Google Sheets")

if na_pool_enabled:
    if st.button("Push NA_Pool naar Google Sheets", type="primary", key="push_na_pool"):
        try:
            from gsheets_writer import push_to_na_pool

            with st.spinner("Bezig met pushen naar Google Sheets..."):
                geschreven, geskipt, geskipte_namen = push_to_na_pool(
                    df=na_eligible_df,
                    weight=int(na_weight),
                    cap_dag=int(na_cap_dag),
                    cap_week=int(na_cap_week),
                )

            st.success(f"✅ **Push succesvol!**\n\n- Geschreven: {geschreven} coaches\n- Geskipt (geen owner_id): {geskipt}")

            if geskipte_namen:
                with st.expander("Geskipte coaches"):
                    for naam in geskipte_namen:
                        st.write(f"- {naam}")

            if geschreven > 0:
                st.markdown("#### Preview geschreven data (eerste 20 rijen)")
                preview_df = na_with_id.head(20)[["coach_id", "Coachnaam", winrate_col, "na_status"]].copy()
                preview_df["eligible"] = "JA"
                preview_df["weight"] = na_weight
                preview_df["cap_dag"] = na_cap_dag
                preview_df["cap_week"] = na_cap_week
                preview_df = preview_df.rename(columns={
                    "coach_id": "owner_id",
                    "Coachnaam": "coach_naam",
                    winrate_col: "winst%",
                    "na_status": "status",
                })
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                # Trigger Cloud Function refresh
                with st.spinner("Pool-refresh Cloud Function aanroepen..."):
                    try:
                        from gsheets_writer import trigger_na_pool_refresh
                        refresh_result = trigger_na_pool_refresh()

                        entries = refresh_result.get("entries", "?")
                        issues = refresh_result.get("issues", [])

                        if issues:
                            st.warning(
                                f"⚠️ **Pool-refresh afgerond** — {entries} entries, "
                                f"{len(issues)} issues"
                            )
                            with st.expander("Issues"):
                                for issue in issues:
                                    st.write(f"- {issue}")
                        else:
                            st.success(f"🔄 **Pool-refresh afgerond** — {entries} entries verwerkt")
                    except Exception as refresh_err:
                        st.warning(
                            f"⚠️ Push naar Sheets gelukt, maar pool-refresh mislukt: {refresh_err}"
                        )

        except Exception as e:
            st.error(f"❌ **Fout bij pushen:**\n\n{str(e)}")
else:
    st.button("Push NA_Pool naar Google Sheets", type="primary", disabled=True, key="push_na_pool_disabled")
    st.info("Stel GOOGLE_SA_JSON_PATH in om de push functie te activeren.")

# ============================================================================
# FOOTER
# ============================================================================

shared.render_footer("📤", "NA_Pool Export - Coach Dashboard")
