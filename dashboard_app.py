import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Coach Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Coach Performance Dashboard")
st.markdown("Analyze coach metrics across 1-month, 3-month, and 6-month periods")

# ============================================================================
# DATA LOADING (CACHED)
# ============================================================================

@st.cache_data
def load_coach_data():
    """Load coaches data from Excel."""
    file_path = Path("data/coach_eligibility_20260121_195256.xlsx")
    df = pd.read_excel(file_path, sheet_name="Coaches")
    return df

@st.cache_data
def load_deal_class_summary():
    """Load deal class summary for sanity checks."""
    file_path = Path("data/coach_eligibility_20260121_195256.xlsx")
    df = pd.read_excel(file_path, sheet_name="DealClassSummary")
    return df

@st.cache_data
def load_mapping():
    """Load stage mapping."""
    file_path = Path("data/mapping.xlsx")
    df = pd.read_excel(file_path, sheet_name="stage_mapping")
    return df

@st.cache_data
def load_owners():
    """Load owner mapping."""
    file_path = Path("data/owners.json")
    with open(file_path, 'r') as f:
        owners = json.load(f)
    return owners

# Load all data
try:
    coaches_df = load_coach_data()
    summary_df = load_deal_class_summary()
    mapping_df = load_mapping()
    owners_dict = load_owners()
    data_loaded = True
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.info("Make sure all data files are in the `data/` subfolder")
    data_loaded = False
    st.stop()

# ============================================================================
# SIDEBAR: FILTERS
# ============================================================================

st.sidebar.header("🎯 Filters")

# Get unique eligibility values
eligibility_options = sorted(coaches_df['eligibility'].unique())
selected_eligibility = st.sidebar.multiselect(
    "Coach Eligibility",
    options=eligibility_options,
    default=eligibility_options,
    help="Filter by eligibility category"
)

# Deals slider
min_deals_range = int(coaches_df['deals_1m'].min())
max_deals_range = int(coaches_df['deals_1m'].max())
min_deals = st.sidebar.slider(
    "Minimum Deals (1-month)",
    min_value=min_deals_range,
    max_value=max_deals_range,
    value=min_deals_range,
    step=1,
    help="Show only coaches with at least this many deals in the last month"
)

# Apply filters
filtered_df = coaches_df[
    (coaches_df['eligibility'].isin(selected_eligibility)) &
    (coaches_df['deals_1m'] >= min_deals)
].copy()

# Display filter info
st.sidebar.markdown("---")
st.sidebar.markdown(f"### 📈 Filtered Results")
st.sidebar.metric("Coaches shown", len(filtered_df))
st.sidebar.metric("Total coaches", len(coaches_df))

# ============================================================================
# DATA QUALITY / SANITY CHECKS
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Data Quality")

col_qa1, col_qa2 = st.sidebar.columns(2)
with col_qa1:
    st.metric("P50 Smoothed 1m", f"{coaches_df['p50_smoothed_1m'].iloc[0]:.1f}%")
with col_qa2:
    st.metric("Data rows", len(coaches_df))

with st.sidebar.expander("📊 Deal Class Summary"):
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ============================================================================
# MAIN METRICS (TOP CARDS)
# ============================================================================

st.markdown("### 📊 Overview Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_smoothed = filtered_df['smoothed_1m'].mean()
    st.metric("Avg Smoothed 1m", f"{avg_smoothed:.1f}%")

with col2:
    avg_deals = filtered_df['deals_1m'].mean()
    st.metric("Avg Deals 1m", f"{avg_deals:.1f}")

with col3:
    avg_wr = filtered_df['rate_1m'].mean()
    st.metric("Avg Win Rate 1m", f"{avg_wr:.1f}%")

with col4:
    p50 = coaches_df['p50_smoothed_1m'].iloc[0]
    pct_above = (filtered_df['smoothed_1m'] >= p50).sum() / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
    st.metric("% Above P50", f"{pct_above:.0f}%")

# ============================================================================
# SECTION 1: HISTOGRAM WITH PERCENTILE LINE
# ============================================================================

st.markdown("---")
st.markdown("### 1️⃣ Distribution of 1-Month Smoothed Win Rate")

p50_value = coaches_df['p50_smoothed_1m'].iloc[0]

fig_hist = go.Figure()

# Add histogram
fig_hist.add_trace(go.Histogram(
    x=filtered_df['smoothed_1m'],
    nbinsx=25,
    name='Coaches',
    marker_color='rgba(31, 119, 180, 0.7)',
    hovertemplate='<b>Win Rate Range</b>: %{x}<br><b>Count</b>: %{y}<extra></extra>'
))

# Add percentile line
fig_hist.add_vline(
    x=p50_value,
    line_dash="dash",
    line_color="red",
    annotation_text=f"P50 = {p50_value:.1f}%",
    annotation_position="top right"
)

fig_hist.update_layout(
    title="Distribution of Smoothed Win Rate (1-month)",
    xaxis_title="Smoothed Win Rate (%)",
    yaxis_title="Number of Coaches",
    hovermode='x unified',
    height=400,
    showlegend=False,
    plot_bgcolor='rgba(240,240,240,0.5)'
)

st.plotly_chart(fig_hist, use_container_width=True)

# ============================================================================
# SECTION 2: BAR CHART - ELIGIBILITY DISTRIBUTION
# ============================================================================

st.markdown("---")
st.markdown("### 2️⃣ Coach Distribution by Eligibility")

eligibility_counts = filtered_df['eligibility'].value_counts().reset_index()
eligibility_counts.columns = ['eligibility', 'count']
eligibility_counts = eligibility_counts.sort_values('count', ascending=False)

fig_bar = px.bar(
    eligibility_counts,
    x='eligibility',
    y='count',
    labels={'eligibility': 'Eligibility', 'count': 'Number of Coaches'},
    text='count',
    color='count',
    color_continuous_scale='Blues',
    hover_name='eligibility'
)

fig_bar.update_traces(
    textposition='outside',
    texttemplate='%{text}',
    hovertemplate='<b>%{x}</b><br>Coaches: %{y}<extra></extra>'
)

fig_bar.update_layout(
    title="Coach Distribution by Eligibility",
    xaxis_title="Eligibility Category",
    yaxis_title="Number of Coaches",
    height=400,
    showlegend=False,
    hovermode='x'
)

st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# SECTION 3: SCATTER - DEALS VS SMOOTHED WIN RATE
# ============================================================================

st.markdown("---")
st.markdown("### 3️⃣ Deals vs Smoothed Win Rate (Colored by Eligibility)")

fig_scatter = px.scatter(
    filtered_df,
    x='deals_1m',
    y='smoothed_1m',
    color='eligibility',
    hover_name='Coachnaam',
    hover_data={
        'coach_id': True,
        'deals_1m': ':.0f',
        'smoothed_1m': ':.1f',
        'rate_1m': ':.1f',
        'eligibility': True
    },
    labels={
        'deals_1m': 'Number of Deals (1-month)',
        'smoothed_1m': 'Smoothed Win Rate (%)',
        'eligibility': 'Eligibility'
    },
    title="Deals vs Smoothed Win Rate (1-month)",
    height=500
)

# Add p50 reference line
fig_scatter.add_hline(
    y=p50_value,
    line_dash="dash",
    line_color="red",
    annotation_text=f"P50 = {p50_value:.1f}%",
    annotation_position="right"
)

fig_scatter.update_layout(
    hovermode='closest',
    plot_bgcolor='rgba(240,240,240,0.5)'
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# SECTION 4: TIME COMPARISON (1m vs 3m vs 6m)
# ============================================================================

st.markdown("---")
st.markdown("### 4️⃣ Comparison: 1-Month vs 3-Month vs 6-Month")

# Create small multiple histograms
fig_multi = go.Figure()

periods = [
    ('smoothed_1m', '1-Month'),
    ('smoothed_3m', '3-Month'),
    ('smoothed_6m', '6-Month')
]

for i, (col, label) in enumerate(periods):
    fig_multi.add_trace(go.Histogram(
        x=filtered_df[col],
        name=label,
        nbinsx=20,
        visible=(i == 0),  # Show only first by default
        hovertemplate=f'<b>{label}</b><br>Win Rate: %{{x:.1f}}%<br>Count: %{{y}}<extra></extra>'
    ))

# Create buttons to switch between periods
buttons = []
for i, (col, label) in enumerate(periods):
    visible = [False] * len(periods)
    visible[i] = True
    buttons.append(
        dict(
            label=label,
            method='update',
            args=[
                {'visible': visible},
                {'title': f'Distribution of Smoothed Win Rate ({label})'}
            ]
        )
    )

fig_multi.update_layout(
    updatemenus=[
        dict(
            active=0,
            buttons=buttons,
            direction="left",
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )
    ],
    title="Distribution of Smoothed Win Rate (1-Month)",
    xaxis_title="Smoothed Win Rate (%)",
    yaxis_title="Number of Coaches",
    height=400,
    hovermode='x unified',
    plot_bgcolor='rgba(240,240,240,0.5)',
    showlegend=False
)

st.plotly_chart(fig_multi, use_container_width=True)

# ============================================================================
# SECTION 5: COMPARATIVE TABLE (1m vs 3m vs 6m)
# ============================================================================

st.markdown("---")
st.markdown("### 📋 Trends: 1m vs 3m vs 6m")

trend_cols = [
    'coach_id',
    'Coachnaam',
    'deals_1m', 'smoothed_1m',
    'deals_3m', 'smoothed_3m',
    'deals_6m', 'smoothed_6m',
    'eligibility'
]

trend_df = filtered_df[trend_cols].copy()
trend_df = trend_df.sort_values('smoothed_1m', ascending=False)

# Format for display
display_df = trend_df.copy()
display_df['smoothed_1m'] = display_df['smoothed_1m'].apply(lambda x: f"{x:.1f}%")
display_df['smoothed_3m'] = display_df['smoothed_3m'].apply(lambda x: f"{x:.1f}%")
display_df['smoothed_6m'] = display_df['smoothed_6m'].apply(lambda x: f"{x:.1f}%")

display_df = display_df.rename(columns={
    'coach_id': 'Coach ID',
    'Coachnaam': 'Coach Name',
    'deals_1m': 'Deals (1m)',
    'smoothed_1m': 'Win Rate (1m)',
    'deals_3m': 'Deals (3m)',
    'smoothed_3m': 'Win Rate (3m)',
    'deals_6m': 'Deals (6m)',
    'smoothed_6m': 'Win Rate (6m)',
    'eligibility': 'Eligibility'
})

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Coach ID": st.column_config.NumberColumn(format="%.0f"),
        "Coach Name": st.column_config.TextColumn(width="medium"),
        "Deals (1m)": st.column_config.NumberColumn(format="%.0f"),
        "Deals (3m)": st.column_config.NumberColumn(format="%.0f"),
        "Deals (6m)": st.column_config.NumberColumn(format="%.0f"),
    }
)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    <p>📊 Coach Performance Dashboard | Data as of 2026-01-21</p>
    <p>No external API calls | All data from local files</p>
</div>
""", unsafe_allow_html=True)
