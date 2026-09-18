"""De sluitingskalender in Postgres: schrijven, en teruglezen.

De databasekant van `bakkerij/sluitingskalender.py`, naar het model van
`kostenmodel_db.py`: migratie 011 draagt de tabellen (`sluitingsdag`,
`sluitingsregel`), migratie 012 de schrijffunctie voor PostgREST. Deze module
is voor de Python-kant van de keten — de canoniekbouw en de contractbouw die
teruglezen, en het eenmalige laadscript (`make db-sluitingen`) dat de
bestandslijst overzet.

WAT ER NOOIT IN GAAT

Klantdata. De sluitingskalender bestaat uit datums, een toestand, en een
zakelijke reden ("Kerstmis", "Jaarlijkse sluiting"). Geen transacties, geen
klanten -- er is hier per constructie niets om te censureren. De reden komt
op het scherm en in deze tabellen; migratie 011 herhaalt de waarschuwing uit
config/sluitingsdagen.json dat er dus nooit een naam of een persoonlijke
omstandigheid in hoort.

HET SCHRIJFPATROON

Alles weg, dan alles erin, binnen één transactie -- zelfde vorm en zelfde
argument als bij het kostenmodel: een uitspraak die de beheerder intrekt
(de ?-knop), hoort ook uit de database te verdwijnen, en binnen één
transactie bestaat er geen moment waarop een lezer een halve kalender ziet.
`schrijf` commit niet: de aanroeper bepaalt de transactiegrens.

`bewaard_op` zet de database zelf (`default now()`), om dezelfde reden als
bij het kostenmodel: de klok van de database is een betere bron dan de klok
van wie schrijft.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from bakkerij.sluitingskalender import Uitspraak, Weekregel

DAGEN_SQL = (
    "select datum, toestand, reden, bron, bewaard_door, bewaard_op "
    "from public.sluitingsdag order by datum"
)

REGELS_SQL = (
    "select weekdag, vanaf, tot, reden, bewaard_door, bewaard_op "
    "from public.sluitingsregel order by weekdag, vanaf"
)

VERWIJDER_DAGEN_SQL = "delete from public.sluitingsdag"
VERWIJDER_REGELS_SQL = "delete from public.sluitingsregel"

INVOEG_DAG_SQL = (
    "insert into public.sluitingsdag (datum, toestand, reden, bron, "
    "bewaard_door) values (%s, %s, %s, %s, %s)"
)

INVOEG_REGEL_SQL = (
    "insert into public.sluitingsregel (weekdag, vanaf, tot, reden, "
    "bewaard_door) values (%s, %s, %s, %s, %s)"
)


@dataclass(frozen=True)
class Sluitingskalender:
    """De volledige stand uit de database, plus wie hem het laatst bewaarde.

    `bewaard_door` en `bewaard_op` komen uit de jongste rij: één opslag
    schrijft alles (migratie 012, alles weg dan alles erin), dus de jongste
    rij spreekt voor het geheel — dezelfde redenering als `_door_van` in
    kostenmodel_db.py.
    """

    uitspraken: tuple[Uitspraak, ...]
    regels: tuple[Weekregel, ...]
    bewaard_door: str
    bewaard_op: str


def _als_datum(waarde) -> dt.date:
    """psycopg levert `date`, maar een test met een string mag niet stil een
    verkeerd type doorgeven."""
    if isinstance(waarde, dt.date):
        return waarde
    return dt.date.fromisoformat(str(waarde))


def kalender_uit_rijen(dag_rijen, regel_rijen) -> Sluitingskalender | None:
    """Databaserijen naar een getoetste `Sluitingskalender`.

    None wanneer er nog niets bewaard is -- de normale beginstand, geen fout.
    De validatie loopt door de dataclasses van `sluitingskalender.py`: een
    rij die daar niet doorheen komt (onbekende toestand, te lange reden),
    komt eruit als een ValueError met de reden in gewone taal.
    """
    dagen = list(dag_rijen)
    regels = list(regel_rijen)
    if not dagen and not regels:
        return None

    uitspraken = tuple(
        Uitspraak(datum=_als_datum(datum), toestand=str(toestand),
                  reden=str(reden or ""), bron=str(bron))
        for datum, toestand, reden, bron, _door, _op in dagen
    )
    weekregels = tuple(
        Weekregel(weekdag=int(weekdag), vanaf=_als_datum(vanaf),
                  tot=None if tot is None else _als_datum(tot),
                  reden=str(reden or ""))
        for weekdag, vanaf, tot, reden, _door, _op in regels
    )

    momenten = [op for *_rest, op in dagen + regels if op is not None]
    jongste = max(momenten, default=None)
    door = ""
    for *_rest, kandidaat, op in dagen + regels:
        if op == jongste and kandidaat:
            door = str(kandidaat)
            break

    return Sluitingskalender(
        uitspraken=uitspraken,
        regels=weekregels,
        bewaard_door=door,
        bewaard_op=(jongste.isoformat() if hasattr(jongste, "isoformat")
                    else str(jongste or "")),
    )


def haal_rijen(verbinding) -> tuple[list, list]:
    """De ruwe rijen uit beide tabellen, in vaste volgorde, in één rondgang."""
    with verbinding.cursor() as cur:
        cur.execute(DAGEN_SQL)
        dagen = cur.fetchall()
        cur.execute(REGELS_SQL)
        regels = cur.fetchall()
    return dagen, regels


def lees(verbinding) -> Sluitingskalender | None:
    """De sluitingskalender uit de database, of None als er niets bewaard is."""
    return kalender_uit_rijen(*haal_rijen(verbinding))


def schrijf(verbinding, uitspraken: tuple[Uitspraak, ...],
            regels: tuple[Weekregel, ...], door: str) -> int:
    """Bewaar de volledige sluitingskalender. Alles of niets.

    Geeft het aantal weggeschreven rijen terug. Commit doet de aanroeper.
    Dubbele datums worden hier geweigerd vóór het eerste delete, zodat een
    invoer die het niet haalt de bestaande kalender niet eerst wist.
    """
    if not door or not door.strip():
        raise ValueError(
            "schrijf() zonder 'door': elke wijziging aan de sluitingskalender "
            "draagt de naam van wie hem deed (kolom bewaard_door in "
            "migratie 011)."
        )
    datums = [u.datum for u in uitspraken]
    if len(datums) != len(set(datums)):
        raise ValueError(
            "Dezelfde datum staat er meer dan één keer in; één uitspraak "
            "per dag."
        )
    naam = door.strip()

    with verbinding.cursor() as cur:
        cur.execute(VERWIJDER_DAGEN_SQL)
        cur.execute(VERWIJDER_REGELS_SQL)
        if uitspraken:
            cur.executemany(INVOEG_DAG_SQL, [
                (u.datum, u.toestand, u.reden, u.bron, naam)
                for u in uitspraken
            ])
        if regels:
            cur.executemany(INVOEG_REGEL_SQL, [
                (r.weekdag, r.vanaf, r.tot, r.reden, naam)
                for r in regels
            ])
    return len(uitspraken) + len(regels)
