import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import os

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Coach Prestatie Nationale Apotheek",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💊 Coach Prestatie Nationale Apotheek")
st.markdown("Bekijk coach prestaties over de afgelopen 1, 3 en 6 maanden")

# Help sectie - GROOT EN DUIDELIJK
st.markdown("""
<div style='background-color: #d4edda; padding: 20px; border-radius: 10px; text-align: center; margin: 10px 0;'>
    <h3 style='margin: 0; color: #155724;'>📖 HULP NODIG?</h3>
    <p style='margin: 10px 0 0 0; color: #155724;'>
        Klik links in het menu op <b>"📖 Uitleg"</b> voor een complete handleiding.
        <br>Zie je geen menu? Klik op het pijltje <b>></b> linksboven.
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING (CACHED)
# ============================================================================

def get_selected_data_file():
    """Get the selected data file from runs.json, or fall back to most recent run folder."""
    data_dir = Path("data")
    runs_file = data_dir / "runs.json"

    # Try to get selected run from runs.json
    if runs_file.is_file():
        try:
            with open(runs_file, "r") as f:
                runs_data = json.load(f)
            selected_id = runs_data.get("selected")
            if selected_id:
                # New structure: data/<run_id>/coach_eligibility.xlsx
                run_file = data_dir / selected_id / "coach_eligibility.xlsx"
                if run_file.is_file():
                    return run_file
        except:
            pass

    # Fallback: find most recent run folder
    run_dirs = [d for d in data_dir.iterdir()
                if d.is_dir() and len(d.name) == 15 and "_" in d.name]
    if run_dirs:
        run_dirs.sort(key=lambda p: p.name, reverse=True)
        for run_dir in run_dirs:
            eligibility_file = run_dir / "coach_eligibility.xlsx"
            if eligibility_file.is_file():
                return eligibility_file

    # Legacy fallback: old flat structure
    files = list(data_dir.glob("coach_eligibility_*.xlsx"))
    if files:
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]

    return None


def get_selected_run_id():
    """Get the currently selected run ID."""
    data_dir = Path("data")
    runs_file = data_dir / "runs.json"

    if runs_file.is_file():
        try:
            with open(runs_file, "r") as f:
                runs_data = json.load(f)
            return runs_data.get("selected")
        except:
            pass
    return None

@st.cache_data
def load_coach_data():
    """Load coaches data from Excel."""
    file_path = get_selected_data_file()
    if file_path is None:
        raise FileNotFoundError("No coach_eligibility_*.xlsx found in data/")
    df = pd.read_excel(file_path, sheet_name="Coaches")

    # Filter uit: Nabellers, programma's, gestopte accounts, onbekenden
    exclude_patterns = ['nabeller']
    exclude_exact = [
        'Rookvrij en Fitter Het Gooi',
        '167331984',
        'UNKNOWN',
        'benVitaal Coaching',
        'SportQube Algemeen'
    ]

    for pattern in exclude_patterns:
        df = df[~df['Coachnaam'].str.lower().str.contains(pattern, na=False)]
    df = df[~df['Coachnaam'].isin(exclude_exact)]

    return df

@st.cache_data
def load_deal_class_summary():
    """Load deal class summary for sanity checks."""
    file_path = get_selected_data_file()
    if file_path is None:
        raise FileNotFoundError("No coach_eligibility_*.xlsx found in data/")
    df = pd.read_excel(file_path, sheet_name="DealClassSummary")
    return df

# Load all data
try:
    coaches_df = load_coach_data()
    summary_df = load_deal_class_summary()
    data_loaded = True
except Exception as e:
    st.error(f"❌ Fout bij laden data: {e}")
    st.info("Zorg dat alle databestanden in de `data/` map staan")
    data_loaded = False
    st.stop()

# Mediaan wordt later berekend, na filters

# ============================================================================
# SIDEBAR: FILTERS
# ============================================================================

st.sidebar.header("🎯 Filters")

# ===================
# PERIODE SELECTIE - BELANGRIJKSTE KEUZE
# ===================
st.sidebar.markdown("### 📅 Periode")
st.sidebar.markdown("*Kies de periode voor ALLE grafieken en berekeningen*")

periode_keuze = st.sidebar.radio(
    "Selecteer periode",
    options=["1 maand", "3 maanden", "6 maanden"],
    index=0,
    horizontal=True
)

# Map keuze naar kolommen
periode_map = {
    "1 maand": {"deals": "deals_1m", "winrate": "smoothed_1m", "label": "1 maand"},
    "3 maanden": {"deals": "deals_3m", "winrate": "smoothed_3m", "label": "3 maanden"},
    "6 maanden": {"deals": "deals_6m", "winrate": "smoothed_6m", "label": "6 maanden"}
}

deals_col = periode_map[periode_keuze]["deals"]
winrate_col = periode_map[periode_keuze]["winrate"]
periode_label = periode_map[periode_keuze]["label"]

st.sidebar.success(f"📊 Alle data gebaseerd op: **{periode_label}**")

st.sidebar.markdown("---")

# ===================
# COACHES UITSLUITEN
# ===================
st.sidebar.markdown("### 🚫 Coaches Uitsluiten")

all_coaches = sorted(coaches_df['Coachnaam'].unique())

excluded_coaches = st.sidebar.multiselect(
    "Selecteer coaches om uit te sluiten",
    options=all_coaches,
    default=[],
    help="Deze coaches worden volledig verwijderd uit alle grafieken en berekeningen"
)

if excluded_coaches:
    coaches_df = coaches_df[~coaches_df['Coachnaam'].isin(excluded_coaches)].copy()
    st.sidebar.info(f"🚫 {len(excluded_coaches)} coach(es) uitgesloten")

st.sidebar.markdown("---")

# ===================
# TOP X% FILTER
# ===================
st.sidebar.markdown("### 🏆 Top Presteerders")

top_percentage = st.sidebar.slider(
    "Toon alleen top X%",
    min_value=10,
    max_value=100,
    value=100,
    step=5,
    help=f"Toon alleen de beste X% coaches op basis van winstpercentage ({periode_label})"
)

if top_percentage < 100:
    cutoff_value = coaches_df[winrate_col].quantile(1 - (top_percentage / 100))
    coaches_before = len(coaches_df)
    coaches_df = coaches_df[coaches_df[winrate_col] >= cutoff_value].copy()
    coaches_after = len(coaches_df)
    st.sidebar.info(f"📊 Toont {coaches_after} van {coaches_before} coaches\n\n**Minimum winst%:** {cutoff_value:.1f}%\n*(om in top {top_percentage}% te vallen)*")

st.sidebar.markdown("---")

# ===================
# MINIMUM DEALS VOOR WEERGAVE
# ===================
st.sidebar.markdown("### 🎚️ Minimum Deals")

min_deals = st.sidebar.slider(
    f"Minimum deals ({periode_label})",
    min_value=0,
    max_value=30,
    value=0,
    step=1,
    help="Coaches met minder deals worden grijs getoond in de grafieken"
)

st.sidebar.markdown("---")

# ===================
# MEDIAAN BEREKENING (voor geselecteerde periode)
# ===================
selected_median = coaches_df[winrate_col].median()

st.sidebar.markdown(f"### 📊 Mediaan ({periode_label})")
st.sidebar.metric("Mediaan winstpercentage", f"{selected_median:.1f}%")

st.sidebar.markdown("---")

# ===================
# DYNAMISCHE STATUS BEREKENING
# ===================
st.sidebar.markdown("### ⭐ Status Berekening")
st.sidebar.markdown(f"*Gebaseerd op {periode_label}*")

laag2_threshold = st.sidebar.slider(
    f"Minimum deals voor Goed",
    min_value=1,
    max_value=30,
    value=14,
    step=1,
    help=f"Coaches met minimaal dit aantal deals ({periode_label}) EN boven de mediaan krijgen status 'Goed'"
)

with st.sidebar.expander("ℹ️ Hoe wordt status berekend?"):
    st.markdown(f"""
    **De regels (voor {periode_label}):**

    ✅ **Goed** =
    - Minimaal **{laag2_threshold}** deals
    - Winstpercentage **≥ {selected_median:.1f}%** (mediaan)

    ⭐ **Matig** =
    - Minimaal **{laag2_threshold // 2}** deals
    - Winstpercentage **≥ {selected_median * 0.8:.1f}%** (80% van mediaan)

    ❌ **Uitsluiten** =
    - Voldoet niet aan bovenstaande

    ⚪ **Geen data** =
    - 0 deals in {periode_label}
    """)

# Recalculate status dynamically based on threshold AND selected period
def calculate_status(row):
    deals = row[deals_col]
    winrate = row[winrate_col]

    if deals == 0:
        return "⚪ Geen data"
    elif deals >= laag2_threshold and winrate >= selected_median:
        return "✅ Goed"
    elif deals >= (laag2_threshold // 2) and winrate >= selected_median * 0.8:
        return "⭐ Matig"
    else:
        return "❌ Uitsluiten"

# Apply dynamic status calculation
coaches_df['dynamic_status'] = coaches_df.apply(calculate_status, axis=1)

# Show impact
status_counts = coaches_df['dynamic_status'].value_counts()
st.sidebar.markdown("**Verdeling met huidige instelling:**")
for status, count in status_counts.items():
    st.sidebar.markdown(f"- {status}: **{count}**")

st.sidebar.markdown("---")

# ===================
# KEUZE: ORIGINELE OF DYNAMISCHE STATUS
# ===================
st.sidebar.markdown("### 📋 Status Weergave")
use_dynamic = st.sidebar.checkbox(
    "Gebruik dynamische status",
    value=True,
    help="Aan = status wordt herberekend op basis van je instellingen. Uit = originele status uit de data."
)

# Determine which status column to use
status_column = 'dynamic_status' if use_dynamic else 'eligibility'

# Get unique status values for filter
status_options = sorted(coaches_df[status_column].unique())
selected_statuses = st.sidebar.multiselect(
    "Toon alleen deze statussen",
    options=status_options,
    default=status_options,
    help="Filter op basis van coach status"
)

# Apply status filter
filtered_df = coaches_df[coaches_df[status_column].isin(selected_statuses)].copy()

# Add column to mark if coach meets minimum deals threshold (voor geselecteerde periode)
filtered_df['meets_threshold'] = filtered_df[deals_col] >= min_deals
filtered_df['display_status'] = filtered_df[status_column]

# Display filter info
st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Resultaten")
st.sidebar.metric("Coaches getoond", len(filtered_df))
st.sidebar.metric("Waarvan boven drempel", len(filtered_df[filtered_df['meets_threshold']]))

# Info over data filtering
with st.sidebar.expander("ℹ️ Uitgefilterde data"):
    st.markdown("""
    **Automatisch verwijderd:**
    - Nabellers (geen coaches)
    - Rookvrij en Fitter Het Gooi
    - 167331984 (onbekend)
    - UNKNOWN
    - benVitaal Coaching (gestopt)
    - SportQube Algemeen (doorstuur)
    """)

# ============================================================================
# MAIN METRICS (TOP CARDS)
# ============================================================================

st.markdown("---")
st.markdown(f"### 📊 Kerncijfers ({periode_label})")

# Only calculate metrics for coaches above threshold
threshold_df = filtered_df[filtered_df['meets_threshold']]

# Calculate total deals in sample (all filtered coaches, not just above threshold)
total_deals_sample = filtered_df[deals_col].sum()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Deals in sample", f"{int(total_deals_sample):,}".replace(",", "."))

with col2:
    if len(threshold_df) > 0:
        avg_smoothed = threshold_df[winrate_col].mean()
        st.metric("Gem. winstpercentage", f"{avg_smoothed:.1f}%")
    else:
        st.metric("Gem. winstpercentage", "N/A")

with col3:
    if len(threshold_df) > 0:
        avg_deals = threshold_df[deals_col].mean()
        st.metric(f"Gem. deals/coach", f"{avg_deals:.1f}")
    else:
        st.metric(f"Gem. deals/coach", "N/A")

with col4:
    st.metric("Mediaan", f"{selected_median:.1f}%")

with col5:
    if len(threshold_df) > 0:
        pct_above = (threshold_df[winrate_col] >= selected_median).sum() / len(threshold_df) * 100
        st.metric("% boven mediaan", f"{pct_above:.0f}%")
    else:
        st.metric("% boven mediaan", "N/A")

# ============================================================================
# SECTION 1: SCATTERPLOT - DEALS VS WINSTPERCENTAGE (GESELECTEERDE PERIODE)
# ============================================================================

st.markdown("---")
st.markdown(f"## 1️⃣ Deals vs Winstpercentage ({periode_label})")
st.markdown(f"""
*Elke stip is een coach. De **rode lijn** toont de mediaan ({selected_median:.1f}%).
De **blauwe lijn** toont je ingestelde minimum ({min_deals} deals).
Coaches onder de minimum worden lichter getoond.*
""")

# Split data into above and below threshold
above_threshold = filtered_df[filtered_df[deals_col] >= min_deals]
below_threshold = filtered_df[filtered_df[deals_col] < min_deals]

fig_scatter = go.Figure()

# Add coaches below threshold (blue, smaller)
if len(below_threshold) > 0:
    fig_scatter.add_trace(go.Scatter(
        x=below_threshold[deals_col],
        y=below_threshold[winrate_col],
        mode='markers',
        name=f'Onder {min_deals} deals',
        marker=dict(
            size=8,
            color='#007bff',  # blue
            opacity=0.7
        ),
        text=below_threshold['Coachnaam'],
        hovertemplate='<b>%{text}</b><br>Deals: %{x}<br>Winst: %{y:.1f}%<br><i>(onder drempel)</i><extra></extra>'
    ))

# Add coaches above threshold (colored by status)
status_colors = {
    "✅ Goed": "#28a745",       # green
    "⭐ Matig": "#ffc107",      # yellow
    "❌ Uitsluiten": "#dc3545", # red
    "⚠️ Uitsluiten": "#dc3545", # red
    "⚪ Geen data": "#6c757d",  # gray
}

if len(above_threshold) > 0:
    for status in above_threshold['display_status'].unique():
        status_df = above_threshold[above_threshold['display_status'] == status]
        fig_scatter.add_trace(go.Scatter(
            x=status_df[deals_col],
            y=status_df[winrate_col],
            mode='markers',
            name=status,
            marker=dict(size=12, color=status_colors.get(status, "#999999")),
            text=status_df['Coachnaam'],
            hovertemplate='<b>%{text}</b><br>Deals: %{x}<br>Winst: %{y:.1f}%<br>Status: ' + status + '<extra></extra>'
        ))

# Add median line (horizontal)
fig_scatter.add_hline(
    y=selected_median,
    line_dash="dash",
    line_color="red",
    line_width=2,
    annotation_text=f"Mediaan = {selected_median:.1f}%",
    annotation_position="right"
)

# Add minimum deals line (vertical)
if min_deals > 0:
    fig_scatter.add_vline(
        x=min_deals,
        line_dash="dot",
        line_color="blue",
        line_width=2,
        annotation_text=f"Min. {min_deals} deals",
        annotation_position="top"
    )

fig_scatter.update_layout(
    title=f"Deals vs Winstpercentage ({periode_label})",
    xaxis_title="Aantal Deals",
    yaxis_title="Winstpercentage (%)",
    height=550,
    hovermode='closest',
    plot_bgcolor='rgba(240,240,240,0.5)',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# SECTION 2: HISTOGRAM - VERDELING WINSTPERCENTAGE (GESELECTEERDE PERIODE)
# ============================================================================

st.markdown("---")
st.markdown(f"## 2️⃣ Verdeling Winstpercentage ({periode_label})")
st.markdown(f"*De **rode lijn** toont de mediaan ({selected_median:.1f}%). Links = onder gemiddeld, rechts = boven gemiddeld.*")

# Only include coaches above threshold
chart_data = filtered_df[filtered_df['meets_threshold']][winrate_col]

fig_hist = go.Figure()

fig_hist.add_trace(go.Histogram(
    x=chart_data,
    nbinsx=20,
    name=periode_label,
    marker_color='rgba(31, 119, 180, 0.7)',
    hovertemplate=f'<b>{periode_label}</b><br>Winstpercentage: %{{x:.1f}}%<br>Aantal coaches: %{{y}}<extra></extra>'
))

# Mediaan lijn
fig_hist.add_vline(
    x=selected_median,
    line_dash="dash",
    line_color="red",
    line_width=2,
    annotation_text=f"Mediaan = {selected_median:.1f}%",
    annotation_position="top right"
)

fig_hist.update_layout(
    title=f"Verdeling Winstpercentage ({periode_label})",
    xaxis_title="Winstpercentage (%)",
    yaxis_title="Aantal Coaches",
    height=450,
    showlegend=False,
    plot_bgcolor='rgba(240,240,240,0.5)'
)

st.plotly_chart(fig_hist, use_container_width=True)

# ============================================================================
# SECTION 3: STATUS VERDELING
# ============================================================================

st.markdown("---")
st.markdown("## 3️⃣ Aantal Coaches per Status")

status_counts_chart = filtered_df[filtered_df['meets_threshold']]['display_status'].value_counts().reset_index()
status_counts_chart.columns = ['Status', 'Aantal']

# Map status to colors
status_colors_bar = {
    "✅ Goed": "#28a745",       # green
    "⭐ Matig": "#ffc107",      # yellow
    "❌ Uitsluiten": "#dc3545", # red
    "⚠️ Uitsluiten": "#dc3545", # red
    "⚪ Geen data": "#6c757d",  # gray
}
status_counts_chart['Color'] = status_counts_chart['Status'].map(lambda s: status_colors_bar.get(s, "#999999"))

fig_bar = px.bar(
    status_counts_chart,
    x='Status',
    y='Aantal',
    text='Aantal',
    color='Status',
    color_discrete_map=status_colors_bar
)

fig_bar.update_traces(
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>Aantal coaches: %{y}<extra></extra>'
)

fig_bar.update_layout(
    title="Aantal Coaches per Status",
    xaxis_title="Status",
    yaxis_title="Aantal Coaches",
    height=400,
    showlegend=False
)

st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# SECTION 4: TABEL MET ALLE COACHES
# ============================================================================

st.markdown("---")
st.markdown(f"## 📋 Overzicht Alle Coaches ({periode_label})")
st.markdown("*Gesorteerd op winstpercentage (hoogste eerst). Klik op een kolomkop om anders te sorteren.*")

# Legenda
st.markdown(f"""
<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
<b>Geselecteerde periode:</b> {periode_label} | <b>Mediaan:</b> {selected_median:.1f}% | ⚪ = onder minimum deals drempel
</div>
""", unsafe_allow_html=True)

# Prepare table data - alleen geselecteerde periode
table_cols = [
    'Coachnaam', 'display_status',
    deals_col, winrate_col,
    'meets_threshold'
]

table_df = filtered_df[table_cols].copy()
table_df = table_df.sort_values(winrate_col, ascending=False)

# Rename columns dynamisch
table_df = table_df.rename(columns={
    'Coachnaam': 'Coach',
    'display_status': 'Status',
    deals_col: 'Deals',
    winrate_col: 'Winst%',
    'meets_threshold': 'Boven drempel'
})

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    height=600,
    column_config={
        "Coach": st.column_config.TextColumn(width="large"),
        "Status": st.column_config.TextColumn(width="small"),
        "Deals": st.column_config.NumberColumn(format="%d", help=f"Aantal deals ({periode_label})"),
        "Winst%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, help=f"Winstpercentage ({periode_label})"),
        "Boven drempel": st.column_config.CheckboxColumn(help=f"✅ = meer dan {min_deals} deals")
    }
)

# ============================================================================
# SECTION 5: NA_POOL EXPORT
# ============================================================================

st.markdown("---")
st.markdown("## 📤 NA_Pool Export")
st.markdown(f"*Push eligible coaches naar Google Sheets (NA_Pool tabblad) - Periode: **{periode_label}***")

# Check if Google Service Account is available (file, env var, or Streamlit secrets)
google_sa_path = os.environ.get("GOOGLE_SA_JSON_PATH")
google_sa_fallback = Path("secrets/service_account.json")
_has_streamlit_secret = False
try:
    _has_streamlit_secret = "gcp_service_account" in st.secrets
except Exception:
    pass

if not google_sa_path and not google_sa_fallback.is_file() and not _has_streamlit_secret:
    st.warning(
        "⚠️ **Google Service Account niet gevonden.**\n\n"
        "**Lokaal:** Plaats `service_account.json` in de `secrets/` map, of stel in met:\n"
        "```\nexport GOOGLE_SA_JSON_PATH=/pad/naar/service_account.json\n```\n"
        "**Streamlit Cloud:** Voeg `gcp_service_account` toe in Settings → Secrets."
    )
    na_pool_enabled = False
else:
    na_pool_enabled = True

# ===================
# Alert Thresholds (zelfde als Week Monitor) - EERST deze, want ze beïnvloeden de mediaan
# ===================
st.markdown("### ⚠️ Pre-filters (beïnvloeden mediaan)")
st.markdown("**Let op:** Deze sliders bepalen welke coaches meetellen voor de mediaan berekening hieronder.")

na_alert_col1, na_alert_col2, na_alert_col3 = st.columns(3)

with na_alert_col1:
    na_nabeller_threshold = st.slider(
        "Nabeller % drempel",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        key="na_pool_nabeller_threshold",
        help="Coaches met nabeller % boven deze waarde worden uitgesloten"
    )

with na_alert_col2:
    na_won_rate_drop = st.slider(
        "Won rate daling drempel",
        min_value=5,
        max_value=30,
        value=15,
        step=5,
        key="na_pool_won_rate_drop",
        help="Coaches met won rate die meer dan X% onder 4-weeks gemiddelde ligt worden gemarkeerd"
    )

with na_alert_col3:
    na_min_deals_week = st.slider(
        "Minimum deals",
        min_value=1,
        max_value=15,
        value=5,
        step=1,
        key="na_pool_min_deals_week",
        help="Coaches met minder deals worden uitgesloten"
    )

st.markdown("---")

# ===================
# Pre-filter data based on alert thresholds to calculate dynamic median
# ===================

# Get base data (with standard excludes applied)
@st.cache_data
def get_base_coaches_for_export_cached():
    """Get coaches with standard excludes applied."""
    file_path = get_selected_data_file()
    if file_path is None:
        return pd.DataFrame()
    df = pd.read_excel(file_path, sheet_name="Coaches")

    # Apply same exclude patterns as main dashboard
    exclude_patterns = ['nabeller']
    exclude_exact = [
        'Rookvrij en Fitter Het Gooi',
        '167331984',
        'UNKNOWN',
        'benVitaal Coaching',
        'SportQube Algemeen'
    ]
    for pattern in exclude_patterns:
        df = df[~df['Coachnaam'].str.lower().str.contains(pattern, na=False)]
    df = df[~df['Coachnaam'].isin(exclude_exact)]

    return df

# Get base data and apply manual excludes from sidebar
na_prefilter_df = get_base_coaches_for_export_cached().copy()
if excluded_coaches:
    na_prefilter_df = na_prefilter_df[~na_prefilter_df['Coachnaam'].isin(excluded_coaches)].copy()

# Determine nabeller column based on selected period
nabeller_col_map = {
    "1 maand": "nabeller_pct_1m",
    "3 maanden": "nabeller_pct_3m",
    "6 maanden": "nabeller_pct_6m"
}
nabeller_col = nabeller_col_map.get(periode_keuze, "nabeller_pct_1m")

# Apply pre-filters: nabeller threshold and minimum deals
# These coaches are used for median calculation
na_prefilter_df['nabeller_pct'] = na_prefilter_df[nabeller_col].fillna(0)
na_for_median_df = na_prefilter_df[
    (na_prefilter_df['nabeller_pct'] <= na_nabeller_threshold) &
    (na_prefilter_df[deals_col] >= na_min_deals_week)
].copy()

# Apply Top % filter from sidebar (same as main dashboard)
if top_percentage < 100 and len(na_for_median_df) > 0:
    na_top_cutoff = na_for_median_df[winrate_col].quantile(1 - (top_percentage / 100))
    na_for_median_df = na_for_median_df[na_for_median_df[winrate_col] >= na_top_cutoff].copy()

# Calculate DYNAMIC mediaan on pre-filtered data (after top % filter)
na_mediaan = na_for_median_df[winrate_col].median() if len(na_for_median_df) > 0 else 0

# ===================
# NA_Pool Status Thresholds
# ===================
st.markdown("### ⭐ Status Thresholds voor Export")
top_info = f" + top {top_percentage}%" if top_percentage < 100 else ""
st.markdown(f"*Mediaan berekend op **{len(na_for_median_df)} coaches** na pre-filters{top_info}*")

na_thresh_col1, na_thresh_col2 = st.columns(2)

with na_thresh_col1:
    na_laag2_threshold = st.slider(
        f"Minimum deals voor 'Goed' ({periode_label})",
        min_value=1,
        max_value=30,
        value=14,
        step=1,
        key="na_pool_laag2_threshold",
        help="Bepaalt Goed vs Matig status. Verandert de mediaan NIET - gebruik pre-filters hierboven."
    )

with na_thresh_col2:
    # Show DYNAMIC mediaan
    st.metric(f"Mediaan winst% ({periode_label})", f"{na_mediaan:.1f}%",
              help="Pas de pre-filters hierboven aan om de mediaan te wijzigen")

# Uitleg status berekening
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
    - Minder dan {na_min_deals_week} deals in {periode_label}
    """)

st.markdown("---")

# ===================
# Google Sheets Parameters
# ===================
st.markdown("### ⚙️ Google Sheets Parameters")

na_col1, na_col2, na_col3 = st.columns(3)

with na_col1:
    na_cap_dag = st.number_input(
        "cap_dag",
        min_value=1,
        max_value=20,
        value=2,
        step=1,
        key="na_pool_cap_dag",
        help="Maximum aantal leads per dag per coach"
    )

with na_col2:
    na_cap_week = st.number_input(
        "cap_week",
        min_value=1,
        max_value=50,
        value=14,
        step=1,
        key="na_pool_cap_week",
        help="Maximum aantal leads per week per coach"
    )

with na_col3:
    na_weight = st.number_input(
        "weight",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        key="na_pool_weight",
        help="Gewicht voor lead verdeling"
    )

# ===================
# Calculate eligible coaches using dynamic mediaan
# ===================

# Use pre-filtered data (na_prefilter_df already has excludes and nabeller_pct column)
na_base_df = na_prefilter_df.copy()

# Calculate top % cutoff for status calculation
na_top_cutoff = None
if top_percentage < 100 and len(na_base_df) > 0:
    na_top_cutoff = na_base_df[winrate_col].quantile(1 - (top_percentage / 100))

# Apply dynamic status calculation for NA_Pool
# Uses the DYNAMIC mediaan calculated on pre-filtered data
def calculate_na_status(row):
    deals = row[deals_col]
    winrate = row[winrate_col]
    nabeller_pct = row.get('nabeller_pct', 0) or 0

    # First check: nabeller % too high -> exclude
    if nabeller_pct > na_nabeller_threshold:
        return "🚫 Nabeller te hoog"

    # Second check: not enough deals for meaningful data
    if deals < na_min_deals_week:
        return "⚪ Te weinig deals"

    # Third check: below top X% threshold
    if na_top_cutoff is not None and winrate < na_top_cutoff:
        return f"📉 Buiten top {top_percentage}%"

    if deals == 0:
        return "⚪ Geen data"
    elif deals >= na_laag2_threshold and winrate >= na_mediaan:
        return "✅ Goed"
    elif deals >= (na_laag2_threshold // 2) and winrate >= na_mediaan * 0.8:
        return "⭐ Matig"
    else:
        return "❌ Uitsluiten"

na_base_df['na_status'] = na_base_df.apply(calculate_na_status, axis=1)

# Select only eligible coaches (Goed or Matig)
na_eligible_df = na_base_df[na_base_df['na_status'].isin(['✅ Goed', '⭐ Matig'])].copy()

# Count coaches excluded by various filters
na_nabeller_excluded = na_base_df[na_base_df['na_status'] == '🚫 Nabeller te hoog']
na_too_few_deals = na_base_df[na_base_df['na_status'] == '⚪ Te weinig deals']
na_below_top_pct = na_base_df[na_base_df['na_status'].str.contains('Buiten top', na=False)]

# Count coaches with and without owner_id
na_with_id = na_eligible_df[na_eligible_df['coach_id'].notna() & (na_eligible_df['coach_id'] != '')]
na_without_id = na_eligible_df[na_eligible_df['coach_id'].isna() | (na_eligible_df['coach_id'] == '')]

# Status counts
na_status_counts = na_base_df['na_status'].value_counts()

# ===================
# Show Preview
# ===================
st.markdown("### 📊 Selectie Preview")

# Show status distribution
st.markdown("**Status verdeling met huidige thresholds:**")
status_prev_cols = st.columns(4)
for i, (status, count) in enumerate(na_status_counts.items()):
    with status_prev_cols[i % 4]:
        is_eligible = status in ['✅ Goed', '⭐ Matig']
        label = f"{status} {'→ export' if is_eligible else ''}"
        st.metric(label, count)

st.markdown("---")

# Summary metrics
prev_col1, prev_col2, prev_col3, prev_col4 = st.columns(4)
with prev_col1:
    st.metric("Eligible (Goed + Matig)", len(na_eligible_df))
with prev_col2:
    st.metric("Met owner_id", len(na_with_id))
with prev_col3:
    st.metric("Zonder owner_id (skip)", len(na_without_id))
with prev_col4:
    st.metric("Wordt geschreven", len(na_with_id))

# Show coaches excluded by nabeller threshold
if len(na_nabeller_excluded) > 0:
    with st.expander(f"🚫 {len(na_nabeller_excluded)} coach(es) uitgesloten: nabeller % > {na_nabeller_threshold}%"):
        for _, row in na_nabeller_excluded.iterrows():
            st.write(f"- {row['Coachnaam']} (nabeller: {row['nabeller_pct']:.1f}%)")

# Show coaches with too few deals
if len(na_too_few_deals) > 0:
    with st.expander(f"⚪ {len(na_too_few_deals)} coach(es) uitgesloten: < {na_min_deals_week} deals"):
        for _, row in na_too_few_deals.iterrows():
            st.write(f"- {row['Coachnaam']} ({row[deals_col]} deals)")

# Show coaches below top X%
if len(na_below_top_pct) > 0:
    with st.expander(f"📉 {len(na_below_top_pct)} coach(es) uitgesloten: buiten top {top_percentage}%"):
        for _, row in na_below_top_pct.iterrows():
            st.write(f"- {row['Coachnaam']} (winst: {row[winrate_col]:.1f}%)")

# Show skipped coaches if any
if len(na_without_id) > 0:
    with st.expander(f"⚠️ {len(na_without_id)} coach(es) zonder owner_id worden geskipt"):
        for _, row in na_without_id.iterrows():
            st.write(f"- {row['Coachnaam']} (status: {row['na_status']})")

# Show preview table of eligible coaches
with st.expander(f"👁️ Preview: {len(na_eligible_df)} eligible coaches"):
    preview_table = na_eligible_df[['Coachnaam', 'coach_id', deals_col, winrate_col, 'nabeller_pct', 'na_status']].copy()
    preview_table = preview_table.sort_values(winrate_col, ascending=False)
    preview_table = preview_table.rename(columns={
        'Coachnaam': 'Coach',
        'coach_id': 'Owner ID',
        deals_col: 'Deals',
        winrate_col: 'Winst%',
        'nabeller_pct': 'Nabeller%',
        'na_status': 'Status'
    })
    st.dataframe(preview_table, use_container_width=True, hide_index=True)

# ===================
# Push Button
# ===================
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
                    cap_week=int(na_cap_week)
                )

            st.success(f"✅ **Push succesvol!**\n\n- Geschreven: {geschreven} coaches\n- Geskipt (geen owner_id): {geskipt}")

            if geskipte_namen:
                with st.expander("Geskipte coaches"):
                    for naam in geskipte_namen:
                        st.write(f"- {naam}")

            # Show preview of written data
            if geschreven > 0:
                st.markdown("#### Preview geschreven data (eerste 20 rijen)")
                preview_df = na_with_id.head(20)[['coach_id', 'Coachnaam', winrate_col, 'na_status']].copy()
                preview_df['eligible'] = 'JA'
                preview_df['weight'] = na_weight
                preview_df['cap_dag'] = na_cap_dag
                preview_df['cap_week'] = na_cap_week
                preview_df = preview_df.rename(columns={
                    'coach_id': 'owner_id',
                    'Coachnaam': 'coach_naam',
                    winrate_col: 'winst%',
                    'na_status': 'status'
                })
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                # Trigger Cloud Function refresh
                with st.spinner("Pool-refresh Cloud Function aanroepen..."):
                    try:
                        from gsheets_writer import trigger_na_pool_refresh
                        refresh_result = trigger_na_pool_refresh()

                        entries = refresh_result.get('entries', '?')
                        issues = refresh_result.get('issues', [])

                        if issues:
                            st.warning(
                                f"⚠️ **Pool-refresh afgerond** — {entries} entries, "
                                f"{len(issues)} issues"
                            )
                            with st.expander("Issues"):
                                for issue in issues:
                                    st.write(f"- {issue}")
                        else:
                            st.success(
                                f"🔄 **Pool-refresh afgerond** — {entries} entries verwerkt"
                            )
                    except Exception as refresh_err:
                        st.warning(
                            f"⚠️ Push naar Sheets gelukt, maar pool-refresh mislukt: "
                            f"{refresh_err}"
                        )

        except Exception as e:
            st.error(f"❌ **Fout bij pushen:**\n\n{str(e)}")
else:
    st.button("Push NA_Pool naar Google Sheets", type="primary", disabled=True, key="push_na_pool_disabled")
    st.info("Stel GOOGLE_SA_JSON_PATH in om de push functie te activeren.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
# Get data file info for footer
run_id = get_selected_run_id()
if run_id and len(run_id) == 15:
    # Parse run_id format: YYYYMMDD_HHMMSS
    data_date = f"{run_id[6:8]}-{run_id[4:6]}-{run_id[:4]}"
    data_time = f"{run_id[9:11]}:{run_id[11:13]}"
    run_info = f"Run: {data_date} {data_time}"
else:
    run_info = "Run: onbekend"

st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>💊 <b>Coach Prestatie Dashboard - Nationale Apotheek</b></p>
    <p>{run_info} | 🔄 <a href="/Data_Beheer" target="_self">Data Beheer</a></p>
    <p>📖 Klik op <b>Uitleg</b> in het linkermenu voor hulp</p>
</div>
""", unsafe_allow_html=True)
