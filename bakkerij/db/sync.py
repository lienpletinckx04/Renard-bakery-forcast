"""De beslislogica van de nachtelijke sync.

De sync zelf is een ketting van bestaande stappen (extract -> canoniek ->
db-laad) en die ketting staat in `scripts/nachtelijke_sync.py`. Wat hier
staat is het deel dat een test verdient: de beslissing of er vannacht
überhaupt iets te doen valt.

WAAROM EEN POORTWACHTER OP `write_date` EN GEEN GEDEELTELIJK EXTRACT. De
oorspronkelijke gedachte (todo, blok 8) was incrementeel extraheren op
`write_date`. Maar het extract aggregeert sinds 12 augustus aan de bron tot
dag x product x kassa, en een dag die je maar half opnieuw ophaalt en dan
upsert, overschrijft het volledige dagtotaal met een gedeeltelijk -- stille
corruptie, precies het soort fout dat pas op het scherm zichtbaar wordt.
Het volledige extract is sinds de herschrijving constant per bladzijde en
past ruim in een nachtelijke job. `write_date` is dus de poortwachter
geworden: is er sinds de laatste geslaagde run niets gewijzigd in Odoo, dan
stopt de job meteen en schrijft hij alleen een logregel. Tijdens een
zomersluiting doet de sync zo elke nacht bijna niets, en dat is juist.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

#: Hoeveel speling de poortwachter neemt op de vergelijking. Odoo-servertijd
#: en runnertijd lopen nooit exact gelijk, en een order die tijdens de vorige
#: run binnenkwam mag niet tussen wal en schip vallen. Ruim genomen: een uur.
MARGE = dt.timedelta(hours=1)


@dataclass(frozen=True)
class Syncbesluit:
    draaien: bool
    reden: str


def beslis_sync(
    jongste_wijziging: dt.datetime | None,
    laatste_geslaagde_run: dt.datetime | None,
    *,
    marge: dt.timedelta = MARGE,
) -> Syncbesluit:
    """Moet de volledige ketting draaien?

    `jongste_wijziging` is de jongste `write_date` in Odoo (pos.order),
    `laatste_geslaagde_run` de starttijd van de jongste geslaagde run uit
    `etl_run`. Beide mogen None zijn en beide horen tijdzonebewust te zijn --
    een naïeve datetime naast een bewuste is een vergelijking die Python
    terecht weigert, en dat gebeurt hier dan ook hardop.
    """
    if laatste_geslaagde_run is None:
        return Syncbesluit(True, "geen eerdere geslaagde run bekend; volledige run")
    if jongste_wijziging is None:
        # Geen enkele order in Odoo is geen reden om te draaien, maar wel om
        # het te melden: een lege bron is doorgaans een kapotte toegang.
        return Syncbesluit(False, "Odoo meldt geen enkele orderwijziging; "
                                  "niets te laden, wel iets om na te kijken")
    if jongste_wijziging >= laatste_geslaagde_run - marge:
        return Syncbesluit(True, f"wijzigingen in Odoo tot "
                                 f"{jongste_wijziging.isoformat()}; run")
    return Syncbesluit(False, f"geen wijzigingen sinds de vorige run "
                              f"({laatste_geslaagde_run.isoformat()}); overslaan")
