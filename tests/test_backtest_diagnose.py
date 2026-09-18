"""Tests voor de pure hulpfuncties van scripts/backtest_diagnose.py.

Het script zelf draait op de canonieke data en wordt hier niet aangeraakt;
getest wordt wat zonder data te toetsen valt: de foutmaten (dezelfde
definities als het harnas) en de afbakening van vakantie-overgangsdagen
(open dagen, niet kalenderdagen — dat onderscheid is precies waar zo'n
functie stil fout kan gaan).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backtest_diagnose import foutmaten, overgangsdagen, vakantiebewust_niveau

from bakkerij.model.verfijning import weekdag_niveau

# --- foutmaten ----------------------------------------------------------------

def test_foutmaten_wape_en_bias():
    verwacht = pd.Series([110.0, 90.0, 100.0])
    werkelijk = pd.Series([100.0, 100.0, 100.0])
    m = foutmaten(verwacht, werkelijk)
    assert m["n"] == 3
    # |10| + |-10| + |0| = 20 op 300 werkelijk
    assert m["wape"] == pytest.approx(20 / 300)
    # (+10 - 10 + 0) / 3 = 0: fouten heffen elkaar op, en dat moet de bias tonen
    assert m["bias"] == pytest.approx(0.0)
    assert m["som_abs_fout"] == pytest.approx(20.0)


def test_foutmaten_bias_houdt_teken():
    verwacht = pd.Series([120.0, 130.0])
    werkelijk = pd.Series([100.0, 100.0])
    m = foutmaten(verwacht, werkelijk)
    assert m["bias"] == pytest.approx(25.0)  # structureel te hoog is positief
    assert m["wape"] == pytest.approx(50 / 200)


def test_foutmaten_leeg_geeft_nullen():
    # Deelverzameling en geen volledige dict-vergelijking (19 augustus 2026):
    # deze test bewaakt dat een lege reeks nullen oplevert in plaats van NaN of
    # een deling door nul. Een vijfde metriek erbij is geen regressie, maar met
    # `==` brak hij hier wel -- en dan wordt de test aangepast zonder gelezen te
    # worden. Wat hier staat, moet nul zijn; wat er verder bij komt, gaat deze
    # test niet aan.
    m = foutmaten(pd.Series(dtype=float), pd.Series(dtype=float))
    verwacht = {"n": 0, "wape": 0.0, "bias": 0.0, "som_abs_fout": 0.0}
    assert m.items() >= verwacht.items()


# --- overgangsdagen -----------------------------------------------------------

def _open_dagen(*datums: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(d) for d in datums])


def test_overgangsdagen_telt_open_dagen_niet_kalenderdagen():
    # Vakantie 10 t/m 20 juli; de zaak is dicht op 21-23 juli. De eerste
    # drie OPEN dagen na de vakantie zijn dan 24, 25 en 26 juli.
    dagen = _open_dagen("2026-07-06", "2026-07-07", "2026-07-08",
                        "2026-07-24", "2026-07-25", "2026-07-26", "2026-07-27")
    periodes = {"zomer_2026": ("2026-07-10", "2026-07-20")}
    na, voor = overgangsdagen(dagen, periodes, n=3)
    assert list(na) == [pd.Timestamp("2026-07-24"), pd.Timestamp("2026-07-25"),
                        pd.Timestamp("2026-07-26")]
    assert list(voor) == [pd.Timestamp("2026-07-06"), pd.Timestamp("2026-07-07"),
                          pd.Timestamp("2026-07-08")]


def test_overgangsdagen_aan_de_rand_van_de_reeks():
    # Geen open dagen vóór de vakantie en maar één erna: geen fout, gewoon
    # minder overgangsdagen dan gevraagd.
    dagen = _open_dagen("2026-01-12")
    periodes = {"kerst_2025": ("2025-12-22", "2026-01-04")}
    na, voor = overgangsdagen(dagen, periodes, n=3)
    assert list(na) == [pd.Timestamp("2026-01-12")]
    assert len(voor) == 0


def test_overgangsdagen_meerdere_periodes_ontdubbeld():
    # Twee vakanties dicht op elkaar: een dag kan zowel "na" de ene als
    # "voor" de andere zijn, maar binnen één kant nooit dubbel.
    dagen = _open_dagen("2026-02-02", "2026-02-03", "2026-02-04")
    periodes = {
        "krokus_2026": ("2026-02-09", "2026-02-15"),
        "kerst_2025": ("2025-12-22", "2026-01-04"),
    }
    na, voor = overgangsdagen(dagen, periodes, n=3)
    assert list(na) == list(dagen)     # na kerst
    assert list(voor) == list(dagen)   # voor krokus
    assert not na.has_duplicates
    assert not voor.has_duplicates


# --- vakantiebewust_niveau (ronde 2, variant B) --------------------------------

def test_vakantiebewust_niveau_gebruikt_status_van_de_doeldag():
    # 70 open dagen: 56 gewone dagen op 100, dan 14 vakantiedagen op 200.
    # De weekdagmediaan (laatste 8 keer dezelfde weekdag: 6x 100, 2x 200)
    # blijft 100; het niveau moet per status verschillen.
    dagen = pd.date_range("2026-01-05", periods=70, freq="D")
    historiek = pd.Series([100.0] * 56 + [200.0] * 14, index=dagen)
    alle = pd.date_range("2026-01-05", periods=72, freq="D")
    status = pd.Series([False] * 56 + [True] * 14 + [True, False], index=alle)

    model = vakantiebewust_niveau(status)
    doeldagen = pd.DatetimeIndex([alle[70], alle[71]])  # in resp. uit vakantie
    uit = model(historiek, doeldagen)

    # Vakantiedoeldag: niveau uit de jongste 14 vakantiedagen (factor 2.0);
    # gewone doeldag: niveau uit de jongste 14 niet-vakantiedagen (factor 1.0).
    assert uit.iloc[0] == pytest.approx(200.0)
    assert uit.iloc[1] == pytest.approx(100.0)


def test_vakantiebewust_niveau_valt_terug_op_gewone_venster():
    # Maar 5 vakantiedagen in de historiek: minder dan het niveauvenster van
    # 14, dus de vakantiedoeldag krijgt het gewone venster — en het resultaat
    # valt exact samen met weekdag_niveau.
    dagen = pd.date_range("2026-01-05", periods=40, freq="D")
    historiek = pd.Series(range(100, 140), index=dagen, dtype=float)
    alle = pd.date_range("2026-01-05", periods=41, freq="D")
    status = pd.Series(False, index=alle)
    status.iloc[35:41] = True  # 5 vakantiedagen in de historiek + de doeldag

    doeldagen = pd.DatetimeIndex([alle[40]])
    uit = vakantiebewust_niveau(status)(historiek, doeldagen)
    referentie = weekdag_niveau(historiek, doeldagen)
    assert uit.iloc[0] == pytest.approx(referentie.iloc[0])


def test_vakantiebewust_niveau_lekt_geen_toekomst():
    # Dezelfde leklat als elke voorspeller: een doeldag in de historiek is
    # een harde fout.
    dagen = pd.date_range("2026-01-05", periods=20, freq="D")
    historiek = pd.Series(100.0, index=dagen)
    status = pd.Series(False, index=dagen)
    with pytest.raises(ValueError, match="lekt de toekomst"):
        vakantiebewust_niveau(status)(historiek, pd.DatetimeIndex([dagen[5]]))
