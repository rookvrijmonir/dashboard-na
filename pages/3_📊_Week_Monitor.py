import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Week Monitor - Nationale Apotheek",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Week Monitor")

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
# DATA LOADING
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RUNS_FILE = DATA_DIR / "runs.json"

PIPELINE_NABELLER = "38341389"


def get_selected_run_id():
    """Get the currently selected run ID from runs.json."""
    if RUNS_FILE.is_file():
        try:
            with open(RUNS_FILE, "r") as f:
                runs_data = json.load(f)
            return runs_data.get("selected")
        except:
            pass
    return None


def get_selected_run_dir():
    """Get the directory of the selected run."""
    run_id = get_selected_run_id()
    if run_id:
        run_dir = DATA_DIR / run_id
        if run_dir.is_dir():
            return run_dir
    return None


@st.cache_data
def load_deals_flat():
    """Load deals_flat.csv from the selected run."""
    run_dir = get_selected_run_dir()
    if run_dir is None:
        return None

    deals_path = run_dir / "deals_flat.csv"
    if not deals_path.is_file():
        return None

    df = pd.read_csv(deals_path)

    # Parse created_dt to datetime (ISO8601 format for mixed microseconds)
    df["created_dt"] = pd.to_datetime(df["created_dt"], format="ISO8601", utc=True, errors="coerce")

    # Filter out invalid dates
    df = df.dropna(subset=["created_dt"])

    return df


@st.cache_data
def load_coach_data():
    """Load coach eligibility data for filters."""
    run_dir = get_selected_run_dir()
    if run_dir is None:
        return None

    eligibility_path = run_dir / "coach_eligibility.xlsx"
    if not eligibility_path.is_file():
        return None

    df = pd.read_excel(eligibility_path, sheet_name="Coaches")

    # Filter: same exclusions as main dashboard
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


# Load data
deals_df = load_deals_flat()
coaches_df = load_coach_data()

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


# ============================================================================
# WEEK AGGREGATION FUNCTIONS
# ============================================================================

def get_iso_week_start(dt):
    """Get the Monday of the ISO week for a given datetime."""
    return dt - timedelta(days=dt.weekday())


def aggregate_by_week(df: pd.DataFrame, num_weeks: int = 12) -> pd.DataFrame:
    """
    Aggregate deals by coach and ISO week.

    Returns DataFrame with columns:
    - coach_id, Coachnaam
    - week_start (Monday of the week)
    - deals_week, won_week, lost_week, open_week
    - won_rate_week
    - nabeller_week, nabeller_pct_week
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(weeks=num_weeks)

    # Filter to time range
    filtered = df[df["created_dt"] >= cutoff].copy()

    if filtered.empty:
        return pd.DataFrame()

    # Add week_start column (Monday of ISO week)
    filtered["week_start"] = filtered["created_dt"].apply(
        lambda dt: get_iso_week_start(dt.replace(tzinfo=None)).date()
    )

    # Aggregate by coach and week
    agg_rows = []

    for (coach_id, coachnaam, week_start), group in filtered.groupby(
        ["coach_id", "Coachnaam", "week_start"]
    ):
        deals_week = len(group)
        won_week = (group["class"] == "WON").sum()
        lost_week = (group["class"] == "LOST").sum()
        open_week = (group["class"] == "OPEN").sum()
        nabeller_week = (group["pipeline"] == PIPELINE_NABELLER).sum()

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
    """Add rolling 4-week average of won_rate_week per coach."""
    if weekly_df.empty:
        return weekly_df

    df = weekly_df.copy()
    df = df.sort_values(["coach_id", "week_start"])

    # Calculate rolling average per coach
    df["won_rate_rolling_4w"] = df.groupby("coach_id")["won_rate_week"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )

    return df


def detect_alerts(
    weekly_df: pd.DataFrame,
    nabeller_threshold: float = 20.0,
    won_rate_drop_threshold: float = 15.0,
    min_deals_week: int = 5
) -> pd.DataFrame:
    """
    Detect alerts for the most recent week.

    Alert conditions:
    - nabeller_pct_week > nabeller_threshold
    - won_rate_week < rolling_4w_avg - won_rate_drop_threshold

    Only for coaches with deals_week >= min_deals_week.
    """
    if weekly_df.empty:
        return pd.DataFrame()

    # Get the most recent week
    latest_week = weekly_df["week_start"].max()
    latest = weekly_df[weekly_df["week_start"] == latest_week].copy()

    # Filter on minimum deals
    latest = latest[latest["deals_week"] >= min_deals_week]

    if latest.empty:
        return pd.DataFrame()

    # Detect alerts
    alerts = []

    for _, row in latest.iterrows():
        reasons = []

        # Check nabeller threshold
        if row["nabeller_pct_week"] > nabeller_threshold:
            reasons.append(f"Nabeller {row['nabeller_pct_week']:.1f}% > {nabeller_threshold}%")

        # Check won rate drop
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
                "alert_reasons": "; ".join(reasons)
            })

    return pd.DataFrame(alerts)


# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

st.sidebar.header("🎯 Filters")

# ===================
# DATE RANGE
# ===================
st.sidebar.markdown("### 📅 Periode")

num_weeks = st.sidebar.slider(
    "Aantal weken",
    min_value=1,
    max_value=52,
    value=12,
    step=1,
    help="Toon data voor de laatste X weken"
)

st.sidebar.markdown("---")

# ===================
# COACH FILTER
# ===================
st.sidebar.markdown("### 👤 Coach Selectie")

all_coaches = sorted(coaches_df["Coachnaam"].unique())

selected_coach = st.sidebar.selectbox(
    "Selecteer coach voor detail",
    options=["(Alle coaches)"] + all_coaches,
    index=0,
    help="Kies een coach om detail charts te bekijken"
)

st.sidebar.markdown("---")

# ===================
# ELIGIBILITY FILTER
# ===================
st.sidebar.markdown("### ⭐ Eligibility Filter")

eligibility_options = sorted(coaches_df["eligibility"].unique())
selected_eligibilities = st.sidebar.multiselect(
    "Toon alleen deze eligibility",
    options=eligibility_options,
    default=eligibility_options,
    help="Filter coaches op eligibility status"
)

# Apply eligibility filter to coaches list
filtered_coaches = coaches_df[coaches_df["eligibility"].isin(selected_eligibilities)]["Coachnaam"].tolist()

st.sidebar.markdown("---")

# ===================
# ALERT THRESHOLDS
# ===================
st.sidebar.markdown("### ⚠️ Alert Thresholds")

nabeller_threshold = st.sidebar.slider(
    "Nabeller % drempel",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
    help="Alert als nabeller_pct_week > deze waarde"
)

won_rate_drop = st.sidebar.slider(
    "Won rate daling drempel",
    min_value=5,
    max_value=30,
    value=15,
    step=5,
    help="Alert als won_rate_week < 4w gemiddelde - deze waarde"
)

min_deals_week = st.sidebar.slider(
    "Minimum deals/week",
    min_value=1,
    max_value=15,
    value=5,
    step=1,
    help="Negeer weken met minder deals (ruis beperken)"
)

# ============================================================================
# PROCESS DATA
# ============================================================================

# Filter deals to selected coaches
filtered_deals = deals_df[deals_df["Coachnaam"].isin(filtered_coaches)]

# Aggregate by week
weekly_df = aggregate_by_week(filtered_deals, num_weeks=num_weeks)

if weekly_df.empty:
    st.warning("⚠️ Geen data gevonden voor de geselecteerde filters en periode.")
    st.stop()

# Add rolling average
weekly_df = calculate_rolling_avg(weekly_df, window=4)

# Detect alerts
alerts_df = detect_alerts(
    weekly_df,
    nabeller_threshold=nabeller_threshold,
    won_rate_drop_threshold=won_rate_drop,
    min_deals_week=min_deals_week
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

    # Display alerts table
    display_alerts = alerts_df[[
        "Coachnaam", "deals_week", "won_rate_week",
        "nabeller_pct_week", "won_rate_rolling_4w", "alert_reasons"
    ]].copy()

    display_alerts = display_alerts.rename(columns={
        "Coachnaam": "Coach",
        "deals_week": "Deals",
        "won_rate_week": "Won Rate %",
        "nabeller_pct_week": "Nabeller %",
        "won_rate_rolling_4w": "4w Gem %",
        "alert_reasons": "Alert Reden"
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
        }
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

        # Get eligibility for this coach
        coach_elig = coaches_df[coaches_df["Coachnaam"] == selected_coach]["eligibility"].values
        if len(coach_elig) > 0:
            st.markdown(f"**Eligibility:** {coach_elig[0]}")

        # Create charts side by side
        col1, col2 = st.columns(2)

        with col1:
            # Line chart: Won Rate over time
            fig_won_rate = go.Figure()

            fig_won_rate.add_trace(go.Scatter(
                x=coach_weekly["week_start"],
                y=coach_weekly["won_rate_week"],
                mode="lines+markers",
                name="Won Rate %",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=8),
                hovertemplate="Week: %{x|%d-%m-%Y}<br>Won Rate: %{y:.1f}%<extra></extra>"
            ))

            # Add rolling average line
            if "won_rate_rolling_4w" in coach_weekly.columns:
                fig_won_rate.add_trace(go.Scatter(
                    x=coach_weekly["week_start"],
                    y=coach_weekly["won_rate_rolling_4w"],
                    mode="lines",
                    name="4w Gemiddelde",
                    line=dict(color="#ff7f0e", width=2, dash="dash"),
                    hovertemplate="Week: %{x|%d-%m-%Y}<br>4w Gem: %{y:.1f}%<extra></extra>"
                ))

            fig_won_rate.update_layout(
                title="Won Rate % per Week",
                xaxis_title="Week",
                yaxis_title="Won Rate (%)",
                height=350,
                hovermode="x unified",
                plot_bgcolor="rgba(240,240,240,0.5)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig_won_rate, use_container_width=True)

        with col2:
            # Line chart: Nabeller % over time
            fig_nabeller = go.Figure()

            fig_nabeller.add_trace(go.Scatter(
                x=coach_weekly["week_start"],
                y=coach_weekly["nabeller_pct_week"],
                mode="lines+markers",
                name="Nabeller %",
                line=dict(color="#d62728", width=2),
                marker=dict(size=8),
                hovertemplate="Week: %{x|%d-%m-%Y}<br>Nabeller: %{y:.1f}%<extra></extra>"
            ))

            # Add threshold line
            fig_nabeller.add_hline(
                y=nabeller_threshold,
                line_dash="dash",
                line_color="orange",
                annotation_text=f"Drempel ({nabeller_threshold}%)",
                annotation_position="right"
            )

            fig_nabeller.update_layout(
                title="Nabeller % per Week",
                xaxis_title="Week",
                yaxis_title="Nabeller (%)",
                height=350,
                hovermode="x unified",
                plot_bgcolor="rgba(240,240,240,0.5)"
            )

            st.plotly_chart(fig_nabeller, use_container_width=True)

        # Bar chart: Deals per week
        fig_deals = go.Figure()

        fig_deals.add_trace(go.Bar(
            x=coach_weekly["week_start"],
            y=coach_weekly["deals_week"],
            name="Deals",
            marker_color="#2ca02c",
            hovertemplate="Week: %{x|%d-%m-%Y}<br>Deals: %{y}<extra></extra>"
        ))

        # Add minimum threshold line
        fig_deals.add_hline(
            y=min_deals_week,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"Min. ({min_deals_week})",
            annotation_position="right"
        )

        fig_deals.update_layout(
            title="Deals per Week",
            xaxis_title="Week",
            yaxis_title="Aantal Deals",
            height=300,
            plot_bgcolor="rgba(240,240,240,0.5)"
        )

        st.plotly_chart(fig_deals, use_container_width=True)

        # Weekly data table
        st.markdown("### 📋 Weekoverzicht")

        table_weekly = coach_weekly[[
            "week_start", "deals_week", "won_week", "lost_week", "open_week",
            "won_rate_week", "nabeller_week", "nabeller_pct_week"
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
            "nabeller_pct_week": "Nabeller %"
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
            }
        )


# ============================================================================
# SECTION 3: ALL COACHES OVERVIEW
# ============================================================================

st.markdown("---")
st.markdown("## 3️⃣ Overzicht Alle Coaches (Laatste Week)")

# Get latest week data for all coaches
latest_week = weekly_df["week_start"].max()
latest_all = weekly_df[weekly_df["week_start"] == latest_week].copy()

if latest_all.empty:
    st.warning("Geen data voor de laatste week.")
else:
    st.markdown(f"**Week van:** {latest_week.strftime('%d-%m-%Y')}")

    # Sort by deals_week descending
    latest_all = latest_all.sort_values("deals_week", ascending=False)

    display_all = latest_all[[
        "Coachnaam", "deals_week", "won_week", "lost_week",
        "won_rate_week", "nabeller_week", "nabeller_pct_week"
    ]].copy()

    display_all = display_all.rename(columns={
        "Coachnaam": "Coach",
        "deals_week": "Deals",
        "won_week": "Won",
        "lost_week": "Lost",
        "won_rate_week": "Won Rate %",
        "nabeller_week": "Nabeller",
        "nabeller_pct_week": "Nabeller %"
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
        }
    )


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")

run_id = get_selected_run_id()
if run_id and len(run_id) == 15:
    data_date = f"{run_id[6:8]}-{run_id[4:6]}-{run_id[:4]}"
    data_time = f"{run_id[9:11]}:{run_id[11:13]}"
    run_info = f"Run: {data_date} {data_time}"
else:
    run_info = "Run: onbekend"

st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>📊 <b>Week Monitor - Coach Dashboard</b></p>
    <p>{run_info} | 🔄 <a href="/Data_Beheer" target="_self">Data Beheer</a></p>
    <p>💊 Nationale Apotheek</p>
</div>
""", unsafe_allow_html=True)
