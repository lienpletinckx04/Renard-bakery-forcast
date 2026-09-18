"""Het kostenmodel in Postgres: schrijven, en teruglezen.

De invoer van de beheerder leefde tot 18 augustus 2026 alleen als bestand
(`data/config/kostenmodel.json`, buiten git). Dat werkt op de machine van de
bouwer en nergens anders, en dat was een echt probleem, niet een netheidskwestie:

  * de nachtelijke sync draait op een GitHub-runner die `data/config/` niet
    heeft, en bouwde daar dus een contract zonder kostenmodel -- een groene run
    met minder cijfers erin (zie `contract_rijen.ontbrekende_sleutels`, dat er
    een wacht voor bouwde);
  * de gehoste omgeving kon de invoer niet eens aanmaken: het formulier op
    Instellingen weigerde onder `CONTRACT_BRON=db`, want een bestand schrijven
    dat niemand leest is erger dan eerlijk weigeren.

Deze module is de databasekant van diezelfde invoer: migratie 005 draagt de
tabellen, migratie 009 de schrijffunctie voor PostgREST. Er komt geen tweede
vorm bij -- de vertaling loopt door `kostenmodel.parse_kostenmodel`, zodat een
model uit de database exact dezelfde controles doorstaat als een model uit een
bestand. Eén bron van waarheid, één validatie.

WAT ER NOOIT IN GAAT

Klantdata. Het kostenmodel bestaat uit criterianamen (door de beheerder
gekozen), productgroepnamen (uit het assortiment) en percentages. Geen
transacties, geen klanten, geen bonnen -- er is hier per constructie niets om
te censureren, en dat blijft zo zolang deze module alleen `Kostenmodel` schrijft
en niets uit `verkopen` aanraakt.

HET SCHRIJFPATROON

Alles weg, dan alles erin, binnen één transactie. Anders dan de feitentabellen
(die `insert ... on conflict` gebruiken, zie `laden.py`) is dat hier de juiste
vorm, om dezelfde reden als bij `contract_antwoord`: een criterium dat de
beheerder schrapt, hoort ook uit de database te verdwijnen. Binnen één
transactie bestaat er geen moment waarop een lezer een halve invoer ziet, en
faalt er iets, dan staat het oude model er nog.

`schrijf` commit niet: de aanroeper bepaalt de transactiegrens, precies zoals
`laden.schrijf`.

`bewaard_op` wordt niet meegestuurd maar door de database gezet (`default
now()`). Dat is met opzet: het veld zegt wanneer de invoer bewaard is, en de
klok van de database is daarvoor een betere bron dan de klok van wie schrijft.
"""

from __future__ import annotations

import json
from decimal import Decimal

from bakkerij import kostenmodel as km

#: De criteria in hun eigen volgorde -- die volgorde is de kolomvolgorde op het
#: scherm, dus ze hoort bewaard te blijven. Op naam erachteraan zodat twee
#: criteria met hetzelfde volgordenummer (handmatig ingrijpen) toch een vaste
#: uitkomst geven; een lezing die per run verschilt, is niet reproduceerbaar.
CRITERIA_SQL = (
    "select naam, omschrijving, bewaard_door, bewaard_op "
    "from public.kosten_criterium order by volgorde, naam"
)

WAARDEN_SQL = (
    "select groep, criterium, pct from public.kosten_waarde "
    "order by groep, criterium"
)

VERWIJDER_WAARDEN_SQL = "delete from public.kosten_waarde"
VERWIJDER_CRITERIA_SQL = "delete from public.kosten_criterium"

INVOEG_CRITERIUM_SQL = (
    "insert into public.kosten_criterium "
    "(naam, omschrijving, volgorde, bewaard_door) values (%s, %s, %s, %s)"
)

INVOEG_WAARDE_SQL = (
    "insert into public.kosten_waarde (groep, criterium, pct, bewaard_door) "
    "values (%s, %s, %s, %s)"
)


def criteriumrijen(
    model: km.Kostenmodel, door: str
) -> list[tuple[str, str, int, str]]:
    """De criteria als databaserijen: (naam, omschrijving, volgorde, door).

    De volgorde begint bij 1, zoals `with ordinality` in migratie 009 -- de twee
    schrijvers moeten dezelfde nummering geven, anders staan de kolommen op het
    scherm anders na een handmatige laadrun dan na een formulieropslag.
    """
    return [
        (c.naam, c.omschrijving, nummer, door)
        for nummer, c in enumerate(model.criteria, start=1)
    ]


def waarderijen(
    model: km.Kostenmodel, door: str
) -> list[tuple[str, str, Decimal, str]]:
    """De kosten als databaserijen: (groep, criterium, pct, door).

    Percentages blijven `Decimal`, nooit float: de kolom is `numeric(5, 2)` en
    een kost van 30,5% die als float rondreist, is op het scherm een keer
    30,499... (harde regel over geld, en migratie 005 zegt hetzelfde).

    De volgorde is groep, dan de criteriumvolgorde van het model zelf -- niet
    de willekeurige volgorde van een dict-iteratie.
    """
    rangen = {c.naam: i for i, c in enumerate(model.criteria)}
    rijen: list[tuple[str, str, Decimal, str]] = []
    for groep in sorted(model.waarden):
        per_criterium = model.waarden[groep]
        for criterium in sorted(per_criterium, key=lambda n: (rangen.get(n, 999), n)):
            rijen.append((groep, criterium, per_criterium[criterium], door))
    return rijen


def model_uit_rijen(criteria_rijen, waarde_rijen) -> km.Kostenmodel | None:
    """Databaserijen terug naar een getoetst `Kostenmodel`.

    None wanneer er nog niets bewaard is -- de normale beginstand, geen fout,
    net als een ontbrekend `kostenmodel.json`.

    De validatie loopt door `kostenmodel.parse_kostenmodel` en niet langs een
    eigen reeks controles. Dat is de hele reden dat deze functie via de
    bestandsvorm gaat: een model uit de database dat de bestandsroute niet zou
    overleven, mag ook hier niet doorglippen. Zit er onzin in de tabellen, dan
    komt dat eruit als een ValueError met de reden in gewone taal -- in de
    ingestelde taal, want de parser gebruikt `t()`.
    """
    criteria = list(criteria_rijen)
    waarden = list(waarde_rijen)
    if not criteria and not waarden:
        return None

    boom: dict = {
        "versie": 2,
        "criteria": [
            {"naam": naam, "omschrijving": omschrijving or ""}
            for naam, omschrijving, _door, _op in criteria
        ],
        "waarden": {},
        "ingevuld_door": _door_van(criteria),
        "ingevuld_op": _op_van(criteria),
    }
    for groep, criterium, pct in waarden:
        # str() en niet float(): de parser eist een string met punt-decimaal, en
        # dat is precies de vorm waarin een numeric uit psycopg als Decimal
        # aankomt. Een tussenstap via float zou de precisie weggooien die de
        # kolom juist bewaart.
        boom["waarden"].setdefault(groep, {})[criterium] = str(pct)

    return km.parse_kostenmodel(json.dumps(boom))


def _door_van(criteria: list) -> str:
    """Wie het bewaard heeft. Alle rijen dragen dezelfde naam (één schrijver per
    opslag), dus de eerste is de waarheid; leeg blijft leeg."""
    for _naam, _omschrijving, door, _op in criteria:
        if door:
            return str(door)
    return ""


def _op_van(criteria: list) -> str:
    """Wanneer, als ISO 8601 -- dezelfde vorm die het formulier in het bestand
    schreef, zodat het contract er niets van hoeft te weten."""
    momenten = [op for *_rest, op in criteria if op is not None]
    if not momenten:
        return ""
    jongste = max(momenten)
    return jongste.isoformat() if hasattr(jongste, "isoformat") else str(jongste)


def haal_rijen(verbinding) -> tuple[list, list]:
    """De ruwe rijen uit beide tabellen, in vaste volgorde.

    Apart van `lees` omdat de contractbouw ze één keer ophaalt en daarna per
    taal een model bouwt: de foutmeldingen van de parser en de naam van het
    v1-criterium volgen `t()`, en die staat pas vast binnen de taalcontext.
    Twee keer dezelfde query naar de database sturen om dat te bereiken, zou
    twee rondgangen kosten voor dezelfde rijen.
    """
    with verbinding.cursor() as cur:
        cur.execute(CRITERIA_SQL)
        criteria = cur.fetchall()
        cur.execute(WAARDEN_SQL)
        waarden = cur.fetchall()
    return criteria, waarden


def lees(verbinding) -> km.Kostenmodel | None:
    """Het kostenmodel uit de database, of None als er niets bewaard is."""
    return model_uit_rijen(*haal_rijen(verbinding))


def schrijf(verbinding, model: km.Kostenmodel, door: str) -> int:
    """Bewaar het volledige kostenmodel. Alles of niets.

    Geeft het aantal weggeschreven kostenrijen terug. Commit doet de aanroeper.

    `door` is niet vrijblijvend: `bewaard_door` is `not null` in migratie 005
    omdat elke wijziging aan de cijferbasis de naam draagt van wie hem deed.
    """
    if not door or not door.strip():
        raise ValueError(
            "schrijf() zonder 'door': elke wijziging aan het kostenmodel draagt "
            "de naam van wie hem deed (kolom bewaard_door in migratie 005)."
        )
    # Toetsen vóór het eerste delete. Een model dat de parser niet overleeft,
    # mag de bestaande invoer niet eerst wissen -- dan is de oude er niet meer
    # en de nieuwe er nooit geweest.
    getoetst = km.toets(model)
    naam = door.strip()

    criteria = criteriumrijen(getoetst, naam)
    waarden = waarderijen(getoetst, naam)

    with verbinding.cursor() as cur:
        cur.execute(VERWIJDER_WAARDEN_SQL)
        cur.execute(VERWIJDER_CRITERIA_SQL)
        if criteria:
            cur.executemany(INVOEG_CRITERIUM_SQL, criteria)
        if waarden:
            cur.executemany(INVOEG_WAARDE_SQL, waarden)
    return len(waarden)
