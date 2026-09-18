"""Leest de Deliveroo-rapporten uit Partner Hub en zet ze om naar tabellen.

DE PARSER ZELF IS NOG NIET GEBOUWD, EN DAT IS EEN BESLISSING (zie
`beslissingen.md`, 25 aug 2026). Wat hier staat is het skelet: de foutklasse,
de vorm van de twee rapporten, en de twee controles die geen kennis van de
documentvorm vergen. Het lezen zelf wacht op echte CSV's, want de ervaring met
een eerdere kanaalparser is dat de vorm van echte documenten verrast — drie
datumnotaties, drie namen voor dezelfde artikelregel, en een euroteken dat
vóór, achter of nergens staat. Een parser op een bedachte CSV is schijnwerk
dat je twee keer betaalt.

Deliveroo heeft geen bruikbare API voor dit doel: de Order API geeft niets
ouder dan dertig dagen en de webhook draagt geen commissie en geen
netto-uitbetaling. Wat wél bestaat is Partner Hub -> Reports, en daar kan de
zaakvoerder zelf bij. Twee rapporten, en ze vullen elkaar aan:

    Items Sold   per artikel: categorie, artikel, aantal, prijs, subtotaal.
                 GEEN commissie.
    Orders       per bestelling, met `Deliveroo commission` en
                 `VAT on Deliveroo commission`. GEEN artikelregels.

Daar zit het eigenlijke werk van deze module: Deliveroo rekent per bestelling,
terwijl de omzet per artikel staat. Netto-omzet per product-dag vergt dus een
toewijzing van de ordercommissie over de artikelregels van diezelfde order.
Twee routes, en welke het wordt hangt af van één ding dat we nog niet weten:
of de twee rapporten een gemeenschappelijke order-sleutel dragen.

    met order-sleutel : join, en de commissie pro rata over de artikelregels
                        naar subtotaal. Zuiver, en dan is de marge per product
                        verdedigbaar.
    zonder            : effectief dagtarief -- de dagcommissie gedeeld door de
                        dagbruto -- pro rata toegepast. Op dagniveau exact
                        goed, per product een benadering.

Welke van de twee gebruikt is, hoort in de uitvoer te staan en niet in het
hoofd van wie het gebouwd heeft. Een stille keuze tussen deze twee is precies
het soort verschil dat niemand naast elkaar legt tot het te laat is.

Alles hier is een pure functie. Het inlezen van de bestanden staat in
`scripts/deliveroo_extract.py`, zodat dit met vaste teksten te testen is en er
geen klantbestand in de tests hoeft te staan.

DE MAPPENCONVENTIE. Partner Hub levert per download een bereik van maximaal
negentig dagen, en de bestandsnaam die het portaal meegeeft is niet vast.
Daarom draagt de MAP het bereik, en niet de bestandsnaam:

    data/raw/Deliveroo/2025-08-25_2025-11-22/items-sold.csv
    data/raw/Deliveroo/2025-08-25_2025-11-22/orders.csv

Dat bereik is geen administratie maar een controle: het is het enige dat
dag/maand-omwisseling kan betrappen (zie `klopt_met_bereik`). Een download
zonder zo'n map wordt niet gelezen.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

#: De map met de rapporten, onder data/raw. Eén submap per download.
BRONMAP = "Deliveroo"

#: `2025-08-25_2025-11-22` -- het bereik van één Partner Hub-download.
_BEREIK = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})")

#: Wat de extractie meldt zolang de parser niet gebouwd is. Eén tekst, zodat
#: het script en deze module niet uiteen kunnen lopen.
NOG_NIET_GEBOUWD = (
    "De Deliveroo-parser is nog niet gebouwd. Dat wacht bewust op echte "
    "CSV's uit Partner Hub -> Reports (Items Sold en Orders); zie de "
    "moduletekst van bakkerij/sources/deliveroo_parse.py en de vervolglijst "
    "in docs/plan-deliveroo-parser.md."
)


class DeliverooFormaatFout(ValueError):
    """De CSV ziet er anders uit dan verwacht.

    Met opzet een fout en geen stille nul: een leverancier wijzigt ergens
    onderweg de vorm van zijn export, en een parser die dat niet merkt levert
    een leeg kwartaal op dat niemand opvalt. Bij Deliveroo weegt dat extra
    zwaar, want de historiek is niet opnieuw op te halen: het venster in
    Partner Hub is twaalf maanden en schuift elke dag op.
    """


@dataclass(frozen=True)
class Artikelregel:
    """Eén regel uit Items Sold: wat er verkocht is, zonder commissie."""

    datum: datetime.date
    store_id: str
    artikel_naam: str
    categorie: str
    aantal: int
    subtotaal: Decimal
    order_id: str | None = None
    """De sleutel naar Orders, áls het rapport hem draagt. Zie de moduletekst:
    hij bepaalt of de commissie per artikel of per dag toegewezen wordt."""


@dataclass(frozen=True)
class Orderregel:
    """Eén regel uit Orders: de bestelling met wat Deliveroo inhield."""

    datum: datetime.date
    store_id: str
    order_id: str
    subtotaal: Decimal
    commissie: Decimal
    btw_op_commissie: Decimal | None = None


def parse_items_sold(tekst: str) -> list[Artikelregel]:
    """Haalt de artikelregels uit een Items Sold-export.

    Nog niet gebouwd -- zie `NOG_NIET_GEBOUWD`. Wat hier moet komen, en wat
    pas met een echte export te schrijven is: de kopregelcontrole (welke
    kolommen heten hoe), de datumnotatie (Partner Hub is Engelstalig, dus
    `05/03` kan 5 maart of 3 mei zijn), en of het rapport binnen één bereik
    per dag uitsplitst of over de periode optelt. Die laatste vraag beslist
    of vier downloads volstaan of dat het per kalenderdag moet.
    """
    raise NotImplementedError(NOG_NIET_GEBOUWD)


#: De kopregel van het Orders-rapport, zoals Partner Hub hem levert wanneer het
#: portaal op Nederlands staat. Gemeten op 23 downloads, september 2025 t/m
#: september 2026. De taal van de kop hangt aan de portaalinstelling en niet aan
#: het rapport: komt er ooit een Franse of Engelse export binnen, dan hoort daar
#: een eigen kopregel bij en geen losse vertaalpoging per kolom.
ORDER_KOLOMMEN = {
    "restaurant": "Naam restaurant",
    "order_id": "Bestelnummer",
    "status": "Bestelstatus",
    "datum": "Datum ingediend",
    "subtotaal": "Subtotaal",
    "commissie": "Deliveroo-commissie",
    "btw": "Btw op Deliveroo-commissie",
}

#: De enige status die omzet is. De drie andere die in de historiek voorkomen
#: (`Geannuleerd`, `Afgewezen (Automatisch afgewezen)`, `Niet gerealiseerd`)
#: dragen wél een subtotaal maar nul commissie: samen 76 bestellingen en
#: EUR 1.885,25 over twaalf maanden. Wie niet op status filtert telt dat als
#: omzet én verlaagt het gemeten commissiepercentage, want de noemer groeit
#: terwijl de teller gelijk blijft. Een witte lijst en geen zwarte: een status
#: die Deliveroo er morgen bij verzint, is dan geen stille omzet.
STATUS_OMZET = "Afgerond"


def _decimaal(waarde: str, kolom: str, regel: int) -> Decimal:
    """Een bedrag uit de export naar Decimal, of een leesbare fout.

    Punt-decimaal, geen duizendtalscheiding: zo levert Partner Hub het, en
    `Decimal(str)` is hier exact waar `float` dat niet is. Een leeg veld is nul
    en geen fout -- dat komt voor bij de commissie op een geannuleerde
    bestelling -- maar tekst die geen getal is, is wél een fout.
    """
    schoon = (waarde or "").strip()
    if schoon == "":
        return Decimal(0)
    try:
        return Decimal(schoon)
    except InvalidOperation as fout:
        raise DeliverooFormaatFout(
            f"regel {regel}: kolom '{kolom}' bevat geen bedrag ({waarde!r})"
        ) from fout


def parse_orders(tekst: str) -> list[Orderregel]:
    """Haalt de bestellingen met commissie uit een Orders-export.

    Het waardevolste van de twee rapporten: de enige bron die de commissie per
    bestelling mét datum geeft, en daarmee de enige weg naar een marge per
    kanaal zonder facturen te parsen.

    DE DATUM IS `Datum ingediend` EN NIET `Bezorgdatum`. Een bestelling hoort
    bij de dag waarop ze geplaatst is, zoals een kassabon bij de dag hoort
    waarop hij geslagen is. De twee lopen alleen rond middernacht uiteen: 8 van
    de 31.139 afgeronde bestellingen in twaalf maanden. Klein verschil, maar
    het moest een keuze zijn en geen toeval.

    ER ZIT GEEN ARTIKEL IN DIT RAPPORT EN GEEN ORDERSLEUTEL IN HET ANDERE.
    `Items Sold` draagt geen bestelnummer en geen datum; het telt op over de
    hele downloadperiode. De "met order-sleutel"-route uit de moduletekst
    hierboven bestaat dus niet in wat Deliveroo levert, en wat overblijft is
    het effectieve dagtarief. Dat is geen implementatiedetail maar de reden dat
    een marge per product bij Deliveroo een benadering blijft.

    ONTDUBBELEN GEBEURT HIER NIET. Downloads overlappen, dus dezelfde
    bestelling kan twee keer gelezen worden. De sleutel daarvoor is
    (datum, store_id, order_id) en niet `order_id` alleen: het bestelnummer is
    kort en per vestiging, dus botsingen tussen winkels zijn te verwachten.
    """
    lezer = csv.DictReader(io.StringIO(tekst))
    ontbreekt = [k for k in ORDER_KOLOMMEN.values()
                 if k not in (lezer.fieldnames or [])]
    if ontbreekt:
        raise DeliverooFormaatFout(
            "Orders-export mist de kolom(men) " + ", ".join(ontbreekt)
            + f". Gelezen kopregel: {lezer.fieldnames}"
        )

    regels: list[Orderregel] = []
    for nummer, rij in enumerate(lezer, start=2):  # regel 1 is de kopregel
        if (rij.get(ORDER_KOLOMMEN["status"]) or "").strip() != STATUS_OMZET:
            continue
        ruwe_datum = (rij.get(ORDER_KOLOMMEN["datum"]) or "").strip()
        try:
            datum = datetime.date.fromisoformat(ruwe_datum)
        except ValueError as fout:
            # Geen eigen datumraadwerk: Partner Hub levert hier ISO, en een
            # afwijking daarop is een vormwijziging die iemand moet zien --
            # juist bij Deliveroo, waar de historiek niet opnieuw op te halen is.
            raise DeliverooFormaatFout(
                f"regel {nummer}: '{ORDER_KOLOMMEN['datum']}' is geen "
                f"ISO-datum ({ruwe_datum!r})"
            ) from fout

        regels.append(Orderregel(
            datum=datum,
            store_id=(rij.get(ORDER_KOLOMMEN["restaurant"]) or "").strip(),
            order_id=(rij.get(ORDER_KOLOMMEN["order_id"]) or "").strip(),
            subtotaal=_decimaal(rij.get(ORDER_KOLOMMEN["subtotaal"], ""),
                                ORDER_KOLOMMEN["subtotaal"], nummer),
            commissie=_decimaal(rij.get(ORDER_KOLOMMEN["commissie"], ""),
                                ORDER_KOLOMMEN["commissie"], nummer),
            btw_op_commissie=_decimaal(rij.get(ORDER_KOLOMMEN["btw"], ""),
                                       ORDER_KOLOMMEN["btw"], nummer),
        ))
    return regels


def bereik_uit_pad(pad) -> tuple[datetime.date, datetime.date] | None:
    """Vindt de `JJJJ-MM-DD_JJJJ-MM-DD`-map in het pad van een export.

    Geeft None als geen enkel paddeel het bereik draagt; de aanroeper beslist
    dan wat dat betekent. Een omgekeerd bereik (van na tot) is geen None maar
    een fout: dat is een typefout in een mapnaam en die moet je zien.
    """
    from pathlib import Path

    for deel in Path(pad).parts:
        m = _BEREIK.fullmatch(deel)
        if not m:
            continue
        try:
            van = datetime.date.fromisoformat(m.group(1))
            tot = datetime.date.fromisoformat(m.group(2))
        except ValueError as fout:
            raise DeliverooFormaatFout(
                f"mapnaam '{deel}' draagt geen geldige datums: {fout}"
            ) from fout
        if tot < van:
            raise DeliverooFormaatFout(
                f"mapnaam '{deel}' loopt achteruit: {van} tot {tot}"
            )
        return van, tot
    return None


def klopt_met_bereik(
    datums: list[datetime.date],
    van: datetime.date,
    tot: datetime.date,
) -> list[datetime.date]:
    """Controleert de gelezen datums tegen het bereik van de download.

    Dit vangt de enige echt gevaarlijke leesfout af: dag en maand omgewisseld.
    05/03 en 03/05 zijn allebei geldige datums en geen enkele parser ziet het
    verschil. Hier is de map het bereik van de download: negentig dagen buiten
    een bereik van negentig dagen valt harder op dan een dag buiten een maand.

    Het risico is bij Deliveroo extra groot. Partner Hub is Engelstalig, en
    een Engelstalige export schrijft `03/05` net zo makkelijk als
    mei-de-derde. Van de 365 dagen in een jaar zijn er 132 waarop de
    omwisseling een andere, even geldige datum oplevert.

    Geeft de lijst onveranderd terug zodat dit in een keten past
    (`klopt_met_bereik(parse_items_sold(t), van, tot)`), en faalt luid zodra
    er ook maar één datum buiten valt.
    """
    fout = [d for d in datums if not (van <= d <= tot)]
    if fout:
        raise DeliverooFormaatFout(
            f"{len(fout)} van {len(datums)} datums vallen buiten "
            f"{van}..{tot} (eerste: {min(fout)}). Mogelijk dag/maand "
            "omgewisseld, of de verkeerde export in de map."
        )
    return datums


def gaten_in_dekking(
    bereiken: list[tuple[datetime.date, datetime.date]],
) -> list[tuple[datetime.date, datetime.date]]:
    """De dagen die tussen de downloads ontbreken, als losse bereiken.

    Bestaat omdat de historiek in blokken van maximaal negentig dagen komt en
    er dus vier downloads nodig zijn voor twaalf maanden. Een blok dat iemand
    vergeet, is een gat dat niemand ziet: de reeks loopt door, alleen met een
    stille leegte erin. En anders dan bij elk ander gat in dit project is dit
    er een die niet meer te dichten is zodra het venster van twaalf maanden
    eroverheen geschoven is.

    Overlappende bereiken zijn geen probleem en leveren geen gat; de
    ontdubbeling gebeurt verderop, op de order-sleutel.
    """
    if not bereiken:
        return []
    gesorteerd = sorted(bereiken)
    gaten: list[tuple[datetime.date, datetime.date]] = []
    tot_nu = gesorteerd[0][1]
    for van, tot in gesorteerd[1:]:
        if van > tot_nu + datetime.timedelta(days=1):
            gaten.append((tot_nu + datetime.timedelta(days=1),
                          van - datetime.timedelta(days=1)))
        tot_nu = max(tot_nu, tot)
    return gaten
