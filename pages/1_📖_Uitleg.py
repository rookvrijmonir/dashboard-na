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
# SECTION 0: BELANGRIJKE CIJFERS
# ============================================================================

st.markdown("---")
st.markdown("## 📊 Belangrijke Cijfers")

st.info("""
**Medianen per periode (de rode lijnen in de grafieken):**
- **1 maand:** 55.6%
- **3 maanden:** 54.5%
- **6 maanden:** 50.0%

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
""")

# ============================================================================
# SECTION 2: DE STATUSSEN UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 2. Wat betekenen de statussen?")

st.markdown("""
Elke coach krijgt een **status** toegewezen. Dit bepaalt of ze in aanmerking komen
voor coaching programma's of andere acties.
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✅ Laag 2")
    st.success("""
    **Beste presteerders**

    Deze coaches:
    - Hebben een winstpercentage **boven de mediaan** van die periode
    - Hebben **minimaal 14 deals** in de afgelopen maand
    - Zijn statistisch betrouwbaar door voldoende volume

    *Dit zijn de coaches die consistent goed presteren.*
    """)

    st.markdown("### ⭐ Laag 3")
    st.info("""
    **Opkomende coaches**

    Deze coaches:
    - Hebben minder deals dan Laag 2
    - Zijn wel actief en presteren redelijk
    - Hebben potentie om door te groeien naar Laag 2

    *Deze coaches verdienen aandacht en ondersteuning.*
    """)

with col2:
    st.markdown("### ❌ Uitsluiten")
    st.error("""
    **Niet in aanmerking**

    Deze coaches worden uitgesloten om twee mogelijke redenen:

    **Reden 1: Te weinig deals**
    - Minder dan 14 deals in de afgelopen maand
    - Zelfs met een hoog winstpercentage is dit niet betrouwbaar
    - Voorbeeld: 75% winst op 3 deals kan puur geluk zijn

    **Reden 2: Onder de mediaan**
    - Winstpercentage onder de mediaan voor die periode
    - Ook met veel deals presteren ze onder gemiddeld
    """)

    st.markdown("### Geen data")
    st.warning("""
    **Geen recente activiteit**

    Deze coaches:
    - Hebben 0 deals in de afgelopen maand
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
""")

# ============================================================================
# SECTION 4: DE GRAFIEKEN UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 4. Hoe lees je de grafieken?")

st.markdown("### 📊 Grafiek 1: Verdeling Winstpercentage")
st.markdown("""
**Wat zie je?**
- Een staafdiagram (histogram) dat laat zien hoeveel coaches in elke winstpercentage-groep zitten
- De rode stippellijn toont de **mediaan** (het midden)

**Hoe interpreteer je dit?**
- Coaches links van de rode lijn presteren **onder gemiddeld**
- Coaches rechts van de rode lijn presteren **boven gemiddeld**
- Hoe hoger de staaf, hoe meer coaches in die groep zitten

**Voorbeeld interpretatie:**
> "De meeste coaches zitten tussen 40% en 60% winstpercentage.
> De mediaan is het middelste percentage - de helft presteert beter, de helft slechter. Let op: de mediaan verschilt per periode!"
""")

st.markdown("### 📊 Grafiek 2: Aantal Coaches per Status")
st.markdown("""
**Wat zie je?**
- Een staafdiagram met het aantal coaches per status

**Hoe interpreteer je dit?**
- Je ziet direct hoeveel coaches in elke categorie vallen
- Dit geeft een overzicht van de verdeling van je team

**Voorbeeld interpretatie:**
> "Van de 105 coaches zijn er 16 in Laag 2 (top presteerders) en 51 uitgesloten."
""")

st.markdown("### 📊 Grafiek 3: Deals vs Winstpercentage (Scatter)")
st.markdown("""
**Wat zie je?**
- Elke **stip is één coach**
- **Horizontale as (→):** Aantal deals - meer naar rechts = meer deals
- **Verticale as (↑):** Winstpercentage - hoger = beter percentage
- **Kleuren:** Verschillende statussen
- **Rode stippellijn:** De mediaan (verschilt per periode!)

**Hoe interpreteer je dit?**
- **Rechtsboven:** Veel deals EN hoog percentage = beste coaches
- **Rechtsonder:** Veel deals maar laag percentage = consistent onderpresterend
- **Linksboven:** Weinig deals maar hoog percentage = mogelijk geluk, nog niet bewezen
- **Linksonder:** Weinig deals en laag percentage = inactief of slecht

**Voorbeeld interpretatie:**
> "Coach X staat rechtsboven: veel deals én hoog winstpercentage. Dit is een toppresteerder.
> Coach Y staat linksboven met 75% maar slechts 3 deals - dit kan toeval zijn."
""")

st.markdown("### 📊 Grafiek 4: Vergelijking 1, 3 en 6 Maanden")
st.markdown("""
**Wat zie je?**
- Dezelfde verdeling als grafiek 1, maar dan over verschillende periodes
- Klik op de knoppen om te wisselen tussen periodes

**Hoe interpreteer je dit?**
- Vergelijk hoe de verdeling verandert over tijd
- Een stabiele verdeling = consistente prestaties
- Grote verschuivingen = seizoenseffecten of veranderingen in het team
""")

# ============================================================================
# SECTION 5: DE TABEL UITGELEGD
# ============================================================================

st.markdown("---")
st.markdown("## 5. Hoe lees je de tabel?")

st.markdown("""
De tabel onderaan het dashboard toont alle coaches met hun cijfers.

| Kolom | Betekenis |
|-------|-----------|
| **Coach Naam** | Naam van de coach |
| **Deals (1/3/6 mnd)** | Aantal deals in die periode |
| **Winst % (1/3/6 mnd)** | Winstpercentage in die periode |
| **Status** | De toegewezen status (Laag 2, Laag 3, etc.) |

**Tips voor de tabel:**
- Klik op een kolomkop om te sorteren
- Vergelijk de 1-maand met 3-maand cijfers om trends te zien
- Een coach met dalende percentages over tijd verdient aandacht
""")

# ============================================================================
# SECTION 6: DATA FILTERING
# ============================================================================

st.markdown("---")
st.markdown("## 6. Welke data is uitgefilterd?")

st.markdown("""
Niet alle entries in de brondata zijn echte coaches. De volgende worden
**automatisch uitgefilterd** en tellen niet mee in de statistieken:
""")

st.error("""
**Uitgefilterde entries:**

| Naam | Reden |
|------|-------|
| Nabeller Rookvrij | Dit is een nabeller, geen coach |
| Rookvrij en Fitter Het Gooi | Dit is een programma, geen persoon |

Deze entries zouden de statistieken vervuilen als ze meegeteld worden,
omdat ze geen echte coach-prestaties vertegenwoordigen.
""")

st.info("""
**Let op:** Als er in de toekomst meer nabellers of programma's worden toegevoegd
aan de brondata, moeten deze ook uitgefilterd worden in de dashboard code.
""")

# ============================================================================
# SECTION 7: VEELGESTELDE VRAGEN
# ============================================================================

st.markdown("---")
st.markdown("## 7. Veelgestelde vragen")

with st.expander("Waarom heeft coach X een hoog percentage maar status 'Uitsluiten'?"):
    st.markdown("""
    Dit komt door **te weinig deals**. Een hoog winstpercentage op basis van
    1-5 deals is statistisch niet betrouwbaar. Het kan puur geluk zijn.

    **Voorbeeld:** Een coach met 2 gewonnen deals van 3 totaal heeft 66% winst.
    Maar dit zegt weinig over hun echte prestaties.
    """)

with st.expander("Wat is het verschil tussen 'ruwe winrate' en 'winstpercentage'?"):
    st.markdown("""
    - **Ruwe winrate:** Simpelweg gewonnen ÷ totaal × 100%
    - **Winstpercentage (smoothed):** Een gecorrigeerde versie die rekening houdt
      met onzekerheid bij weinig deals

    Bij weinig deals wordt het percentage "naar het gemiddelde getrokken" om
    extreme uitschieters te voorkomen.
    """)

with st.expander("Hoe vaak wordt de data bijgewerkt?"):
    st.markdown("""
    De data in dit dashboard komt uit een Excel-bestand dat periodiek wordt
    gegenereerd. Kijk naar de datum in de footer voor de laatste update.
    """)

with st.expander("Kan ik de data exporteren?"):
    st.markdown("""
    Ja! In de tabel kun je:
    - De data kopiëren naar Excel (selecteer en Ctrl+C)
    - Sorteren door op kolomkoppen te klikken
    - Filteren via de sidebar links
    """)

# ============================================================================
# SECTION 8: SAMENVATTING
# ============================================================================

st.markdown("---")
st.markdown("## 8. Samenvatting")

st.info("""
**De belangrijkste punten:**

1. **Status bepaalt geschiktheid** - Alleen Laag 2 en Laag 3 komen in aanmerking
2. **Volume is belangrijk** - Minimaal 14 deals voor betrouwbare statistiek
3. **Mediaan verschilt per periode** - 1m: 55.6%, 3m: 54.5%, 6m: 50.0%
4. **Grafieken lezen** - Rechtsboven in de scatter = beste coaches
5. **Trends bekijken** - Vergelijk 1, 3 en 6 maanden voor patronen
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
