import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Week Monitor - Nationale Apotheek",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Week Monitor")

# Import shared module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import shared

# ============================================================================
# WARNING BANNER
# ============================================================================

st.markdown("""
<div style='background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px;'>
    <h3 style='margin: 0 0 10px 0; color: #856404;'>⚠️ Monitoring – niet gebruiken voor selectie</h3>
    <p style='margin: 0; color: #856404;'>
        Deze pagina is alleen voor <b>signalering</b> van trends en afwijkingen.<br>
        Selectie van coaches gebeurt op basis van <b>1m eligibility uit de ETL</b> (zie hoofdpagina).
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# GLOBAL SIDEBAR
# ============================================================================

ctx = shared.render_global_sidebar()
periode_label = ctx["periode_label"]
excluded_coaches = ctx["excluded_coaches"]

# ============================================================================
# DATA LOADING
# ============================================================================

deals_df = shared.load_deals_flat()
try:
    coaches_df = shared.load_coach_data_raw()
except FileNotFoundError:
    coaches_df = None

if deals_df is None:
    st.error("""
    ❌ **deals_flat.csv niet gevonden!**

    Dit bestand wordt gegenereerd door de ETL. Volg deze stappen:

    1. Ga naar **🔄 Data Beheer**
    2. Klik op **🔄 Data Ophalen**
    3. Kom terug naar deze pagina

    Of run handmatig:
    ```bash
    python -m etl.calculate_metrics
    ```
    """)
    st.stop()

if coaches_df is None:
    st.error("❌ Coach eligibility data niet gevonden!")
    st.stop()

# Apply global exclusions
coaches_df = shared.apply_global_exclusions(coaches_df)

# ============================================================================
# LOCAL SIDEBAR CONTROLS
# ============================================================================

st.sidebar.markdown("### 📊 Week Monitor Filters")

num_weeks = st.sidebar.slider(
    "Aantal weken",
    min_value=1, max_value=52, value=12, step=1,
    help="Toon data voor de laatste X weken",
)

st.sidebar.markdown("---")

st.sidebar.markdown("### 👤 Coach Selectie")

all_coaches = sorted(coaches_df["Coachnaam"].unique())

selected_coach = st.sidebar.selectbox(
    "Selecteer coach voor detail",
    options=["(Alle coaches)"] + all_coaches,
    index=0,
    help="Kies een coach om detail charts te bekijken",
)

st.sidebar.markdown("---")

st.sidebar.markdown("### ⭐ Eligibility Filter")

eligibility_options = sorted(coaches_df["eligibility"].unique()) if "eligibility" in coaches_df.columns else []
selected_eligibilities = st.sidebar.multiselect(
    "Toon alleen deze eligibility",
    options=eligibility_options,
    default=eligibility_options,
    help="Filter coaches op eligibility status",
)

filtered_coaches = coaches_df[coaches_df["eligibility"].isin(selected_eligibilities)]["Coachnaam"].tolist() if "eligibility" in coaches_df.columns else all_coaches

st.sidebar.markdown("---")

st.sidebar.markdown("### ⚠️ Alert Thresholds")

nabeller_threshold = st.sidebar.slider(
    "Nabeller % drempel",
    min_value=5, max_value=50, value=20, step=5,
    help="Alert als nabeller_pct_week > deze waarde",
    key="wm_nabeller_threshold",
)

won_rate_drop = st.sidebar.slider(
    "Won rate daling drempel",
    min_value=5, max_value=30, value=15, step=5,
    help="Alert als won_rate_week < 4w gemiddelde - deze waarde",
    key="wm_won_rate_drop",
)

min_deals_week = st.sidebar.slider(
    "Minimum deals/week",
    min_value=1, max_value=15, value=5, step=1,
    help="Negeer weken met minder deals (ruis beperken)",
    key="wm_min_deals_week",
)

# ============================================================================
# FILTER BANNER
# ============================================================================

extra_filters = {}
if num_weeks != 12:
    extra_filters["Weken"] = str(num_weeks)
if nabeller_threshold != 20:
    extra_filters["Nabeller drempel"] = f"{nabeller_threshold}%"
if min_deals_week != 5:
    extra_filters["Min deals/week"] = str(min_deals_week)

shared.render_active_filters_banner(periode_label, excluded_coaches, extra_filters)

# ============================================================================
# WEEK AGGREGATION FUNCTIONS
# ============================================================================

def get_iso_week_start(dt):
    return dt - timedelta(days=dt.weekday())


def aggregate_by_week(df: pd.DataFrame, num_weeks: int = 12) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(weeks=num_weeks)

    filtered = df[df["created_dt"] >= cutoff].copy()
    if filtered.empty:
        return pd.DataFrame()

    filtered["week_start"] = filtered["created_dt"].apply(
        lambda dt: get_iso_week_start(dt.replace(tzinfo=None)).date()
    )

    agg_rows = []
    for (coach_id, coachnaam, week_start), group in filtered.groupby(
        ["coach_id", "Coachnaam", "week_start"]
    ):
        deals_week = len(group)
        won_week = (group["class"] == "WON").sum()
        lost_week = (group["class"] == "LOST").sum()
        open_week = (group["class"] == "OPEN").sum()
        nabeller_week = (group["pipeline"] == shared.PIPELINE_NABELLER).sum()

        won_rate_week = (won_week / deals_week * 100.0) if deals_week > 0 else 0.0
        nabeller_pct_week = (nabeller_week / deals_week * 100.0) if deals_week > 0 else 0.0

        agg_rows.append({
            "coach_id": coach_id,
            "Coachnaam": coachnaam,
            "week_start": week_start,
            "deals_week": deals_week,
            "won_week": won_week,
            "lost_week": lost_week,
            "open_week": open_week,
            "won_rate_week": round(won_rate_week, 1),
            "nabeller_week": nabeller_week,
            "nabeller_pct_week": round(nabeller_pct_week, 1),
        })

    result = pd.DataFrame(agg_rows)
    result["week_start"] = pd.to_datetime(result["week_start"])
    return result


def calculate_rolling_avg(weekly_df: pd.DataFrame, window: int = 4) -> pd.DataFrame:
    if weekly_df.empty:
        return weekly_df
    df = weekly_df.copy()
    df = df.sort_values(["coach_id", "week_start"])
    df["won_rate_rolling_4w"] = df.groupby("coach_id")["won_rate_week"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )
    return df


def detect_alerts(weekly_df, nabeller_threshold, won_rate_drop_threshold, min_deals_week):
    if weekly_df.empty:
        return pd.DataFrame()

    latest_week = weekly_df["week_start"].max()
    latest = weekly_df[weekly_df["week_start"] == latest_week].copy()
    latest = latest[latest["deals_week"] >= min_deals_week]

    if latest.empty:
        return pd.DataFrame()

    alerts = []
    for _, row in latest.iterrows():
        reasons = []
        if row["nabeller_pct_week"] > nabeller_threshold:
            reasons.append(f"Nabeller {row['nabeller_pct_week']:.1f}% > {nabeller_threshold}%")
        if "won_rate_rolling_4w" in row and pd.notna(row["won_rate_rolling_4w"]):
            if row["won_rate_week"] < row["won_rate_rolling_4w"] - won_rate_drop_threshold:
                reasons.append(
                    f"Won rate {row['won_rate_week']:.1f}% < "
                    f"4w avg ({row['won_rate_rolling_4w']:.1f}%) - {won_rate_drop_threshold}%"
                )
        if reasons:
            alerts.append({
                "Coachnaam": row["Coachnaam"],
                "coach_id": row["coach_id"],
                "deals_week": row["deals_week"],
                "won_rate_week": row["won_rate_week"],
                "nabeller_pct_week": row["nabeller_pct_week"],
                "won_rate_rolling_4w": row.get("won_rate_rolling_4w", None),
                "alert_reasons": "; ".join(reasons),
            })

    return pd.DataFrame(alerts)


# ============================================================================
# PROCESS DATA
# ============================================================================

# Filter deals to selected coaches (applies global exclusion via filtered_coaches list)
filtered_deals = deals_df[deals_df["Coachnaam"].isin(filtered_coaches)]

weekly_df = aggregate_by_week(filtered_deals, num_weeks=num_weeks)

if weekly_df.empty:
    st.warning("⚠️ Geen data gevonden voor de geselecteerde filters en periode.")
    st.stop()

weekly_df = calculate_rolling_avg(weekly_df, window=4)

alerts_df = detect_alerts(
    weekly_df,
    nabeller_threshold=nabeller_threshold,
    won_rate_drop_threshold=won_rate_drop,
    min_deals_week=min_deals_week,
)

# ============================================================================
# SECTION 1: ALERTS
# ============================================================================

st.markdown("---")
st.markdown("## 1️⃣ Alerts Deze Week")

if alerts_df.empty:
    st.success("✅ Geen alerts voor de meest recente week met de huidige thresholds.")
else:
    st.warning(f"⚠️ **{len(alerts_df)} coach(es) met alerts**")

    display_alerts = alerts_df[[
        "Coachnaam", "deals_week", "won_rate_week",
        "nabeller_pct_week", "won_rate_rolling_4w", "alert_reasons",
    ]].copy()

    display_alerts = display_alerts.rename(columns={
        "Coachnaam": "Coach",
        "deals_week": "Deals",
        "won_rate_week": "Won Rate %",
        "nabeller_pct_week": "Nabeller %",
        "won_rate_rolling_4w": "4w Gem %",
        "alert_reasons": "Alert Reden",
    })

    st.dataframe(
        display_alerts,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Coach": st.column_config.TextColumn(width="medium"),
            "Deals": st.column_config.NumberColumn(format="%d"),
            "Won Rate %": st.column_config.NumberColumn(format="%.1f%%"),
            "Nabeller %": st.column_config.NumberColumn(format="%.1f%%"),
            "4w Gem %": st.column_config.NumberColumn(format="%.1f%%"),
            "Alert Reden": st.column_config.TextColumn(width="large"),
        },
    )

# ============================================================================
# SECTION 2: COACH DETAIL CHARTS
# ============================================================================

st.markdown("---")
st.markdown("## 2️⃣ Coach Detail")

if selected_coach == "(Alle coaches)":
    st.info("👆 Selecteer een specifieke coach in de sidebar om detail charts te bekijken.")
else:
    coach_weekly = weekly_df[weekly_df["Coachnaam"] == selected_coach].copy()

    if coach_weekly.empty:
        st.warning(f"⚠️ Geen weekdata gevonden voor {selected_coach}")
    else:
        coach_weekly = coach_weekly.sort_values("week_start")

        st.markdown(f"### 📈 {selected_coach}")

        coach_elig = coaches_df[coaches_df["Coachnaam"] == selected_coach]["eligibility"].values if "eligibility" in coaches_df.columns else []
        if len(coach_elig) > 0:
            st.markdown(f"**Eligibility:** {coach_elig[0]}")

        col1, col2 = st.columns(2)

        with col1:
            fig_won_rate = go.Figure()
            fig_won_rate.add_trace(go.Scatter(
                x=coach_weekly["week_start"],
                y=coach_weekly["won_rate_week"],
                mode="lines+markers",
                name="Won Rate %",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=8),
                hovertemplate="Week: %{x|%d-%m-%Y}<br>Won Rate: %{y:.1f}%<extra></extra>",
            ))
            if "won_rate_rolling_4w" in coach_weekly.columns:
                fig_won_rate.add_trace(go.Scatter(
                    x=coach_weekly["week_start"],
                    y=coach_weekly["won_rate_rolling_4w"],
                    mode="lines",
                    name="4w Gemiddelde",
                    line=dict(color="#ff7f0e", width=2, dash="dash"),
                    hovertemplate="Week: %{x|%d-%m-%Y}<br>4w Gem: %{y:.1f}%<extra></extra>",
                ))
            fig_won_rate.update_layout(
                title="Won Rate % per Week",
                xaxis_title="Week", yaxis_title="Won Rate (%)",
                height=350, hovermode="x unified",
                plot_bgcolor="rgba(240,240,240,0.5)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_won_rate, use_container_width=True)

        with col2:
            fig_nabeller = go.Figure()
            fig_nabeller.add_trace(go.Scatter(
                x=coach_weekly["week_start"],
                y=coach_weekly["nabeller_pct_week"],
                mode="lines+markers",
                name="Nabeller %",
                line=dict(color="#d62728", width=2),
                marker=dict(size=8),
                hovertemplate="Week: %{x|%d-%m-%Y}<br>Nabeller: %{y:.1f}%<extra></extra>",
            ))
            fig_nabeller.add_hline(
                y=nabeller_threshold, line_dash="dash", line_color="orange",
                annotation_text=f"Drempel ({nabeller_threshold}%)", annotation_position="right",
            )
            fig_nabeller.update_layout(
                title="Nabeller % per Week",
                xaxis_title="Week", yaxis_title="Nabeller (%)",
                height=350, hovermode="x unified",
                plot_bgcolor="rgba(240,240,240,0.5)",
            )
            st.plotly_chart(fig_nabeller, use_container_width=True)

        fig_deals = go.Figure()
        fig_deals.add_trace(go.Bar(
            x=coach_weekly["week_start"],
            y=coach_weekly["deals_week"],
            name="Deals",
            marker_color="#2ca02c",
            hovertemplate="Week: %{x|%d-%m-%Y}<br>Deals: %{y}<extra></extra>",
        ))
        fig_deals.add_hline(
            y=min_deals_week, line_dash="dot", line_color="gray",
            annotation_text=f"Min. ({min_deals_week})", annotation_position="right",
        )
        fig_deals.update_layout(
            title="Deals per Week",
            xaxis_title="Week", yaxis_title="Aantal Deals",
            height=300, plot_bgcolor="rgba(240,240,240,0.5)",
        )
        st.plotly_chart(fig_deals, use_container_width=True)

        st.markdown("### 📋 Weekoverzicht")

        table_weekly = coach_weekly[[
            "week_start", "deals_week", "won_week", "lost_week", "open_week",
            "won_rate_week", "nabeller_week", "nabeller_pct_week",
        ]].copy()
        table_weekly = table_weekly.sort_values("week_start", ascending=False)
        table_weekly["week_start"] = table_weekly["week_start"].dt.strftime("%d-%m-%Y")
        table_weekly = table_weekly.rename(columns={
            "week_start": "Week Start",
            "deals_week": "Deals",
            "won_week": "Won",
            "lost_week": "Lost",
            "open_week": "Open",
            "won_rate_week": "Won Rate %",
            "nabeller_week": "Nabeller",
            "nabeller_pct_week": "Nabeller %",
        })

        st.dataframe(
            table_weekly,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Week Start": st.column_config.TextColumn(width="small"),
                "Deals": st.column_config.NumberColumn(format="%d"),
                "Won": st.column_config.NumberColumn(format="%d"),
                "Lost": st.column_config.NumberColumn(format="%d"),
                "Open": st.column_config.NumberColumn(format="%d"),
                "Won Rate %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Nabeller": st.column_config.NumberColumn(format="%d"),
                "Nabeller %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


# ============================================================================
# SECTION 3: ALL COACHES OVERVIEW
# ============================================================================

st.markdown("---")
st.markdown("## 3️⃣ Overzicht Alle Coaches (Laatste Week)")

latest_week = weekly_df["week_start"].max()
latest_all = weekly_df[weekly_df["week_start"] == latest_week].copy()

if latest_all.empty:
    st.warning("Geen data voor de laatste week.")
else:
    st.markdown(f"**Week van:** {latest_week.strftime('%d-%m-%Y')}")

    latest_all = latest_all.sort_values("deals_week", ascending=False)

    display_all = latest_all[[
        "Coachnaam", "deals_week", "won_week", "lost_week",
        "won_rate_week", "nabeller_week", "nabeller_pct_week",
    ]].copy()

    display_all = display_all.rename(columns={
        "Coachnaam": "Coach",
        "deals_week": "Deals",
        "won_week": "Won",
        "lost_week": "Lost",
        "won_rate_week": "Won Rate %",
        "nabeller_week": "Nabeller",
        "nabeller_pct_week": "Nabeller %",
    })

    st.dataframe(
        display_all,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "Coach": st.column_config.TextColumn(width="medium"),
            "Deals": st.column_config.NumberColumn(format="%d"),
            "Won": st.column_config.NumberColumn(format="%d"),
            "Lost": st.column_config.NumberColumn(format="%d"),
            "Won Rate %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "Nabeller": st.column_config.NumberColumn(format="%d"),
            "Nabeller %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

# ============================================================================
# FOOTER
# ============================================================================

shared.render_footer("📊", "Week Monitor - Coach Dashboard")
