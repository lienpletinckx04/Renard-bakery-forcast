"""Gedeelde fixtures.

Hier woont één ding: de verbinding met een échte Postgres, voor de suite die
niet zonder kan.

WAAROM DIE ER MOET ZIJN. Tot 18 augustus 2026 was de hele databaselaag
databaseloos getest -- de kop van .github/workflows/tests.yml zei dat met
zoveel woorden, en het was een bewuste keuze. De prijs bleek die dag: geen
enkele regel SQL was ooit door Postgres geparseerd, en de eerste echte run
liep meteen op drie fouten die geen enkele bestaande test kón zien (een COPY
die lege tekst als NULL aanbood aan een `not null`-kolom, een migratie die
grants deed op een tabel die een latere migratie weer weghaalt, en een rol
zonder leesrecht op precies de tabel waaruit het platform leest).

Die fouten waren allemaal goedkoop te repareren en geen van alle te vinden
zonder server. Vandaar deze fixture.
"""
import os

import pytest


@pytest.fixture(scope="session")
def echte_db():
    """Een verbinding met de testdatabase uit TEST_DB_URL, of een skip.

    Zonder die variabele slaat de databasesuite zichzelf over, zodat
    `make test-py` op elke machine groen blijft zonder Postgres.

    De verbinding gaat OPZETTELIJK buiten `bakkerij.db.verbinding.verbind()`
    om. Die functie eist `sslmode=require` en poort 5432, en dat hoort ze te
    doen -- de omzet van de klant gaat niet onversleuteld over het internet.
    Een wegwerpdatabase op localhost heeft dat niet nodig, en de wacht
    versoepelen zou de productieregel uithollen om een test te laten draaien.
    Dus: hier rechtstreeks verbinden, en de wacht zelf ongemoeid laten (die
    heeft haar eigen tests in test_db_verbinding.py).

    De teruggave rolt ALTIJD terug, ook (juist) wanneer de test faalde. Zonder
    die regel commit psycopg3 bij het verlaten van het `with`-blok, en dan legt
    een gevallen test zijn halve toestand vast in de testdatabase: de volgende
    run meet dan die toestand in plaats van zichzelf. Gemeten op 19 aug 2026 --
    twee tests die op een assert vielen vóór hun eigen `rollback()`, lieten een
    verzonnen verkoopregel en een overschreven kanaalkostmaand achter. Een test
    die de meting van morgen verandert, is erger dan een test die faalt.

    Wie bewust wil vastleggen (zoals de alles-of-niets-test van het
    kostenmodel), commit expliciet in de test zelf en ruimt daar ook op.
    """
    dsn = os.environ.get("TEST_DB_URL")
    if not dsn:
        pytest.skip(
            "TEST_DB_URL niet gezet. Deze suite vergt een echte Postgres; zie "
            "de kop van tests/test_db_echt.py voor het opzetten ervan."
        )

    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(dsn) as verbinding:
        try:
            yield verbinding
        finally:
            verbinding.rollback()
