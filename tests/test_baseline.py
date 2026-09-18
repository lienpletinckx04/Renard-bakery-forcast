"""Tests voor de baselines.

De oude versie van deze tests draaide uitsluitend op aaneensluitende reeksen, en
dat is precies waarom de weekdagverschuiving na een sluiting nooit is opgevallen.
Elke test hieronder die over weekdagen gaat, bestaat daarom in twee varianten:
één zonder gaten en één met een sluiting die géén veelvoud van zeven is.
"""
import numpy as np
import pandas as pd
import pytest

from bakkerij.model.baseline import (
    naive,
    seizoen_naive,
    weekdag_gemiddelde,
    weekdag_mediaan,
)

PATROON = np.array([10.0, 10.0, 10.0, 10.0, 20.0, 30.0, 5.0])  # ma t/m zo


def _reeks(start="2025-01-06", dagen=70) -> pd.Series:
    """Perfect weekpatroon, startend op een maandag."""
    index = pd.date_range(start, periods=dagen, freq="D")
    return pd.Series(PATROON[index.dayofweek], index=index)


def _volgende_dagen(historiek: pd.Series, aantal: int) -> pd.DatetimeIndex:
    start = historiek.index[-1] + pd.Timedelta(days=1)
    return pd.date_range(start, periods=aantal, freq="D")


# --- naive ------------------------------------------------------------------

def test_naive_herhaalt_de_laatst_gemeten_waarde():
    r = _reeks()
    doel = _volgende_dagen(r, 3)
    uit = naive(r, doel)
    assert uit.index.equals(doel)
    assert (uit == r.iloc[-1]).all()


# --- seizoen_naive ----------------------------------------------------------

def test_seizoen_naive_vangt_het_weekpatroon_zonder_gaten():
    r = _reeks()
    doel = _volgende_dagen(r, 7)
    uit = seizoen_naive(r, doel)
    assert np.allclose(uit.to_numpy(), PATROON[doel.dayofweek])


def test_seizoen_naive_blijft_op_de_juiste_weekdag_na_een_sluiting():
    """Het geval dat de oude implementatie fout deed.

    Drie sluitingsdagen: geen veelvoud van zeven, dus positioneel rekenen zou de
    weekdag met drie opschuiven. Gemeten op de oude versie: maandag kreeg de
    waarde van een vrijdag (130 tegen 100), dinsdag die van een zaterdag.
    """
    r = _reeks(dagen=28)
    dicht = pd.date_range("2025-01-27", periods=3, freq="D")  # ma, di, wo
    met_gat = r.drop(dicht)
    doel = _volgende_dagen(met_gat, 7)

    uit = seizoen_naive(met_gat, doel)

    assert np.allclose(uit.to_numpy(), PATROON[doel.dayofweek])
    # En expliciet het geval dat eerder misging: de eerstvolgende maandag.
    maandag = doel[doel.dayofweek == 0][0]
    assert uit.loc[maandag] == pytest.approx(10.0)


def test_seizoen_naive_over_een_sluiting_van_meer_dan_een_week():
    # De paassluiting van 2025 duurde acht dagen; de zomersluiting ruim drie weken.
    r = _reeks(dagen=60)
    met_gat = r.drop(pd.date_range("2025-02-10", periods=8, freq="D"))
    doel = _volgende_dagen(met_gat, 7)
    uit = seizoen_naive(met_gat, doel)
    assert np.allclose(uit.to_numpy(), PATROON[doel.dayofweek])


def test_zonder_waarneming_voor_een_weekdag_valt_hij_terug_op_de_mediaan():
    # Een winkel die nooit op zondag open was: de zondag heeft geen historiek.
    r = _reeks(dagen=28)
    zonder_zondag = r[r.index.dayofweek != 6]
    doel = _volgende_dagen(zonder_zondag, 7)
    uit = seizoen_naive(zonder_zondag, doel)
    zondag = doel[doel.dayofweek == 6][0]
    assert uit.loc[zondag] == pytest.approx(float(zonder_zondag.median()))


# --- weekdag_gemiddelde en weekdag_mediaan ----------------------------------

def test_weekdag_gemiddelde_klopt_op_een_stabiel_patroon():
    r = _reeks()
    doel = _volgende_dagen(r, 7)
    uit = weekdag_gemiddelde(r, doel)
    assert np.allclose(uit.to_numpy(), PATROON[doel.dayofweek])


def test_weekdag_gemiddelde_blijft_correct_na_een_sluiting():
    r = _reeks(dagen=56)
    met_gat = r.drop(pd.date_range("2025-02-04", periods=5, freq="D"))
    doel = _volgende_dagen(met_gat, 7)
    uit = weekdag_gemiddelde(met_gat, doel)
    assert np.allclose(uit.to_numpy(), PATROON[doel.dayofweek])


def test_weekdag_mediaan_negeert_een_uitschieter_die_het_gemiddelde_meesleept():
    r = _reeks(dagen=70).copy()
    laatste_zaterdag = r.index[r.index.dayofweek == 5][-1]
    r.loc[laatste_zaterdag] = 300.0  # groepsbestelling, geen vraagsignaal
    doel = _volgende_dagen(r, 7)
    zaterdag = doel[doel.dayofweek == 5][0]

    assert weekdag_mediaan(r, doel).loc[zaterdag] == pytest.approx(30.0)
    assert weekdag_gemiddelde(r, doel).loc[zaterdag] > 60.0


# --- wat er niet mag --------------------------------------------------------

def test_een_doeldag_binnen_de_historiek_wordt_geweigerd():
    """Anders lekt de backtest de toekomst zonder dat iemand het ziet."""
    r = _reeks()
    binnen = pd.DatetimeIndex([r.index[-3]])
    with pytest.raises(ValueError, match="lekt de toekomst"):
        seizoen_naive(r, binnen)


def test_ongesorteerde_historiek_wordt_geweigerd():
    r = _reeks(dagen=14).iloc[::-1]
    with pytest.raises(ValueError, match="gesorteerd"):
        seizoen_naive(r, _volgende_dagen(r.sort_index(), 1))


def test_lege_historiek_wordt_geweigerd():
    leeg = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    doel = pd.date_range("2025-01-01", periods=1, freq="D")
    with pytest.raises(ValueError, match="lege historiek"):
        naive(leeg, doel)


def test_elke_baseline_geeft_precies_de_gevraagde_dagen_terug():
    """Het contract waar de backtest op rust: index in, dezelfde index uit."""
    r = _reeks()
    met_gat = r.drop(pd.date_range("2025-02-10", periods=3, freq="D"))
    doel = _volgende_dagen(met_gat, 5)
    for fn in (naive, seizoen_naive, weekdag_gemiddelde, weekdag_mediaan):
        assert fn(met_gat, doel).index.equals(doel), fn.__name__
