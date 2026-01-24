# Coach Performance Dashboard

Streamlit dashboard voor coach prestatie analyse met geïntegreerde HubSpot ETL.

## Features

- **Dashboard** met interactieve grafieken (scatter, histogram, bar charts)
- **Periode selectie** - 1, 3 of 6 maanden analyse
- **Data Beheer** - Refresh data direct vanuit het dashboard
- **Run historie** - Bewaar en vergelijk meerdere data snapshots
- **Dynamische filters** - Coaches uitsluiten, top X%, minimum deals
- **Dynamische status** - Configureerbare Goed/Matig thresholds
- **NA_Pool Export** - Push coach selectie naar Google Sheets
- **Week Monitor** - Wekelijkse trends en alerts
- **Coach Beschikbaarheid** - Google Sheets integratie voor beschikbaarheid

## Quick Start

### 1. Clone en setup

```bash
git clone git@github.com:rookvrijmonir/dashboard-na.git
cd dashboard-na

python -m venv venv
source venv/bin/activate  # Linux/Mac
# of: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. HubSpot configuratie

```bash
cp .env.example .env
# Edit .env en vul je HUBSPOT_PAT in
```

### 3. Data ophalen

```bash
# Eerste keer: alles ophalen uit HubSpot
python refresh_data.py --refresh

# Of via het dashboard (Data Beheer pagina)
```

### 4. Dashboard starten

```bash
streamlit run dashboard_app.py
```

Open http://localhost:8501

## Folder Structuur

```
coach-dashboard/
├── dashboard_app.py          # Hoofddashboard + NA_Pool Export
├── gsheets_writer.py         # Google Sheets writer module
├── refresh_data.py           # CLI data refresh script
├── .env                      # Credentials (niet in git)
├── .env.example              # Template voor .env
│
├── secrets/
│   └── service_account.json  # Google SA credentials (niet in git)
│
├── pages/
│   ├── 1_📖_Uitleg.py              # Handleiding
│   ├── 2_🔄_Data_Beheer.py         # Data management UI
│   ├── 3_📊_Week_Monitor.py        # Wekelijkse trends/alerts
│   └── 4_👥_Coach_Beschikbaarheid.py  # Google Sheets beschikbaarheid
│
├── etl/
│   ├── fetch_hubspot.py      # HubSpot API data fetcher
│   ├── calculate_metrics.py  # Metrics berekening
│   ├── cache/                # API response cache (niet in git)
│   └── logs/                 # ETL logs (niet in git)
│
└── data/
    ├── runs.json             # Run configuratie
    ├── mapping.xlsx          # Stage mapping (gedeeld)
    └── YYYYMMDD_HHMMSS/      # Run folders
        ├── coach_eligibility.xlsx
        ├── deals_flat.csv    # Voor Week Monitor
        └── enums.xlsx
```

## Data Refresh

### Via Dashboard (aanbevolen)

1. Ga naar **🔄 Data Beheer** in het menu
2. Klik op **Data Ophalen**
3. Volg de voortgang
4. Nieuwe run wordt automatisch geselecteerd

### Via CLI

```bash
# Met cache (sneller, gebruikt opgeslagen API responses)
python refresh_data.py

# Alles opnieuw ophalen uit HubSpot
python refresh_data.py --refresh
```

## Dashboard Pagina's

### 💊 Coach Prestatie (hoofdpagina)

- **Kerncijfers** - Gemiddelden en mediaan
- **Scatterplot** - Deals vs winstpercentage per coach
- **Histogram** - Verdeling winstpercentages
- **Status verdeling** - Aantal coaches per status
- **Coach tabel** - Sorteerbaar overzicht

**Sidebar filters:**
- Periode selectie (1/3/6 maanden)
- Coaches uitsluiten
- Top X% filter
- Minimum deals drempel
- Status berekening configuratie

### 📖 Uitleg

Handleiding met uitleg over:
- Wat de statussen betekenen
- Hoe de grafieken te lezen
- Waarom minimum deals belangrijk zijn

### 🔄 Data Beheer

- **Dataset selector** - Wissel tussen opgeslagen runs
- **Refresh knop** - Haal nieuwe data op met voortgang
- **Run historie** - Bekijk en verwijder oude runs

### 📊 Week Monitor

- **Alerts** - Coaches met afwijkende prestaties deze week
- **Coach detail** - Weektrends per coach (won rate, nabeller %)
- **Overzicht** - Alle coaches laatste week

**Alert thresholds (configureerbaar):**
- Nabeller % drempel (default 20%)
- Won rate daling t.o.v. 4-weeks gemiddelde (default 15%)
- Minimum deals per week (default 5)

### 👥 Coach Beschikbaarheid

Google Sheets integratie voor coach beschikbaarheid data.

## NA_Pool Export (Hoofdpagina)

Push eligible coaches naar Google Sheets voor lead distributie.

### Setup Google Sheets

1. **Service Account aanmaken:**
   - Ga naar Google Cloud Console → IAM & Admin → Service Accounts
   - Maak een service account aan
   - Download JSON key naar `secrets/service_account.json`

2. **Sheet delen:**
   - Open het `client_email` uit de JSON
   - Deel de Google Sheet met dat email als **Editor**

3. **Sheet ID:** `1f3fbZasyqt_UwZtXuShHJ8f9H66lUB3KE20vj6OFxwI`
   - Tab: `NA_Pool`

### Hoe het werkt

De NA_Pool Export sectie op de hoofdpagina heeft:

**Pre-filters (beïnvloeden mediaan):**
- Nabeller % drempel - coaches boven drempel uitgesloten
- Minimum deals - coaches met te weinig deals uitgesloten
- Top % (sidebar) - alleen beste X% meegenomen

**Status Thresholds:**
- Minimum deals voor 'Goed' - bepaalt Goed vs Matig status
- Mediaan wordt dynamisch berekend op gefilterde coaches

**Google Sheets Parameters:**
- cap_dag - max leads per dag per coach
- cap_week - max leads per week per coach
- weight - gewicht voor lead verdeling

**Output naar NA_Pool tab:**
```
owner_id | coach_naam | eligible | weight | cap_dag | cap_week | exclude_manual | laatst_bijgewerkt | note
```

### Code structuur

```python
# gsheets_writer.py - Google Sheets writer
push_to_na_pool(df, weight, cap_dag, cap_week)  # Push coaches naar NA_Pool
get_gspread_client()  # Auth via service account
test_connection()  # Test verbinding

# dashboard_app.py - NA_Pool Export sectie (regel 617+)
# - Pre-filters + mediaan berekening
# - Status berekening (Goed/Matig/Uitsluiten)
# - Top % filter uit sidebar
# - Push knop
```

## ETL Pipeline

De data flow:

```
HubSpot API
    ↓
fetch_hubspot.py
    ↓ (contacts, associations, deals)
etl/cache/
    ↓
calculate_metrics.py
    ↓ (metrics, eligibility)
data/YYYYMMDD_HHMMSS/coach_eligibility.xlsx
    ↓
Dashboard
```

**Stappen:**
1. **Contacten** - Haal NA contacten op (aangebracht_door = "Nationale Apotheek")
2. **Associations** - Koppel contacten aan deals
3. **Deals** - Haal deal details op
4. **Enums** - Laad pipeline/stage configuratie
5. **Metrics** - Bereken win rates per periode
6. **Eligibility** - Bepaal coach status

## Configuratie

### .env variabelen

```bash
# Vereist
HUBSPOT_PAT=pat-xx-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Google Sheets (optioneel - kan ook via secrets/ folder)
GOOGLE_SA_JSON_PATH=secrets/service_account.json

# Optioneel (defaults)
AANGEBRACHT_DOOR_VALUE=Nationale Apotheek
PIPELINE_STATUS_BEGELEIDING=15413220
PIPELINE_NABELLER=38341389
```

### Google Service Account

Plaats `service_account.json` in de `secrets/` map, of stel het pad in via:
```bash
export GOOGLE_SA_JSON_PATH=/pad/naar/service_account.json
```

De code zoekt automatisch naar `secrets/service_account.json` als fallback.

### Stage Mapping

Edit `data/mapping.xlsx` om te configureren welke deal stages als WON/LOST/OPEN tellen.

## Uitgefilterde Data

Het dashboard filtert automatisch:
- Nabellers (pattern match)
- Rookvrij en Fitter Het Gooi
- 167331984 (onbekend)
- UNKNOWN
- benVitaal Coaching (gestopt)
- SportQube Algemeen (doorstuur)

## Troubleshooting

### "HUBSPOT_PAT niet gevonden"

Zorg dat `.env` bestaat met een geldige token:
```bash
cp .env.example .env
# Edit .env
```

### "No coach_eligibility found"

Run eerst de ETL:
```bash
python refresh_data.py --refresh
```

### Dashboard toont oude data

1. Ga naar Data Beheer
2. Check welke run geselecteerd is
3. Klik op "Data Ophalen" voor nieuwe data

### Cache wissen

```bash
rm -rf etl/cache/*
python refresh_data.py --refresh
```

## Development

### Requirements

- Python 3.8+
- Streamlit 1.28+
- Packages: pandas, plotly, requests, openpyxl

### Lokaal testen

```bash
# Activeer venv
source venv/bin/activate

# Run dashboard
streamlit run dashboard_app.py

# Of met auto-reload
streamlit run dashboard_app.py --server.runOnSave true
```
