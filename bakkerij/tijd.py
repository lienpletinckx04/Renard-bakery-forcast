"""Eén plek voor de projecttijdzone en de conversie van Odoo-momenten.

Odoo slaat momenten op in UTC en geeft ze via de API terug als ISO-string
zónder zone-aanduiding. De dag van een verkoop is de Belgische dag
(CLAUDE.md: tijdzone Europe/Brussels), dus elke dagsleutel hoort via een
expliciete conversie te lopen: eerst UTC aanplakken, dan naar Brussel, dan
pas de datum nemen.

Waarom dit een module is en geen conventie: zeven bestanden definieerden elk
hun eigen ZoneInfo("Europe/Brussels"), en de ene plek die de conversie
oversloeg -- dagsleutel() in scripts/odoo_extract.py, gevonden bij de
inspectieronde van 18 augustus 2026 -- legde de kernfeitentabel op de
UTC-dag terwijl de bonnen- en urenextracten op de Brusselse dag lagen. In de
zomer (UTC+2) verschoof elke verkoop na 22u00 UTC daardoor stil naar de
verkeerde dag, en vergeleek de kwaliteitslaag twee kalenders met elkaar.
Een conversie die maar op één plek bestaat, kan niet meer op één plek
vergeten worden.

Sinds 18 augustus 2026 halen ook bakkerij/contract.py en
bakkerij/sources/agenda.py hun zone hier, en sinds 19 augustus scripts/ en
tests/ ook: de regel hieronder is de enige ZoneInfo("Europe/Brussels") in de
repo. (Deze alinea somde tot 19 augustus vijf scripts op die nog een eigen zone
zouden hebben, met de mededeling dat die opruiming apart liep. Ze was allang
gedaan. In een codebase waar de docstring de documentatie is, stuurt zo'n zin
de volgende lezer op werk af dat niet meer bestaat -- en dat is geen
schoonheidsfoutje maar een verkeerd feit.)
"""
import datetime as dt
from zoneinfo import ZoneInfo

BRUSSEL = ZoneInfo("Europe/Brussels")
UTC = ZoneInfo("UTC")


def brussels_moment(waarde) -> dt.datetime:
    """'2024-09-19 21:14:03' (UTC, zoals Odoo levert) -> Brussels moment.

    Een waarde die al een zone draagt wordt gerespecteerd; een naïeve waarde
    is per Odoo-contract UTC.
    """
    s = str(waarde)
    try:
        ruw = dt.datetime.fromisoformat(s)
    except ValueError:
        # Een staart die fromisoformat niet kent: dan alleen de
        # datum-plus-seconden lezen.
        ruw = dt.datetime.fromisoformat(s[:19])
    if ruw.tzinfo is None:
        ruw = ruw.replace(tzinfo=UTC)
    return ruw.astimezone(BRUSSEL)


def brusselse_dag(waarde) -> dt.date:
    """De Belgische kalenderdag waarop een Odoo-moment valt."""
    return brussels_moment(waarde).date()
