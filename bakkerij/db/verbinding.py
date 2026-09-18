"""De verbinding met Postgres, en de drie valkuilen die haar stilletjes slopen.

`docs/stack.md` beschrijft onder "De ETL naar de database" drie eisen aan de
verbindingsstring. Ze staan daar als proza, en proza wordt niet uitgevoerd.
Deze module maakt ze toetsbaar: `controleer_dsn` is een pure functie met
tests, en `verbind` weigert te starten op een string die niet deugt.

Waarom dat de moeite waard is: alle drie de fouten geven een foutmelding die
naar iets ANDERS wijst dan de oorzaak.

  * `db.<ref>.supabase.co` is IPv6-only. GitHub Actions-runners hebben
    onbetrouwbare IPv6-uitgang. Symptoom: `network is unreachable`, midden in
    de nacht, in een run die niemand zit te bekijken. Je gaat firewalls en
    Supabase-status controleren, niet je hostnaam.
  * Poort 6543 is transaction mode. Die kent geen prepared statements. Met
    psycopg3 en met COPY loopt dat mis op een manier die op een SQL-fout
    lijkt, niet op een poortkeuze.
  * Gebruiker `postgres` in plaats van `postgres.<project-ref>` geeft een
    authenticatiefout, en dan ga je het wachtwoord opnieuw zetten.

Geen van de drie is te vinden door harder te kijken naar de foutmelding.
Daarom worden ze hier bij naam genoemd, vóór de eerste verbinding.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

# Hoe lang één statement mag duren voor Postgres hem afkapt. De ETL doet COPY
# van tienduizenden rijen; dat is ruim binnen een minuut. Staat er geen
# timeout, dan kan een hangend statement een verbinding uit de pooler
# vasthouden tot iemand het merkt.
STATEMENT_TIMEOUT_MS = 120_000

# Hoe lang het opzetten van de verbinding zelf mag duren. Zonder deze grens
# geldt de TCP-timeout van het besturingssysteem -- ruim twee minuten -- en
# faalt een onbereikbare pooler traag en met een generieke melding.
CONNECT_TIMEOUT_S = 10

_IPV6_ONLY_HOST = ".supabase.co"
_POOLER_HOST = ".pooler.supabase.com"
_TRANSACTION_MODE_POORT = 6543
_SESSION_MODE_POORT = 5432


def controleer_dsn(dsn: str) -> list[str]:
    """Toets een verbindingsstring op de drie valkuilen uit stack.md.

    Geeft een lijst bezwaren terug, elk als één leesbare zin. Lege lijst
    betekent: hier is niets aan op te merken.

    Deze functie raakt het netwerk niet aan en leest geen wachtwoord. Ze
    kijkt alleen naar de vorm, zodat ze in een test kan draaien zonder
    database en zonder geheim.
    """
    bezwaren: list[str] = []

    if not dsn or not dsn.strip():
        return ["De verbindingsstring is leeg. Vul SUPABASE_DB_URL in .env in."]

    # De plaatshouder uit het Supabase-dashboard. Die blokhaken laten urlparse
    # denken dat het netloc een IPv6-adres draagt, en dan werpt hij met een
    # ValueError over 'does not appear to be an IPv4 or IPv6 address' -- een
    # melding die naar het verkeerde probleem wijst. Vang hem bij naam.
    if "[YOUR-PASSWORD]" in dsn or "[wachtwoord]" in dsn.lower():
        return [
            (
                "De plaatshouder [YOUR-PASSWORD] staat er nog in. Vervang hem, "
                "inclusief de blokhaken, door het databasewachtwoord."
            )
        ]

    try:
        ontleed = urlparse(dsn)
    except ValueError:
        # Elke andere onontleedbare vorm. De string zelf komt hier NIET in de
        # melding: daar staat het wachtwoord in.
        return [
            (
                "De verbindingsstring is niet te ontleden als URL. Kopieer hem "
                "opnieuw uit Supabase (Connect -> Session pooler) en let op "
                "afbreekstreepjes of spaties die er bij het plakken in slopen."
            )
        ]

    if ontleed.scheme not in ("postgresql", "postgres"):
        bezwaren.append(
            f"Schema is '{ontleed.scheme}' maar hoort 'postgresql' te zijn."
        )

    host = ontleed.hostname or ""
    if host.startswith("db.") and host.endswith(_IPV6_ONLY_HOST):
        bezwaren.append(
            f"De hostnaam '{host}' is IPv6-only. GitHub Actions-runners hebben "
            "onbetrouwbare IPv6-uitgang en falen daarop met 'network is "
            "unreachable'. Gebruik de pooler-hostname "
            "(aws-<n>-<regio>.pooler.supabase.com), die is altijd IPv4."
        )

    poort = ontleed.port
    if poort == _TRANSACTION_MODE_POORT:
        bezwaren.append(
            f"Poort {_TRANSACTION_MODE_POORT} is transaction mode. Die kent geen "
            "prepared statements, wat botst met psycopg3 en met COPY. Gebruik "
            f"poort {_SESSION_MODE_POORT} (session mode)."
        )
    elif poort is None:
        bezwaren.append(
            f"Er staat geen poort in de verbindingsstring. Zet hem expliciet op "
            f"{_SESSION_MODE_POORT} (session mode)."
        )

    gebruiker = ontleed.username or ""
    if host.endswith(_POOLER_HOST) and "." not in gebruiker:
        bezwaren.append(
            f"De gebruiker is '{gebruiker}', maar de pooler verwacht "
            "'postgres.<project-ref>'. Zonder de projectverwijzing weet de "
            "pooler niet naar welk project hij moet routeren."
        )

    vraag = parse_qs(ontleed.query)
    if vraag.get("sslmode", [""])[0] not in ("require", "verify-ca", "verify-full"):
        bezwaren.append(
            "sslmode staat niet op 'require'. Voeg '?sslmode=require' toe: de "
            "omzet van de klant hoort niet onversleuteld over het internet."
        )

    return bezwaren


def normaliseer_dsn(dsn: str) -> str:
    """Repareer de twee dingen die bij plakken standaard misgaan.

    Dit is geen soepelheid maar een gemeten wrijvingspunt: de knop "Copy" in
    het Supabase-dashboard levert de pooler-URI *zonder* `sslmode`, en een
    secret-veld of een teksteditor plakt er graag een regeleinde achter. Beide
    gaven een afwijzing die de beheerder zelf moest oplossen, midden in een
    opzet waarin niets anders mis was. De eis zelf blijft onverkort staan --
    `controleer_dsn` toetst nog steeds op `sslmode=require` -- alleen vult
    deze functie hem aan in plaats van de beheerder ernaar te laten raden.

    Wat hier NIET gebeurt: een ontbrekende poort of een verkeerde host
    bijschrijven. Die twee dragen een keuze (session- versus transaction mode,
    IPv4 versus IPv6) en die keuze hoort zichtbaar te zijn, niet geraden.
    """
    dsn = dsn.strip()
    if not dsn:
        return dsn

    try:
        ontleed = urlparse(dsn)
    except ValueError:
        return dsn  # onontleedbaar: controleer_dsn zegt dat zo dadelijk netjes

    if "sslmode" in parse_qs(ontleed.query):
        return dsn
    return dsn + ("&" if ontleed.query else "?") + "sslmode=require"


def dsn_uit_omgeving(variabele: str = "SUPABASE_DB_URL") -> str:
    """Haal de verbindingsstring uit de omgeving en toets hem.

    Werpt met een leesbare uitleg als er iets niet klopt. De string zelf komt
    NOOIT in de foutmelding terecht -- daar staat het wachtwoord in.
    """
    dsn = normaliseer_dsn(os.environ.get(variabele, ""))
    bezwaren = controleer_dsn(dsn)
    if bezwaren:
        regels = "\n".join(f"  - {b}" for b in bezwaren)
        raise ValueError(
            f"{variabele} deugt niet:\n{regels}\n"
            f"\nDe verwachte vorm staat in .env.example en in docs/stack.md."
        )
    return dsn


@contextmanager
def verbind(dsn: str | None = None, *, timeout_ms: int = STATEMENT_TIMEOUT_MS):
    """Open een verbinding met een expliciete statement-timeout.

    Gebruik dit kort. De pooler knipt inactieve verbindingen, dus doe het
    pdf-parsen en het rekenwerk vóór je hier binnenkomt, niet terwijl de
    verbinding openstaat (stack.md).
    """
    import psycopg  # lokaal: wie alleen controleer_dsn gebruikt, hoeft hem niet

    if dsn is None:
        dsn = dsn_uit_omgeving()

    with psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S) as verbinding:
        with verbinding.cursor() as cur:
            cur.execute(f"set statement_timeout = {int(timeout_ms)}")
        yield verbinding
