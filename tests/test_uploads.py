"""De postbus met opgeladen bronbestanden (bakkerij/db/uploads.py).

Wat hier vastligt is gedrag, en één onderscheid draagt de hele module: een
bestand dat we nog niet KUNNEN lezen blijft in de wachtrij staan, een bestand
dat STUK is wordt afgevinkt. Wie die twee door elkaar haalt, bouwt een postbus
die zichzelf leegt door alles wat ze niet begrijpt als kapot te bestempelen --
en dan is de dag dat de parser af is, de dag dat er niets meer te verwerken
valt.

De verbinding is nagebootst; de echte SQL wordt in tests/test_db_echt.py tegen
een draaiende Postgres gesteld. Twee tests hieronder lezen de migratiebestanden
zelf, omdat een lijst in Python en een check in SQL uit elkaar kunnen lopen
zonder dat iets rood wordt -- precies de fout die migratie 013 moest repareren.

Geen klantdata: alle opladingen hieronder zijn verzonnen.
"""

import datetime as dt
from pathlib import Path

import pytest

from bakkerij.db import uploads as up

MIGRATIES = Path(__file__).resolve().parents[1] / "db" / "migraties"


class NepCursor:
    def __init__(self, antwoord):
        self._antwoord = antwoord
        self.gevraagd = []
        self.rowcount = antwoord.get("rowcount", 0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.gevraagd.append((sql, params))

    def fetchall(self):
        return self._antwoord.get("rijen", [])

    def fetchone(self):
        rijen = self._antwoord.get("rijen", [])
        return rijen[0] if rijen else None


class NepVerbinding:
    """Geeft per cursor het volgende antwoord terug, in de volgorde van vragen."""

    def __init__(self, *antwoorden):
        self._antwoorden = list(antwoorden)
        self.cursors = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        antwoord = self._antwoorden.pop(0) if self._antwoorden else {}
        cur = NepCursor(antwoord)
        self.cursors.append(cur)
        return cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


GELADEN_OP = dt.datetime(2026, 8, 28, 20, 15, tzinfo=dt.UTC)

WACHTRIJ = (1, "deliveroo", "export.csv", "text/csv", 2048,
            "a" * 64, "kwinten", GELADEN_OP)


def een_upload(**afwijkend) -> up.Upload:
    velden = {
        "upload_id": 1, "bron": "deliveroo", "bestandsnaam": "export.csv",
        "mediatype": "text/csv", "bytes": 2048, "sha256": "a" * 64,
        "geladen_door": "kwinten", "geladen_op": GELADEN_OP,
    }
    velden.update(afwijkend)
    return up.Upload(**velden)


# --- lezen ------------------------------------------------------------------

def test_de_wachtrij_komt_als_uploads_terug():
    rijen = up.lees_onverwerkt(NepVerbinding({"rijen": [WACHTRIJ]}), "deliveroo")
    assert len(rijen) == 1
    assert rijen[0].bestandsnaam == "export.csv"
    assert rijen[0].verwerkt is False


def test_een_lege_postbus_is_geen_fout():
    """Anders dan bij een bevroren kanaal betekent leeg hier niets bijzonders.

    `bevroren.lees_verkopen` werpt bij nul rijen omdat daar een heel kanaal
    verdwenen zou zijn. Een postbus waar niemand iets in gelegd heeft, is
    gewoon leeg.
    """
    assert up.lees_onverwerkt(NepVerbinding({"rijen": []}), "deliveroo") == []


def test_inhoud_van_een_onbestaande_oplading_werpt():
    with pytest.raises(ValueError, match="bestaat niet"):
        up.lees_inhoud(NepVerbinding({"rijen": []}), 404)


def test_de_lijst_vraagt_de_inhoud_niet_op():
    """Een overzicht van twintig opladingen hoort geen twintig bestanden op te
    halen om twintig namen te kunnen tonen."""
    verbinding = NepVerbinding({"rijen": [WACHTRIJ]})
    up.lees_onverwerkt(verbinding, "deliveroo")
    sql, _ = verbinding.cursors[0].gevraagd[0]
    assert "inhoud" not in sql


# --- afvinken ---------------------------------------------------------------

def test_afvinken_weigert_een_onbekende_status():
    with pytest.raises(ValueError, match="status moet"):
        up.vink_af(NepVerbinding(), 1, "bijna")


def test_afvinken_kort_de_reden_in():
    """`verwerkt_reden` is leesbaar voor elke ingelogde gebruiker, en een
    pandas- of psycopg-fout kan een halve tabel meedragen."""
    verbinding = NepVerbinding({"rowcount": 1})
    up.vink_af(verbinding, 1, up.MISLUKT, "x" * 5000)
    _, params = verbinding.cursors[0].gevraagd[0]
    assert len(params[1]) == up.MAX_REDEN


def test_afvinken_van_een_al_afgevinkte_rij_geeft_false():
    """Twee runs die tegelijk dezelfde wachtrij leegmaken: de tweede hoort te
    weten dat zijn werk niet geteld heeft."""
    assert up.vink_af(NepVerbinding({"rowcount": 0}), 1, up.GELUKT) is False


def test_afvinken_commit_niet_zelf():
    """Het afvinken hoort in dezelfde transactie als wat er met het bestand
    gebeurd is; committen op twee plaatsen levert een bestand op dat verwerkt
    heet zonder dat het resultaat er staat."""
    verbinding = NepVerbinding({"rowcount": 1})
    up.vink_af(verbinding, 1, up.GELUKT)
    assert verbinding.commits == 0


# --- de bestandsnaam --------------------------------------------------------

def test_veilige_naam_haalt_padscheiding_weg():
    naam = up.veilige_naam("../../etc/passwd", 7)
    assert "/" not in naam
    assert ".." not in naam
    assert naam.startswith("000007_")


def test_veilige_naam_houdt_opladingen_uit_elkaar():
    """Twee bestanden met dezelfde naam mogen elkaar op schijf niet
    overschrijven."""
    assert up.veilige_naam("export.csv", 1) != up.veilige_naam("export.csv", 2)


def test_veilige_naam_overleeft_een_naam_zonder_bruikbare_tekens():
    assert up.veilige_naam("///", 3) == "000003_zonder-naam"


# --- de wachtrij aflopen ----------------------------------------------------

def test_zonder_lezer_blijft_de_rij_staan():
    verbinding = NepVerbinding()
    uitkomst = up.verwerk_een(verbinding, een_upload(), {})
    assert uitkomst == up.NOG_NIET_LEESBAAR
    assert verbinding.cursors == []
    assert verbinding.commits == 0


def test_een_lezer_die_nog_niet_af_is_vinkt_niets_af():
    """DE KERNTEST. `parse_items_sold` werpt vandaag NotImplementedError. Dat
    zegt iets over ons en niets over het bestand, dus de rij hoort te blijven
    staan tot de parser er wel is."""
    def nog_niet(inhoud, upload):
        raise NotImplementedError("de parser wacht op een echte export")

    verbinding = NepVerbinding({"rijen": [(b"data",)]})
    uitkomst = up.verwerk_een(verbinding, een_upload(), {"deliveroo": nog_niet})

    assert uitkomst == up.NOG_NIET_LEESBAAR
    assert verbinding.commits == 0
    assert verbinding.rollbacks == 1
    # geen enkele update naar bron_upload
    assert not any("update" in sql.lower()
                   for cur in verbinding.cursors for sql, _ in cur.gevraagd)


def test_een_stuk_bestand_wordt_wel_afgevinkt():
    def stuk(inhoud, upload):
        raise ValueError("kopregel ontbreekt")

    verbinding = NepVerbinding({"rijen": [(b"data",)]}, {"rowcount": 1})
    uitkomst = up.verwerk_een(verbinding, een_upload(), {"deliveroo": stuk})

    assert uitkomst == up.MISLUKT
    assert verbinding.commits == 1
    _, params = verbinding.cursors[1].gevraagd[0]
    assert params[0] == up.MISLUKT
    assert "kopregel ontbreekt" in params[1]
    assert "ValueError" in params[1]


def test_een_gelezen_bestand_wordt_afgevinkt_als_gelukt():
    verbinding = NepVerbinding({"rijen": [(b"data",)]}, {"rowcount": 1})
    uitkomst = up.verwerk_een(
        verbinding, een_upload(), {"deliveroo": lambda inhoud, upload: 42})

    assert uitkomst == up.GELUKT
    assert verbinding.commits == 1
    _, params = verbinding.cursors[1].gevraagd[0]
    assert params[0] == up.GELUKT
    assert "42" in params[1]


def test_de_wachtrij_geeft_een_uitkomst_per_oplading():
    verbinding = NepVerbinding({"rijen": [WACHTRIJ]})
    uitkomsten = up.verwerk_wachtrij(verbinding, "deliveroo", {})
    assert [u for _, u in uitkomsten] == [up.NOG_NIET_LEESBAAR]
    assert uitkomsten[0][0].upload_id == 1


# --- de wachten op drift tussen Python en SQL --------------------------------

def test_bronnen_lopen_gelijk_met_de_check_in_migratie_015():
    """Staat er in Python een bron die de database niet toelaat, dan faalt de
    oplading pas bij de eerste die hem gebruikt."""
    sql = (MIGRATIES / "015_bronupload.sql").read_text()
    for bron in up.BRONNEN:
        assert f"'{bron}'" in sql, (
            f"bron {bron!r} staat in BRONNEN maar niet in de check van 015"
        )


def test_de_etl_bron_staat_in_de_check_van_migratie_016():
    """Dit is de fout die 013 al eens moest repareren: een stapnaam die niet in
    `etl_run_bron_bekend` staat, breekt de transactie op de eerste regel van
    `start_run` -- en dat valt pas op wanneer iemand het script nodig heeft."""
    sql = (MIGRATIES / "016_checks_uploads.sql").read_text()
    assert "etl_run_bron_bekend" in sql
    assert f"'{up.ETL_BRON}'" in sql
