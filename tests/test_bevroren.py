"""Het bevroren kanaal teruglezen uit de database (bakkerij/db/bevroren.py).

Wat hier vastligt is gedrag: welke vorm eruit komt, dat er niets herberekend
wordt, en dat een leeg antwoord op de verkopen luid faalt in plaats van stil
een kanaal te laten verdwijnen. De verbinding is nagebootst -- de echte
SQL-vraag wordt in tests/test_db_echt.py tegen een draaiende Postgres gesteld,
want een query die nooit door een parser ging, is niet getest.

Geen klantdata: alle rijen hieronder zijn verzonnen.
"""

import pandas as pd
import pytest

from bakkerij.canoniek import KOLOMMEN
from bakkerij.db import bevroren


class NepCursor:
    def __init__(self, rijen):
        self._rijen = rijen
        self.gevraagd = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.gevraagd.append((sql, params))

    def fetchall(self):
        return self._rijen


class NepVerbinding:
    """Geeft telkens de volgende reeks rijen terug, in de volgorde van vragen."""

    def __init__(self, *reeksen):
        self._reeksen = list(reeksen)
        self.cursors = []

    def cursor(self):
        cur = NepCursor(self._reeksen.pop(0) if self._reeksen else [])
        self.cursors.append(cur)
        return cur


VERKOOPRIJ = ("2026-07-01", "1", "42", "Brood", "tgtg", 3.0, 12.75)
KOSTRIJ = ("tgtg", "2026-07", 90.0, 5.9500, 1.6700, 0.2807)


def test_verkopen_komen_in_canonieke_vorm_terug():
    df = bevroren.lees_verkopen(NepVerbinding([VERKOOPRIJ]), "tgtg")
    assert list(df.columns) == KOLOMMEN
    assert len(df) == 1
    assert df.loc[0, "kanaal"] == "tgtg"
    assert df.loc[0, "product_naam"] == "Brood"


def test_de_datum_is_een_date_en_geen_tijdstip():
    """De canonieke laag rekent in `date`; een timestamp zou hier stil
    doorschuiven tot in de kalenderbouw."""
    df = bevroren.lees_verkopen(NepVerbinding([VERKOOPRIJ]), "tgtg")
    assert df.loc[0, "datum"] == pd.Timestamp("2026-07-01").date()


def test_de_getallen_zijn_float_en_geen_decimal():
    """De canonieke CSV draagt floats. Kwam hier Decimal uit, dan wordt de
    kolom bij het samenvoegen van de kanalen een objectkolom, en die rekent
    verderop stil anders."""
    df = bevroren.lees_verkopen(NepVerbinding([VERKOOPRIJ]), "tgtg")
    assert df["aantal"].dtype == float
    assert df["omzet_excl_btw"].dtype == float


def test_een_leeg_kanaal_faalt_luid():
    """Deze functie wordt alleen aangeroepen omdat de bronbestanden ontbraken.
    Een leeg antwoord betekent dan dat het kanaal nergens meer bestaat."""
    with pytest.raises(ValueError, match="geen enkele verkoopregel"):
        bevroren.lees_verkopen(NepVerbinding([]), "tgtg")


def test_een_onbekend_kanaal_wordt_geweigerd():
    with pytest.raises(ValueError, match="onbekend kanaal"):
        bevroren.lees_verkopen(NepVerbinding([VERKOOPRIJ]), "verzonnen")


def test_het_kanaal_gaat_als_parameter_mee_en_niet_in_de_tekst():
    verbinding = NepVerbinding([VERKOOPRIJ])
    bevroren.lees_verkopen(verbinding, "tgtg")
    sql, params = verbinding.cursors[0].gevraagd[0]
    assert params == ("tgtg",)
    assert "tgtg" not in sql


def test_kanaalkost_komt_terug_zoals_hij_erin_ging():
    df = bevroren.lees_kanaalkost(NepVerbinding([KOSTRIJ]), "tgtg")
    assert list(df.columns) == ["kanaal", "maand", "stuks", "bruto_per_stuk",
                                "commissie_per_stuk", "inhouding_pct"]
    assert df.loc[0, "bruto_per_stuk"] == pytest.approx(5.95)
    assert df.loc[0, "commissie_per_stuk"] == pytest.approx(1.67)


def test_een_lege_kanaalkost_mag_wel():
    """Een kanaal zonder commissie heeft geen wig; het kanaalscherm toont die
    dan als onbeschikbaar met reden in plaats van als nul."""
    df = bevroren.lees_kanaalkost(NepVerbinding([]), "tgtg")
    assert df.empty
