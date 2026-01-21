import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

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

def get_latest_data_file():
    """Find the most recent coach_eligibility file."""
    data_dir = Path("data")
    files = list(data_dir.glob("coach_eligibility_*.xlsx"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

@st.cache_data
def load_coach_data():
    """Load coaches data from Excel."""
    file_path = get_latest_data_file()
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
    file_path = get_latest_data_file()
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
    f"Minimum deals voor Laag 2",
    min_value=1,
    max_value=30,
    value=14,
    step=1,
    help=f"Coaches met minimaal dit aantal deals ({periode_label}) EN boven de mediaan krijgen status 'Laag 2'"
)

with st.sidebar.expander("ℹ️ Hoe wordt status berekend?"):
    st.markdown(f"""
    **De regels (voor {periode_label}):**

    ✅ **Laag 2** =
    - Minimaal **{laag2_threshold}** deals
    - Winstpercentage **≥ {selected_median:.1f}%** (mediaan)

    ⭐ **Laag 3** =
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
        return "✅ Laag 2"
    elif deals >= (laag2_threshold // 2) and winrate >= selected_median * 0.8:
        return "⭐ Laag 3"
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

col1, col2, col3, col4 = st.columns(4)

with col1:
    if len(threshold_df) > 0:
        avg_smoothed = threshold_df[winrate_col].mean()
        st.metric("Gem. winstpercentage", f"{avg_smoothed:.1f}%")
    else:
        st.metric("Gem. winstpercentage", "N/A")

with col2:
    if len(threshold_df) > 0:
        avg_deals = threshold_df[deals_col].mean()
        st.metric(f"Gem. deals", f"{avg_deals:.1f}")
    else:
        st.metric(f"Gem. deals", "N/A")

with col3:
    st.metric("Mediaan", f"{selected_median:.1f}%")

with col4:
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

# Add coaches below threshold (gray, smaller)
if len(below_threshold) > 0:
    fig_scatter.add_trace(go.Scatter(
        x=below_threshold[deals_col],
        y=below_threshold[winrate_col],
        mode='markers',
        name=f'Onder {min_deals} deals',
        marker=dict(
            size=8,
            color='lightgray',
            opacity=0.5
        ),
        text=below_threshold['Coachnaam'],
        hovertemplate='<b>%{text}</b><br>Deals: %{x}<br>Winst: %{y:.1f}%<br><i>(onder drempel)</i><extra></extra>'
    ))

# Add coaches above threshold (colored by status)
if len(above_threshold) > 0:
    for status in above_threshold['display_status'].unique():
        status_df = above_threshold[above_threshold['display_status'] == status]
        fig_scatter.add_trace(go.Scatter(
            x=status_df[deals_col],
            y=status_df[winrate_col],
            mode='markers',
            name=status,
            marker=dict(size=12),
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

fig_bar = px.bar(
    status_counts_chart,
    x='Status',
    y='Aantal',
    text='Aantal',
    color='Aantal',
    color_continuous_scale='Blues'
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
# FOOTER
# ============================================================================

st.markdown("---")
# Get data file info for footer
data_file = get_latest_data_file()
data_date = data_file.stem.split("_")[-2] if data_file else "onbekend"  # Extract YYYYMMDD from filename
if len(data_date) == 8:
    data_date = f"{data_date[6:8]}-{data_date[4:6]}-{data_date[:4]}"  # Format as DD-MM-YYYY

st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>💊 <b>Coach Prestatie Dashboard - Nationale Apotheek</b></p>
    <p>Data van {data_date} | Bestand: {data_file.name if data_file else 'onbekend'}</p>
    <p>📖 Klik op <b>Uitleg</b> in het linkermenu voor hulp</p>
</div>
""", unsafe_allow_html=True)
