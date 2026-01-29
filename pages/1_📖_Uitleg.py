import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Uitleg - Nationale Apotheek",
    page_icon="📖",
    layout="wide",
)

st.title("📖 Handleiding Coach Dashboard")
st.markdown("### Nationale Apotheek")
st.markdown("*Deze pagina legt stap voor stap uit hoe je het dashboard moet lezen en interpreteren.*")

st.markdown("""
<div style='background-color: #cce5ff; padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;'>
    <p style='margin: 0; color: #004085; font-size: 1.1em;'>
        ⬅️ <b>Terug naar dashboard?</b> Klik links in het menu op <b>"dashboard_app"</b>
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SECTION 0: PAGINA STRUCTUUR
# ============================================================================

st.markdown("---")
st.markdown("## 📋 Pagina-overzicht")

st.markdown("""
Het dashboard bestaat uit meerdere pagina's, bereikbaar via het linkermenu:

| Pagina | Doel |
|--------|------|
| **💊 Dashboard** | Hoofdoverzicht: kerncijfers, scatterplot, histogram, statustabel |
| **📖 Uitleg** | Deze handleiding |
| **🔄 Data Beheer** | Data ophalen uit HubSpot, runs beheren |
| **📊 Week Monitor** | Wekelijkse trends en alerts per coach |
| **👥 Coach Beschikbaarheid** | Beschikbaarheid van coaches |
| **📤 NA_Pool Export** | Coaches selecteren en pushen naar Google Sheets |
""")

# ============================================================================
# SECTION 1: GLOBALE VS LOKALE FILTERS
# ============================================================================

st.markdown("---")
st.markdown("## 1. Globale en lokale filters")

st.info("""
**Globale filters** staan bovenaan de sidebar en gelden voor **alle pagina's**:
- **Periode** (1m / 3m / 6m) — bepaalt welke kolommen gebruikt worden
- **Coaches uitsluiten** — verwijdert geselecteerde coaches overal

**Lokale filters** staan onder de globale filters en gelden alleen voor de **huidige pagina**.
Bijvoorbeeld: "Minimum deals" op het dashboard beïnvloedt de NA_Pool Export **niet**.
""")

st.markdown("""
| Filter | Dashboard | NA_Pool Export | Week Monitor |
|--------|-----------|----------------|--------------|
| Periode (1m/3m/6m) | Globaal | Globaal | Globaal |
| Coach exclusie | Globaal | Globaal | Globaal |
| Minimum deals | Lokaal | Lokaal (eigen) | Lokaal (eigen) |
| Top % | Lokaal | Lokaal (eigen) | — |
| Minimum conversie | Lokaal | — | — |
| Nabeller % drempel | — | Lokaal | Lokaal (eigen) |
| Laag2 threshold | — | Lokaal | — |
| cap/weight | — | Lokaal | — |
""")

st.markdown("""
**Filter-banner:** Bovenaan elke pagina zie je een gekleurde balk die toont welke filters
actief zijn. Zo weet je altijd welke data je bekijkt.
""")

# ============================================================================
# SECTION 2: MEDIAAN
# ============================================================================

st.markdown("---")
st.markdown("## 2. Over de mediaan")

st.info("""
**De mediaan (rode lijn in grafieken)** wordt **dynamisch berekend** op basis van:
- De gekozen periode (1, 3 of 6 maanden)
- Welke coaches zijn uitgefilterd
- De huidige dataset

*De mediaan is het middelste winstpercentage. 50% van de coaches scoort hoger, 50% lager.*

**Let op:** Het dashboard en de NA_Pool Export berekenen elk hun **eigen mediaan**.
De NA_Pool mediaan houdt rekening met extra pre-filters (nabeller %, minimum deals).
""")

# ============================================================================
# SECTION 3: STATUSSEN
# ============================================================================

st.markdown("---")
st.markdown("## 3. Wat betekenen de statussen?")

st.markdown("""
Elke coach krijgt een **dynamische status** op basis van het aantal deals en
het winstpercentage ten opzichte van de mediaan.
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✅ Goed")
    st.success("""
    **Beste presteerders**

    - Winstpercentage **boven de mediaan**
    - Voldoende deals (standaard: minimaal 14)
    - Statistisch betrouwbaar door voldoende volume
    """)

    st.markdown("### ⭐ Matig")
    st.info("""
    **Opkomende coaches**

    - Minder deals dan Goed (maar minimaal de helft)
    - Winstpercentage minimaal 80% van de mediaan
    - Actief en redelijk presterend
    """)

with col2:
    st.markdown("### ❌ Uitsluiten")
    st.error("""
    **Niet in aanmerking**

    Twee mogelijke redenen:

    **Reden 1: Te weinig deals**
    - Zelfs met hoog winstpercentage niet betrouwbaar

    **Reden 2: Onder de mediaan**
    - Winstpercentage onder de drempel
    """)

    st.markdown("### ⚪ Geen data")
    st.warning("""
    **Geen recente activiteit**

    - 0 deals in de geselecteerde periode
    - Kan niet beoordeeld worden
    """)

# ============================================================================
# SECTION 4: MINIMUM DEALS
# ============================================================================

st.markdown("---")
st.markdown("## 4. Waarom is een minimum aantal deals belangrijk?")

st.markdown("Een winstpercentage is alleen **betrouwbaar** bij voldoende deals.")

example_data = {
    "Coach": ["Anna", "Bert", "Clara"],
    "Deals": [2, 10, 50],
    "Gewonnen": [2, 7, 35],
    "Winst%": ["100%", "70%", "70%"],
    "Betrouwbaar?": ["❌ Nee", "⚠️ Twijfelachtig", "✅ Ja"],
}
st.dataframe(pd.DataFrame(example_data), use_container_width=True, hide_index=True)

st.markdown("""
> **Vuistregel:** Pas bij ~14+ deals wordt een winstpercentage statistisch betekenisvol.
""")

# ============================================================================
# SECTION 5: GRAFIEKEN
# ============================================================================

st.markdown("---")
st.markdown("## 5. Hoe lees je de grafieken?")

st.markdown("### 📊 Grafiek 1: Deals vs Winstpercentage (Scatter)")
st.markdown("""
- Elke **stip is één coach**
- **Horizontale as (→):** Aantal deals
- **Verticale as (↑):** Winstpercentage
- **Rode stippellijn:** Mediaan
- **Blauwe stippellijn:** Minimum deals

**Interpretatie:**
- **Rechtsboven:** Veel deals EN hoog percentage = toppresteerders
- **Rechtsonder:** Veel deals maar laag percentage = consistent onderpresterend
- **Linksboven:** Weinig deals maar hoog percentage = mogelijk geluk
- **Linksonder:** Weinig deals en laag percentage = inactief of slecht
""")

st.markdown("### 📊 Grafiek 2: Verdeling Winstpercentage (Histogram)")
st.markdown("""
- Links van de rode lijn = **onder gemiddeld**
- Rechts van de rode lijn = **boven gemiddeld**
- Hoe hoger de staaf, hoe meer coaches in die groep
""")

st.markdown("### 📊 Grafiek 3: Aantal Coaches per Status")
st.markdown("Een staafdiagram met het aantal coaches per status-categorie.")

# ============================================================================
# SECTION 6: TABEL KOLOMMEN
# ============================================================================

st.markdown("---")
st.markdown("## 6. Hoe lees je de tabel?")

st.markdown("""
| Kolom | Betekenis |
|-------|-----------|
| **Coach** | Naam van de coach |
| **Status** | Dynamische status (Goed, Matig, etc.) |
| **Deals** | Aantal deals in de geselecteerde periode |
| **Winst%** | Winstpercentage in de geselecteerde periode |
| **Warme aanvraag** | Aantal warme aanvragen in de periode |
| **Info aanvraag** | Aantal informatie-aanvragen in de periode |
| **Boven drempel** | ✅ als de coach meer dan het minimum aantal deals heeft |

**Warme aanvraag** en **Info aanvraag** geven inzicht in de **drukte per coach**.
Een coach met veel warme aanvragen heeft meer nieuwe leads in behandeling.

**Tip:** Deze kolommen zijn pas beschikbaar na een verse data-run.
Bij oudere data-runs worden ze niet getoond.
""")

# ============================================================================
# SECTION 7: NA_POOL EXPORT
# ============================================================================

st.markdown("---")
st.markdown("## 7. NA_Pool Export")

st.markdown("""
De **📤 NA_Pool Export** pagina is een **zelfstandige pagina** met eigen filters.

**Hoe werkt het?**
1. De globale filters (periode + exclusie) worden gedeeld met het dashboard
2. De NA_Pool heeft **eigen** sliders voor nabeller %, minimum deals, top %, en laag2 drempel
3. Op basis van deze filters wordt een **eigen mediaan** berekend
4. Coaches worden geclassificeerd als Goed, Matig, of Uitsluiten
5. Alleen Goed en Matig coaches worden naar Google Sheets gepusht

**Belangrijk:** De NA_Pool sliders beïnvloeden het dashboard **niet**, en andersom.
Alleen de globale filters (periode en exclusie) worden gedeeld.
""")

# ============================================================================
# SECTION 8: UITGEFILTERDE DATA
# ============================================================================

st.markdown("---")
st.markdown("## 8. Welke data is automatisch uitgefilterd?")

st.error("""
**Automatisch verwijderde entries:**

| Naam | Reden |
|------|-------|
| Nabeller * | Dit zijn nabellers, geen coaches |
| Rookvrij en Fitter Het Gooi | Doorstuur account |
| 167331984 | Onbekend account |
| UNKNOWN | Onbekende entries |
| benVitaal Coaching | Gestopt account |
| SportQube Algemeen | Doorstuur account |

Deze worden op **alle pagina's** automatisch verwijderd.
""")

# ============================================================================
# SECTION 9: DATA BEHEER
# ============================================================================

st.markdown("---")
st.markdown("## 9. Data vernieuwen")

st.markdown("""
1. Ga naar **🔄 Data Beheer** in het linkermenu
2. Klik op **Data Ophalen**
3. Wacht tot de voortgang 100% is
4. De nieuwe data wordt automatisch geselecteerd

**Run historie:** Elke keer dat je data ophaalt, wordt een nieuwe "run" opgeslagen.
Je kunt altijd terug naar eerdere runs via de dropdown in Data Beheer.
""")

# ============================================================================
# SECTION 10: FAQ
# ============================================================================

st.markdown("---")
st.markdown("## 10. Veelgestelde vragen")

with st.expander("Waarom heeft coach X een hoog percentage maar status 'Uitsluiten'?"):
    st.markdown("""
    Dit komt door **te weinig deals**. Een hoog winstpercentage op basis van
    weinig deals is statistisch niet betrouwbaar.
    """)

with st.expander("Wat is het verschil tussen 'ruwe winrate' en 'winstpercentage'?"):
    st.markdown("""
    - **Ruwe winrate:** Simpelweg gewonnen ÷ totaal × 100%
    - **Winstpercentage (smoothed):** Gecorrigeerde versie die rekening houdt
      met onzekerheid bij weinig deals
    """)

with st.expander("Beïnvloeden dashboard sliders de NA_Pool?"):
    st.markdown("""
    **Nee.** Alleen de globale filters (periode en coach exclusie) worden gedeeld.
    Alle andere sliders zijn pagina-lokaal en beïnvloeden andere pagina's niet.
    """)

with st.expander("Wat zijn 'Warme aanvraag' en 'Info aanvraag'?"):
    st.markdown("""
    - **Warme aanvraag:** Deals in de dealstage "Warme aanvraag" — leads die actief
      interesse hebben getoond
    - **Info aanvraag:** Deals in de dealstage "Informatie aangevraagd" — leads die
      informatie hebben opgevraagd

    Deze kolommen geven inzicht in de drukte per coach.
    Ze zijn beschikbaar na een verse data-run met de bijgewerkte ETL.
    """)

with st.expander("Ik zie 'Warme aanvraag' / 'Info aanvraag' niet in de tabel"):
    st.markdown("""
    Deze kolommen worden pas beschikbaar na een **verse data-run** met de
    bijgewerkte ETL. Oudere runs bevatten deze kolommen niet.

    Ga naar **🔄 Data Beheer** en haal verse data op.
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>📖 <b>Handleiding - Coach Prestatie Dashboard</b></p>
    <p>💊 Nationale Apotheek</p>
    <p>Vragen? Neem contact op met de data-afdeling.</p>
</div>
""", unsafe_allow_html=True)
