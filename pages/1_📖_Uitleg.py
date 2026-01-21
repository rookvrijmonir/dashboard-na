import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Uitleg - Nationale Apotheek",
    page_icon="📖",
    layout="wide"
)

st.title("📖 Handleiding Coach Dashboard")
st.markdown("### Nationale Apotheek")
st.markdown("*Deze pagina legt stap voor stap uit hoe je het dashboard moet lezen en interpreteren.*")

# Terug naar dashboard instructie
st.markdown("""
<div style='background-color: #cce5ff; padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;'>
    <p style='margin: 0; color: #004085; font-size: 1.1em;'>
        ⬅️ <b>Terug naar dashboard?</b> Klik links in het menu op <b>"dashboard_app"</b>
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SECTION 0: BELANGRIJKE INFORMATIE
# ============================================================================

st.markdown("---")
st.markdown("## 📊 Belangrijke Informatie")

st.info("""
**Over de mediaan (rode lijn in grafieken):**

De mediaan wordt **dynamisch berekend** op basis van de geselecteerde periode en filters.
Dit betekent dat de waarde kan verschillen afhankelijk van:
- De gekozen periode (1, 3 of 6 maanden)
- Welke coaches zijn uitgefilterd
- De huidige dataset

*De mediaan is het middelste winstpercentage. 50% van de coaches scoort hoger, 50% lager.*
""")

# ============================================================================
# SECTION 1: WAT IS DIT DASHBOARD?
# ============================================================================

st.markdown("---")
st.markdown("## 1. Wat is dit dashboard?")

st.markdown("""
Dit dashboard toont de **prestaties van coaches** op basis van hun deals.
Je kunt zien:
- Hoeveel deals elke coach heeft gehad
- Hoeveel daarvan gewonnen zijn (winstpercentage)
- Hoe coaches zich verhouden tot het gemiddelde
- Welke coaches in aanmerking komen voor bepaalde programma's

**Nieuw:** Je kunt nu zelf de data verversen via de **🔄 Data Beheer** pagina!
""")

# ============================================================================
# SECTION 2: DE STATUSSEN UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 2. Wat betekenen de statussen?")

st.markdown("""
Elke coach krijgt een **status** toegewezen. Dit bepaalt of ze in aanmerking komen
voor coaching programma's of andere acties.

**Let op:** De status wordt **dynamisch berekend** in het dashboard. Je kunt de
drempelwaarden aanpassen in de sidebar onder "Status Berekening".
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✅ Laag 2")
    st.success("""
    **Beste presteerders**

    Deze coaches:
    - Hebben een winstpercentage **boven de mediaan**
    - Hebben voldoende deals (standaard: minimaal 14)
    - Zijn statistisch betrouwbaar door voldoende volume

    *Dit zijn de coaches die consistent goed presteren.*
    """)

    st.markdown("### ⭐ Laag 3")
    st.info("""
    **Opkomende coaches**

    Deze coaches:
    - Hebben minder deals dan Laag 2 (maar minimaal de helft)
    - Winstpercentage is minimaal 80% van de mediaan
    - Zijn wel actief en presteren redelijk

    *Deze coaches verdienen aandacht en ondersteuning.*
    """)

with col2:
    st.markdown("### ❌ Uitsluiten")
    st.error("""
    **Niet in aanmerking**

    Deze coaches worden uitgesloten om twee mogelijke redenen:

    **Reden 1: Te weinig deals**
    - Minder dan de minimum drempel
    - Zelfs met een hoog winstpercentage is dit niet betrouwbaar
    - Voorbeeld: 75% winst op 3 deals kan puur geluk zijn

    **Reden 2: Onder de mediaan**
    - Winstpercentage onder de (aangepaste) mediaan
    - Ook met veel deals presteren ze onder gemiddeld
    """)

    st.markdown("### ⚪ Geen data")
    st.warning("""
    **Geen recente activiteit**

    Deze coaches:
    - Hebben 0 deals in de geselecteerde periode
    - Kunnen niet beoordeeld worden
    - Zijn mogelijk inactief of nieuw
    """)

# ============================================================================
# SECTION 3: WAAROM MINIMUM AANTAL DEALS?
# ============================================================================

st.markdown("---")
st.markdown("## 3. Waarom is een minimum aantal deals belangrijk?")

st.markdown("""
Een winstpercentage is alleen **betrouwbaar** als het gebaseerd is op voldoende deals.
""")

# Visual example
st.markdown("### Voorbeeld:")

example_data = {
    'Coach': ['Anna', 'Bert', 'Clara'],
    'Deals': [2, 10, 50],
    'Gewonnen': [2, 7, 35],
    'Winst%': ['100%', '70%', '70%'],
    'Betrouwbaar?': ['❌ Nee', '⚠️ Twijfelachtig', '✅ Ja']
}
example_df = pd.DataFrame(example_data)
st.dataframe(example_df, use_container_width=True, hide_index=True)

st.markdown("""
- **Anna** heeft 100% winst, maar op slechts 2 deals. Dit kan toeval zijn.
- **Bert** heeft 70% winst op 10 deals. Iets betrouwbaarder, maar nog steeds onzeker.
- **Clara** heeft 70% winst op 50 deals. Dit is een betrouwbaar patroon.

> **Vuistregel:** Pas bij ~14+ deals wordt een winstpercentage statistisch betekenisvol.
> Je kunt deze drempel aanpassen in de sidebar.
""")

# ============================================================================
# SECTION 4: DE GRAFIEKEN UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 4. Hoe lees je de grafieken?")

st.markdown("### 📊 Grafiek 1: Deals vs Winstpercentage (Scatter)")
st.markdown("""
**Wat zie je?**
- Elke **stip is één coach**
- **Horizontale as (→):** Aantal deals - meer naar rechts = meer deals
- **Verticale as (↑):** Winstpercentage - hoger = beter percentage
- **Kleuren:** Verschillende statussen
- **Rode stippellijn (horizontaal):** De mediaan
- **Blauwe stippellijn (verticaal):** Je ingestelde minimum deals

**Hoe interpreteer je dit?**
- **Rechtsboven:** Veel deals EN hoog percentage = beste coaches
- **Rechtsonder:** Veel deals maar laag percentage = consistent onderpresterend
- **Linksboven:** Weinig deals maar hoog percentage = mogelijk geluk, nog niet bewezen
- **Linksonder:** Weinig deals en laag percentage = inactief of slecht

**Voorbeeld interpretatie:**
> "Coach X staat rechtsboven: veel deals én hoog winstpercentage. Dit is een toppresteerder.
> Coach Y staat linksboven met 75% maar slechts 3 deals - dit kan toeval zijn."
""")

st.markdown("### 📊 Grafiek 2: Verdeling Winstpercentage (Histogram)")
st.markdown("""
**Wat zie je?**
- Een staafdiagram dat laat zien hoeveel coaches in elke winstpercentage-groep zitten
- De rode stippellijn toont de **mediaan** (het midden)

**Hoe interpreteer je dit?**
- Coaches links van de rode lijn presteren **onder gemiddeld**
- Coaches rechts van de rode lijn presteren **boven gemiddeld**
- Hoe hoger de staaf, hoe meer coaches in die groep zitten

**Voorbeeld interpretatie:**
> "De meeste coaches zitten tussen 40% en 60% winstpercentage.
> De mediaan is het middelste percentage - de helft presteert beter, de helft slechter."
""")

st.markdown("### 📊 Grafiek 3: Aantal Coaches per Status")
st.markdown("""
**Wat zie je?**
- Een staafdiagram met het aantal coaches per status

**Hoe interpreteer je dit?**
- Je ziet direct hoeveel coaches in elke categorie vallen
- Dit geeft een overzicht van de verdeling van je team

**Voorbeeld interpretatie:**
> "Van de 105 coaches zijn er 16 in Laag 2 (top presteerders) en 51 uitgesloten."
""")

# ============================================================================
# SECTION 5: PERIODE SELECTIE
# ============================================================================

st.markdown("---")
st.markdown("## 5. Periode selectie")

st.markdown("""
In de sidebar kun je kiezen tussen drie periodes:

| Periode | Betekenis |
|---------|-----------|
| **1 maand** | Meest recente prestaties |
| **3 maanden** | Medium-termijn trend |
| **6 maanden** | Langere termijn stabiliteit |

**Belangrijk:** De gekozen periode beïnvloedt **alle** grafieken en berekeningen!

- De mediaan wordt herberekend
- De status wordt herberekend
- De tabel toont deals/winst% voor die periode
""")

# ============================================================================
# SECTION 6: DE TABEL UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 6. Hoe lees je de tabel?")

st.markdown("""
De tabel onderaan het dashboard toont alle coaches met hun cijfers **voor de geselecteerde periode**.

| Kolom | Betekenis |
|-------|-----------|
| **Coach** | Naam van de coach |
| **Status** | De berekende status (Laag 2, Laag 3, etc.) |
| **Deals** | Aantal deals in de geselecteerde periode |
| **Winst%** | Winstpercentage in de geselecteerde periode |
| **Boven drempel** | ✅ als de coach meer dan het minimum aantal deals heeft |

**Tips voor de tabel:**
- Klik op een kolomkop om te sorteren
- Wissel van periode in de sidebar om trends te zien
- Een coach met dalende percentages over tijd verdient aandacht
""")

# ============================================================================
# SECTION 7: DATA FILTERING
# ============================================================================

st.markdown("---")
st.markdown("## 7. Welke data is uitgefilterd?")

st.markdown("""
Niet alle entries in de brondata zijn echte coaches. De volgende worden
**automatisch uitgefilterd** en tellen niet mee in de statistieken:
""")

st.error("""
**Uitgefilterde entries:**

| Naam | Reden |
|------|-------|
| Nabeller * | Dit zijn nabellers, geen coaches |
| Rookvrij en Fitter Het Gooi | Dit is een programma, geen persoon |
| 167331984 | Onbekend account |
| UNKNOWN | Onbekende entries |
| benVitaal Coaching | Gestopt account |
| SportQube Algemeen | Doorstuur account |

Deze entries zouden de statistieken vervuilen als ze meegeteld worden,
omdat ze geen echte coach-prestaties vertegenwoordigen.
""")

st.info("""
**Extra filtering:** In de sidebar kun je ook handmatig coaches uitsluiten
via de "Coaches Uitsluiten" optie.
""")

# ============================================================================
# SECTION 8: DATA BEHEER
# ============================================================================

st.markdown("---")
st.markdown("## 8. Data vernieuwen")

st.markdown("""
De data komt uit HubSpot en kan vernieuwd worden via de **🔄 Data Beheer** pagina.

**Hoe werkt het?**
1. Ga naar **🔄 Data Beheer** in het linkermenu
2. Klik op de **Data Ophalen** knop
3. Wacht tot de voortgang 100% is
4. De nieuwe data wordt automatisch geselecteerd

**Run historie:**
Elke keer dat je data ophaalt, wordt een nieuwe "run" opgeslagen.
Je kunt altijd terug naar eerdere runs via de dropdown in Data Beheer.

**Tip:** Kijk onderaan het dashboard voor de datum van de huidige dataset.
""")

# ============================================================================
# SECTION 9: VEELGESTELDE VRAGEN
# ============================================================================

st.markdown("---")
st.markdown("## 9. Veelgestelde vragen")

with st.expander("Waarom heeft coach X een hoog percentage maar status 'Uitsluiten'?"):
    st.markdown("""
    Dit komt door **te weinig deals**. Een hoog winstpercentage op basis van
    weinig deals is statistisch niet betrouwbaar. Het kan puur geluk zijn.

    **Voorbeeld:** Een coach met 2 gewonnen deals van 3 totaal heeft 66% winst.
    Maar dit zegt weinig over hun echte prestaties.

    Je kunt de minimum deals drempel aanpassen in de sidebar.
    """)

with st.expander("Wat is het verschil tussen 'ruwe winrate' en 'winstpercentage'?"):
    st.markdown("""
    - **Ruwe winrate:** Simpelweg gewonnen ÷ totaal × 100%
    - **Winstpercentage (smoothed):** Een gecorrigeerde versie die rekening houdt
      met onzekerheid bij weinig deals

    Bij weinig deals wordt het percentage "naar het gemiddelde getrokken" om
    extreme uitschieters te voorkomen.
    """)

with st.expander("Hoe vaak moet ik de data verversen?"):
    st.markdown("""
    Dat hangt af van je behoefte:

    - **Dagelijks:** Als je actuele cijfers nodig hebt
    - **Wekelijks:** Voor regelmatige monitoring
    - **Maandelijks:** Voor periodieke rapportages

    Ga naar **🔄 Data Beheer** om nieuwe data op te halen.
    """)

with st.expander("Kan ik de data exporteren?"):
    st.markdown("""
    Ja! Meerdere opties:

    1. **Vanuit de tabel:** Selecteer en kopieer (Ctrl+C)
    2. **Excel bestand:** De brondata staat in `data/<run_id>/coach_eligibility.xlsx`
    3. **Sorteren:** Klik op kolomkoppen in de tabel
    """)

with st.expander("Hoe verander ik de status berekening?"):
    st.markdown("""
    In de sidebar onder **"⭐ Status Berekening"** kun je aanpassen:

    - **Minimum deals voor Laag 2:** Standaard 14
    - De Laag 3 drempel is automatisch de helft hiervan

    De status wordt direct herberekend als je de slider aanpast.
    """)

# ============================================================================
# SECTION 10: SAMENVATTING
# ============================================================================

st.markdown("---")
st.markdown("## 10. Samenvatting")

st.info("""
**De belangrijkste punten:**

1. **Status bepaalt geschiktheid** - Alleen Laag 2 en Laag 3 komen in aanmerking
2. **Volume is belangrijk** - Minimum deals drempel is configureerbaar (standaard 14)
3. **Mediaan is dynamisch** - Wordt berekend op basis van periode en filters
4. **Grafieken lezen** - Rechtsboven in de scatter = beste coaches
5. **Periode kiezen** - 1/3/6 maanden voor verschillende perspectieven
6. **Data vernieuwen** - Via de 🔄 Data Beheer pagina
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
