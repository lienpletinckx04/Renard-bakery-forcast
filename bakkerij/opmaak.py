"""Belgische getalopmaak voor tekstuitvoer van scripts.

Dit zijn *lexicale* omzettingen: ze verplaatsen scheidingstekens in een string
die al klaar is, en rekenen niets. Een bedrag dat als "1234.56" uit het contract
komt, wordt "€ 1.234,56" — geen afronding, geen float, geen herberekening
(harde regel 4 geldt ook voor een script dat een tabel afdrukt).

WAAROM DEZE MODULE BESTAAT. Deze drie functies stonden tot 18 augustus 2026 in
`bakkerij/report/pdf.py`, de WeasyPrint-bouwer van het CFO-rapport. Die bouwer
is die dag opgeheven: het rapport is een weergave in het platform geworden
(`platform/app/rapport/page.tsx`), en de opmaak van cijfers op een scherm hoort
in `platform/lib/format.ts`. Wat overbleef, is dat `scripts/tgtg_restwaarde.py`
deze omzetting nog nodig heeft voor zijn markdown-tabel. Die functie hoort dan
in een module over opmaak, niet in een module over een rapport dat niet meer
bestaat.

DE TEGENHANGER. `platform/lib/format.ts` doet hetzelfde voor de schermen, en de
tests hier en daar leggen dezelfde uitkomsten vast ("€ 1.234,56", "12,3 %").
Twee talen, één afspraak; wie de ene verandert, verandert de andere mee.

NIET HIERHEEN GEHAALD. `bakkerij/contract.py` en `bakkerij/kwaliteit.py` hebben
elk een eigen `_pct_nl`, maar die nemen een fractie (0.084 -> "8,4 %") en doen
dus wél een bewerking. Ze samenvoegen met deze zou één functie met twee
betekenissen opleveren; dat is een opruiming voor een eigen ronde.
"""

from __future__ import annotations

# De echte minus (U+2212), niet het koppelteken: die staat op dezelfde hoogte
# als het plusteken en breekt niet af aan het eind van een regel.
MINUS = "−"


def euro_nl(waarde: str) -> str:
    """ "1234.56" -> "€ 1.234,56". Puur lexicaal, geen bewerking op de waarde."""
    negatief = waarde.startswith("-")
    kaal = waarde[1:] if negatief else waarde
    heel, _, dec = kaal.partition(".")
    groepen = ""
    for i, cijfer in enumerate(reversed(heel)):
        if i and i % 3 == 0:
            groepen = "." + groepen
        groepen = cijfer + groepen
    romp = f"{groepen},{dec}" if dec else groepen
    return f"€ {MINUS if negatief else ''}{romp}"


def pct_nl(waarde: str) -> str:
    """ "12.3" -> "12,3 %" ; "-4.2" -> "−4,2 %"."""
    tekst = waarde.replace("-", MINUS).replace(".", ",")
    return f"{tekst} %"


def aantal_nl(waarde: str) -> str:
    """ "24960" -> "24.960". Dezelfde groepering als een bedrag, zonder teken."""
    return euro_nl(waarde).removeprefix("€ ")
