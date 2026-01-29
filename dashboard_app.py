import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import shared

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Coach Prestatie Nationale Apotheek",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💊 Coach Prestatie Nationale Apotheek")
st.markdown("Bekijk coach prestaties over de afgelopen 1, 3 en 6 maanden")

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
# GLOBAL SIDEBAR (period + coach exclusion)
# ============================================================================

ctx = shared.render_global_sidebar()
deals_col = ctx["deals_col"]
winrate_col = ctx["winrate_col"]
periode_label = ctx["periode_label"]
excluded_coaches = ctx["excluded_coaches"]
warme_col = ctx["warme_col"]
info_col = ctx["info_col"]

# ============================================================================
# LOCAL SIDEBAR CONTROLS
# ============================================================================

st.sidebar.markdown("### 🎚️ Dashboard Filters")

min_deals = st.sidebar.slider(
    f"Minimum deals ({periode_label})",
    min_value=0, max_value=30, value=0, step=1,
    help="Coaches met minder deals worden grijs getoond in de grafieken",
)

min_conversie = st.sidebar.slider(
    f"Minimum conversie % ({periode_label})",
    min_value=0, max_value=50, value=0, step=5,
    help="Coaches onder deze conversie worden uitgesloten uit de sample",
)

top_percentage = st.sidebar.slider(
    "Top % coaches",
    min_value=10, max_value=100, value=100, step=5,
    help=f"Toon alleen de beste X% coaches op basis van winstpercentage ({periode_label})",
)

# ============================================================================
# DATA LOADING
# ============================================================================

try:
    coaches_df = shared.load_coach_data_raw()
    data_loaded = True
except FileNotFoundError as e:
    st.error(f"❌ Fout bij laden data: {e}")
    st.info("Zorg dat alle databestanden in de `data/` map staan")
    st.stop()

# Apply global exclusions
coaches_df = shared.apply_global_exclusions(coaches_df)

# Apply minimum conversie filter
if min_conversie > 0:
    coaches_before_conv = len(coaches_df)
    coaches_df = coaches_df[coaches_df[winrate_col] >= min_conversie].copy()
    coaches_after_conv = len(coaches_df)
    if coaches_after_conv < coaches_before_conv:
        st.sidebar.info(
            f"📉 {coaches_before_conv - coaches_after_conv} coach(es) "
            f"uitgesloten (conversie < {min_conversie}%)"
        )

# Apply top % filter
if top_percentage < 100 and len(coaches_df) > 0:
    cutoff_value = coaches_df[winrate_col].quantile(1 - (top_percentage / 100))
    coaches_before = len(coaches_df)
    coaches_df = coaches_df[coaches_df[winrate_col] >= cutoff_value].copy()
    coaches_after = len(coaches_df)
    st.sidebar.info(
        f"📊 Toont {coaches_after} van {coaches_before} coaches\n\n"
        f"**Minimum winst%:** {cutoff_value:.1f}%\n"
        f"*(om in top {top_percentage}% te vallen)*"
    )

# ============================================================================
# DYNAMIC STATUS CALCULATION (always dynamic, no toggle)
# ============================================================================

selected_median = coaches_df[winrate_col].median() if len(coaches_df) > 0 else 0

# Use laag2 = 14 as default for dashboard status
LAAG2_DEFAULT = 14

def calculate_status(row):
    deals = row[deals_col]
    winrate = row[winrate_col]
    if deals == 0:
        return "⚪ Geen data"
    elif deals >= LAAG2_DEFAULT and winrate >= selected_median:
        return "✅ Goed"
    elif deals >= (LAAG2_DEFAULT // 2) and winrate >= selected_median * 0.8:
        return "⭐ Matig"
    else:
        return "❌ Uitsluiten"

coaches_df["display_status"] = coaches_df.apply(calculate_status, axis=1)
coaches_df["meets_threshold"] = coaches_df[deals_col] >= min_deals

# Sidebar summary
st.sidebar.markdown("---")
st.sidebar.markdown(f"### 📊 Mediaan ({periode_label})")
st.sidebar.metric("Mediaan winstpercentage", f"{selected_median:.1f}%")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Resultaten")
st.sidebar.metric("Coaches getoond", len(coaches_df))
st.sidebar.metric("Waarvan boven drempel", len(coaches_df[coaches_df["meets_threshold"]]))

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
# FILTER BANNER
# ============================================================================

extra_filters = {}
if min_deals > 0:
    extra_filters["Min deals"] = str(min_deals)
if min_conversie > 0:
    extra_filters["Min conversie"] = f"{min_conversie}%"
if top_percentage < 100:
    extra_filters["Top %"] = f"{top_percentage}%"

shared.render_active_filters_banner(periode_label, excluded_coaches, extra_filters)

# ============================================================================
# MAIN METRICS (TOP CARDS)
# ============================================================================

st.markdown(f"### 📊 Kerncijfers ({periode_label})")

threshold_df = coaches_df[coaches_df["meets_threshold"]]
total_deals_sample = coaches_df[deals_col].sum()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Deals in sample", f"{int(total_deals_sample):,}".replace(",", "."))
with col2:
    if len(threshold_df) > 0:
        st.metric("Gem. winstpercentage", f"{threshold_df[winrate_col].mean():.1f}%")
    else:
        st.metric("Gem. winstpercentage", "N/A")
with col3:
    if len(threshold_df) > 0:
        st.metric("Gem. deals/coach", f"{threshold_df[deals_col].mean():.1f}")
    else:
        st.metric("Gem. deals/coach", "N/A")
with col4:
    st.metric("Mediaan", f"{selected_median:.1f}%")
with col5:
    if len(threshold_df) > 0:
        pct_above = (threshold_df[winrate_col] >= selected_median).sum() / len(threshold_df) * 100
        st.metric("% boven mediaan", f"{pct_above:.0f}%")
    else:
        st.metric("% boven mediaan", "N/A")

# ============================================================================
# SECTION 1: SCATTERPLOT
# ============================================================================

st.markdown("---")
st.markdown(f"## 1️⃣ Deals vs Winstpercentage ({periode_label})")
st.markdown(f"""
*Elke stip is een coach. De **rode lijn** toont de mediaan ({selected_median:.1f}%).
De **blauwe lijn** toont je ingestelde minimum ({min_deals} deals).
Coaches onder de minimum worden lichter getoond.*
""")

above_threshold = coaches_df[coaches_df[deals_col] >= min_deals]
below_threshold = coaches_df[coaches_df[deals_col] < min_deals]

fig_scatter = go.Figure()

if len(below_threshold) > 0:
    fig_scatter.add_trace(go.Scatter(
        x=below_threshold[deals_col],
        y=below_threshold[winrate_col],
        mode="markers",
        name=f"Onder {min_deals} deals",
        marker=dict(size=8, color="#007bff", opacity=0.7),
        text=below_threshold["Coachnaam"],
        hovertemplate="<b>%{text}</b><br>Deals: %{x}<br>Winst: %{y:.1f}%<br><i>(onder drempel)</i><extra></extra>",
    ))

if len(above_threshold) > 0:
    for status in above_threshold["display_status"].unique():
        status_df = above_threshold[above_threshold["display_status"] == status]
        fig_scatter.add_trace(go.Scatter(
            x=status_df[deals_col],
            y=status_df[winrate_col],
            mode="markers",
            name=status,
            marker=dict(size=12, color=shared.STATUS_COLORS.get(status, "#999999")),
            text=status_df["Coachnaam"],
            hovertemplate="<b>%{text}</b><br>Deals: %{x}<br>Winst: %{y:.1f}%<br>Status: " + status + "<extra></extra>",
        ))

fig_scatter.add_hline(
    y=selected_median, line_dash="dash", line_color="red", line_width=2,
    annotation_text=f"Mediaan = {selected_median:.1f}%", annotation_position="right",
)

if min_deals > 0:
    fig_scatter.add_vline(
        x=min_deals, line_dash="dot", line_color="blue", line_width=2,
        annotation_text=f"Min. {min_deals} deals", annotation_position="top",
    )

fig_scatter.update_layout(
    title=f"Deals vs Winstpercentage ({periode_label})",
    xaxis_title="Aantal Deals", yaxis_title="Winstpercentage (%)",
    height=550, hovermode="closest",
    plot_bgcolor="rgba(240,240,240,0.5)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# SECTION 2: HISTOGRAM
# ============================================================================

st.markdown("---")
st.markdown(f"## 2️⃣ Verdeling Winstpercentage ({periode_label})")
st.markdown(f"*De **rode lijn** toont de mediaan ({selected_median:.1f}%). Links = onder gemiddeld, rechts = boven gemiddeld.*")

chart_data = coaches_df[coaches_df["meets_threshold"]][winrate_col]

fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(
    x=chart_data, nbinsx=20, name=periode_label,
    marker_color="rgba(31, 119, 180, 0.7)",
    hovertemplate=f"<b>{periode_label}</b><br>Winstpercentage: %{{x:.1f}}%<br>Aantal coaches: %{{y}}<extra></extra>",
))
fig_hist.add_vline(
    x=selected_median, line_dash="dash", line_color="red", line_width=2,
    annotation_text=f"Mediaan = {selected_median:.1f}%", annotation_position="top right",
)
fig_hist.update_layout(
    title=f"Verdeling Winstpercentage ({periode_label})",
    xaxis_title="Winstpercentage (%)", yaxis_title="Aantal Coaches",
    height=450, showlegend=False, plot_bgcolor="rgba(240,240,240,0.5)",
)

st.plotly_chart(fig_hist, use_container_width=True)

# ============================================================================
# SECTION 3: STATUS VERDELING
# ============================================================================

st.markdown("---")
st.markdown("## 3️⃣ Aantal Coaches per Status")

status_counts_chart = coaches_df[coaches_df["meets_threshold"]]["display_status"].value_counts().reset_index()
status_counts_chart.columns = ["Status", "Aantal"]

fig_bar = px.bar(
    status_counts_chart, x="Status", y="Aantal", text="Aantal",
    color="Status", color_discrete_map=shared.STATUS_COLORS,
)
fig_bar.update_traces(textposition="outside", hovertemplate="<b>%{x}</b><br>Aantal coaches: %{y}<extra></extra>")
fig_bar.update_layout(
    title="Aantal Coaches per Status",
    xaxis_title="Status", yaxis_title="Aantal Coaches",
    height=400, showlegend=False,
)

st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# SECTION 4: COACH TABLE
# ============================================================================

st.markdown("---")
st.markdown(f"## 📋 Overzicht Alle Coaches ({periode_label})")
st.markdown("*Gesorteerd op winstpercentage (hoogste eerst). Klik op een kolomkop om anders te sorteren.*")

st.markdown(f"""
<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
<b>Geselecteerde periode:</b> {periode_label} | <b>Mediaan:</b> {selected_median:.1f}% | ⚪ = onder minimum deals drempel
</div>
""", unsafe_allow_html=True)

# Build table columns — include warme/info if available
table_cols = ["Coachnaam", "display_status", deals_col, winrate_col, "meets_threshold"]

has_warme = warme_col in coaches_df.columns
has_info = info_col in coaches_df.columns
if has_warme:
    table_cols.insert(4, warme_col)
if has_info:
    table_cols.insert(5 if has_warme else 4, info_col)

table_df = coaches_df[table_cols].copy()
table_df = table_df.sort_values(winrate_col, ascending=False)

rename_map = {
    "Coachnaam": "Coach",
    "display_status": "Status",
    deals_col: "Deals",
    winrate_col: "Winst%",
    "meets_threshold": "Boven drempel",
}
if has_warme:
    rename_map[warme_col] = "Warme aanvraag"
if has_info:
    rename_map[info_col] = "Info aanvraag"

table_df = table_df.rename(columns=rename_map)

col_config = {
    "Coach": st.column_config.TextColumn(width="large"),
    "Status": st.column_config.TextColumn(width="small"),
    "Deals": st.column_config.NumberColumn(format="%d", help=f"Aantal deals ({periode_label})"),
    "Winst%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, help=f"Winstpercentage ({periode_label})"),
    "Boven drempel": st.column_config.CheckboxColumn(help=f"✅ = meer dan {min_deals} deals"),
}
if has_warme:
    col_config["Warme aanvraag"] = st.column_config.NumberColumn(format="%d", help=f"Warme aanvragen ({periode_label})")
if has_info:
    col_config["Info aanvraag"] = st.column_config.NumberColumn(format="%d", help=f"Info aanvragen ({periode_label})")

# For old data runs that don't have warme/info columns, show N/B
if not has_warme and "Warme aanvraag" not in table_df.columns:
    pass  # Column simply not shown
if not has_info and "Info aanvraag" not in table_df.columns:
    pass  # Column simply not shown

st.dataframe(
    table_df, use_container_width=True, hide_index=True,
    height=600, column_config=col_config,
)

# ============================================================================
# FOOTER
# ============================================================================

shared.render_footer("💊", "Coach Prestatie Dashboard - Nationale Apotheek")
