# 🎯 Coach Performance Dashboard

A Streamlit-based interactive dashboard to analyze coach performance metrics across 1-month, 3-month, and 6-month periods.

---

## 📋 Features

✅ **Histogram** of smoothed 1-month win rate with P50 reference line  
✅ **Bar Chart** showing coach distribution by eligibility  
✅ **Scatter Plot** of deals vs smoothed win rate (colored by eligibility)  
✅ **Time Comparison** with switchable 1m/3m/6m histograms  
✅ **Trend Table** showing comparative metrics across all time periods  
✅ **Interactive Filters**:
- Filter by eligibility (multiselect)
- Filter by minimum deals in 1-month period (slider)

✅ **Data Quality** indicators and sanity check summaries  
✅ **No external API calls** – all data from local files  
✅ **Responsive design** with clean, readable visualizations  

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Python Version**: 3.8 or higher recommended

### Step 2: Organize Data Files

Create a `data/` folder in the same directory as `dashboard_app.py` and copy these files:

```
project-folder/
├── dashboard_app.py
├── requirements.txt
├── README.md
└── data/
    ├── coach_eligibility_20260121_195256.xlsx
    ├── mapping.xlsx
    ├── deals_flat.csv
    └── owners.json
```

**Important**: The app expects these exact file names in a `data/` subdirectory.

### Step 3: Run the App

```bash
streamlit run dashboard_app.py
```

The app will automatically open in your default browser at:
```
http://localhost:8501
```

If it doesn't auto-open, copy the URL from the terminal output.

### Step 4: Use the Dashboard

1. **Left Sidebar** – Set your filters:
   - Select which eligibility categories to include (multiselect)
   - Set minimum number of deals threshold (slider)

2. **Main View** – Explore visualizations:
   - Overview metrics at the top
   - Histogram with P50 reference line
   - Eligibility distribution bar chart
   - Deals vs Win Rate scatter plot (colored by eligibility)
   - Time period comparison (toggle between 1m, 3m, 6m)
   - Trend table with detailed coach data

3. **Interact** – All charts support:
   - Hover for detailed information
   - Click legend items to show/hide categories
   - Zoom and pan (hover over chart for tools)
   - Download as PNG (camera icon)

---

## 📊 Dashboard Sections Explained

### 1. Overview Metrics (Top Cards)
Quick-look metrics for the filtered dataset:
- **Avg Smoothed 1m**: Average smoothed win rate for the 1-month period
- **Avg Deals 1m**: Average number of deals per coach
- **Avg Win Rate 1m**: Average win rate percentage
- **% Above P50**: Percentage of coaches above the P50 benchmark (51.1%)

### 2. Histogram: Smoothed 1m Distribution
Shows the distribution of smoothed win rates with:
- **X-axis**: Smoothed win rate (%)
- **Y-axis**: Number of coaches
- **Red dashed line**: P50 benchmark (51.1%)

This helps identify if your filtered group outperforms or underperforms the benchmark.

### 3. Eligibility Bar Chart
Displays coach counts by eligibility category.
- Useful for understanding the composition of your filtered group
- Taller bars = more coaches in that eligibility tier

### 4. Scatter: Deals vs Win Rate
Core performance visualization:
- **X-axis**: Number of deals (1-month)
- **Y-axis**: Smoothed win rate (%)
- **Colors**: Eligibility category
- **Red line**: P50 benchmark

Patterns to look for:
- Coaches in upper right = many deals + high win rate (ideal)
- Coaches in upper left = few deals + high win rate (potential)
- Coaches below P50 line = below-benchmark performance

### 5. Time Comparison (1m vs 3m vs 6m)
Toggle buttons to compare win rate distributions across time periods:
- 1-Month: Most recent performance
- 3-Month: Medium-term trend
- 6-Month: Longer-term stability

Helps identify coaches with improving, declining, or stable performance.

### 6. Trends Table
Detailed view of all metrics for filtered coaches:
- Columns: Coach ID, Name, Deals, Win Rate (1m, 3m, 6m), Eligibility
- Sorted by 1m smoothed win rate (descending)
- Useful for identifying outliers or specific coach performance

---

## 🎛️ Filters Explained

### Eligibility Filter (Multiselect)
Select one or more eligibility categories. The dashboard shows only coaches in those categories.
- Default: All categories
- Example: Select only "✅ Laag 2" to focus on that segment

### Minimum Deals Slider
Show only coaches with at least X deals in the 1-month period.
- Range: 0 to maximum deals in your data
- Default: 0 (show all)
- Example: Set to 20 to focus on active coaches

**Combined Effect**: Dashboard shows coaches that match BOTH conditions:
- `(eligibility in selected) AND (deals_1m >= minimum)`

---

## 📂 File Structure

```
project-folder/
├── dashboard_app.py                        # Main Streamlit app (this is what you run)
├── requirements.txt                        # Python dependencies
├── README.md                               # This file
├── IMPLEMENTATION_PLAN.md                  # Technical implementation details
└── data/
    ├── coach_eligibility_20260121_195256.xlsx    # Primary data source
    │   ├── Coaches sheet (105 coaches × 31 metrics)
    │   ├── DealClassSummary sheet (sanity checks)
    │   └── Owners sheet
    │
    ├── mapping.xlsx                        # Pipeline & dealstage → class mapping
    │
    ├── deals_flat.csv                      # Complete deals dataset
    │
    └── owners.json                         # Coach ID → Name backup mapping
```

---

## 🔧 Technical Details

### Data Sources
- **Primary**: `coach_eligibility_*.xlsx` (Coaches sheet with 105 coaches)
- **Sanity Check**: DealClassSummary sheet in same file
- **Mapping**: `mapping.xlsx` for pipeline + stage → class conversion
- **Metadata**: `owners.json` for coach ID mapping

### Key Metrics Available
- **1-Month**: deals_1m, won_1m, lost_1m, open_1m, rate_1m, smoothed_1m
- **3-Month**: deals_3m, won_3m, lost_3m, open_3m, rate_3m, smoothed_3m
- **6-Month**: deals_6m, won_6m, lost_6m, open_6m, rate_6m, smoothed_6m
- **Benchmark**: p50_smoothed_1m = 51.1%
- **Category**: eligibility (categorical field)

### Performance
- Data is cached using `@st.cache_data` for instant filter updates
- Load time: ~1-2 seconds on first run
- Filter response: <500ms

### Libraries Used
- **streamlit**: Web framework
- **pandas**: Data manipulation
- **numpy**: Numerical computing
- **plotly**: Interactive visualizations
- **openpyxl**: Excel file reading

---

## ❓ Troubleshooting

### "Error loading data"
**Problem**: Files not found  
**Solution**: 
1. Check that `data/` folder exists in the same directory as `dashboard_app.py`
2. Verify file names match exactly (case-sensitive on Linux/Mac)
3. Ensure all 4 files are present

### "ModuleNotFoundError: No module named 'streamlit'"
**Problem**: Dependencies not installed  
**Solution**: 
```bash
pip install -r requirements.txt
```

### App runs but shows no data
**Problem**: Filters set too restrictive  
**Solution**: 
1. Reset eligibility filter to "All"
2. Lower the minimum deals slider to 0
3. Refresh the page (press R in Streamlit)

### Slow performance
**Problem**: Too much data or system issue  
**Solution**:
1. Clear Streamlit cache: `streamlit cache clear`
2. Restart app: `Ctrl+C` then `streamlit run dashboard_app.py`
3. Close other applications

---

## 📊 Example Insights to Explore

1. **Who are top performers?**
   - Use scatter plot: look for points in upper right (many deals + high win rate)

2. **Is my team above benchmark?**
   - Check Overview Metrics: "% Above P50" should be > 50%
   - Examine histogram: does bulk of distribution sit right of red line?

3. **Who's improving/declining?**
   - Use Trends Table: compare smoothed_1m vs smoothed_6m
   - Use time comparison: toggle between periods to see patterns

4. **Deal activity patterns?**
   - Look at scatter plot X-axis: who's closing most deals?
   - Consider combining with win rate: deals are good, but quality matters too

5. **Eligibility breakdown?**
   - Bar chart: which categories have most coaches?
   - Scatter plot colors: do certain eligibilities outperform others?

---

## 🛠️ Development Notes

### Customizing the Dashboard

**Change colors**:
Edit lines in `dashboard_app.py` with `color_continuous_scale`:
```python
color_continuous_scale='Blues'  # Try 'Reds', 'Greens', 'Viridis', etc.
```

**Add new filters**:
```python
new_filter = st.sidebar.selectbox("New Filter", options)
filtered_df = filtered_df[filtered_df['column'] == new_filter]
```

**Add new visualizations**:
```python
fig = px.scatter(filtered_df, x='col1', y='col2', ...)
st.plotly_chart(fig, use_container_width=True)
```

### Caching Strategy
Data is loaded and cached on first run. Changes to source files require:
```bash
streamlit cache clear
```

---

## 📞 Support

For issues or questions:
1. Check **Troubleshooting** section above
2. Verify file paths and names
3. Review the `IMPLEMENTATION_PLAN.md` for technical details
4. Check Streamlit docs: https://docs.streamlit.io

---

## 📝 Changelog

**v1.0** (2026-01-21)
- Initial release
- 6 main visualizations
- 2 interactive filters
- Data quality indicators
- Responsive design

---

**Last Updated**: January 21, 2026  
**Streamlit Version**: 1.28+  
**Python Version**: 3.8+
