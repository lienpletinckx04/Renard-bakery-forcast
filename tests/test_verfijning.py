"""De modelverfijningen: niveau-schaling en feestdagcorrectie.

De tests bouwen kleine synthetische reeksen waarin het juiste antwoord op
papier vaststaat, en pinnen daarnaast de beschermingen vast: de klem, de
minimumwaarnemingen, en het lek-verbod dat van baseline._controleer komt.
"""
import datetime as dt

import pandas as pd
import pytest

from bakkerij.model import verfijning as vf


def _reeks(waarden, start="2025-01-06"):
    """Aaneengesloten dagreeks vanaf een maandag."""
    idx = pd.date_range(start, periods=len(waarden), freq="D")
    return pd.Series([float(w) for w in waarden], index=idx)


def _weekpatroon(weken, factor=1.0):
    """ma..zo = 100..160, geschaald."""
    return [(100 + 10 * d) * factor for _ in range(weken) for d in range(7)]


def test_weekdag_niveau_is_de_mediaan_in_een_stabiel_regime():
    reeks = _reeks(_weekpatroon(10))
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    v = vf.weekdag_niveau(reeks, doel)
    # Stabiel regime: factor 1, dus exact het weekdagprofiel.
    assert v.iloc[0] == pytest.approx(100.0)  # maandag
    assert v.iloc[5] == pytest.approx(150.0)  # zaterdag


def test_weekdag_niveau_volgt_een_niveausprong():
    # Acht weken op niveau 1, dan twee weken op 1,3x: het profiel (mediaan
    # over 8) hangt nog grotendeels op het oude niveau, de niveaufactor
    # corrigeert naar het recente regime.
    reeks = _reeks(_weekpatroon(8) + _weekpatroon(2, factor=1.3))
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    v = vf.weekdag_niveau(reeks, doel)
    # Zonder schaling zou maandag 100 zijn; met schaling hoort hij richting
    # 130 te bewegen. We eisen minstens 20% van de sprong.
    assert v.iloc[0] > 106.0
    # En de vorm blijft: zaterdag hoger dan maandag, in dezelfde verhouding.
    assert v.iloc[5] / v.iloc[0] == pytest.approx(1.5, rel=0.01)


def test_weekdag_niveau_klemt_extreme_factoren():
    # Laatste twee weken factor 10: de klem houdt het niveau op 2,0.
    reeks = _reeks(_weekpatroon(8) + _weekpatroon(2, factor=10))
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    v = vf.weekdag_niveau(reeks, doel)
    # De grens staat hier als getal en niet als vf.KLEM[1]: een test die de
    # klem uit de module leest, blijft groen wanneer iemand de klem op 50 zet
    # (audit 15 aug, punt d). De belofte is 2,0 — het profiel (mediaan over
    # 8 weken) kan daarbovenop tot de sprongweken meegroeien, vandaar × 1,5.
    assert v.iloc[0] / 100.0 <= 2.0 * 1.5


def test_weekdag_niveau_weigert_doeldagen_in_de_historiek():
    reeks = _reeks(_weekpatroon(10))
    with pytest.raises(ValueError, match="lekt de toekomst"):
        vf.weekdag_niveau(reeks, reeks.index[-3:])


def _kalender_met(datums, kenmerk):
    alle = pd.date_range("2025-01-06", "2025-12-31", freq="D")
    return pd.DataFrame(
        {
            "datum": alle,
            kenmerk: [d in set(pd.to_datetime(datums)) for d in alle],
        }
    )


def test_feestdagcorrectie_leert_de_factor_uit_de_historiek():
    # Weekpatroon met vier "feestdagen" die telkens 1,5x hun weekdag doen.
    waarden = _weekpatroon(10)
    reeks = _reeks(waarden)
    feestdagen = [reeks.index[9], reeks.index[23], reeks.index[37], reeks.index[51]]
    for d in feestdagen:
        reeks[d] *= 1.5

    kalender = _kalender_met(feestdagen + [reeks.index[-1] + dt.timedelta(days=3)],
                             "feestdag")
    basis = vf.weekdag_niveau
    model = vf.met_feestdagcorrectie(basis, kalender, kenmerken=("feestdag",))

    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    met = model(reeks, doel)
    zonder = basis(reeks, doel)
    # Doeldag 3 is een feestdag: daar hoort de factor te zitten, elders niet.
    assert met.iloc[2] / zonder.iloc[2] == pytest.approx(1.5, rel=0.1)
    assert met.iloc[0] == pytest.approx(zonder.iloc[0])


def test_feestdagcorrectie_zwijgt_onder_de_minimumwaarnemingen():
    waarden = _weekpatroon(10)
    reeks = _reeks(waarden)
    feestdagen = [reeks.index[9], reeks.index[23]]  # maar twee waarnemingen
    for d in feestdagen:
        reeks[d] *= 1.5
    kalender = _kalender_met(
        feestdagen + [reeks.index[-1] + dt.timedelta(days=3)], "feestdag"
    )
    model = vf.met_feestdagcorrectie(vf.weekdag_niveau, kalender, kenmerken=("feestdag",))
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    assert model(reeks, doel).iloc[2] == pytest.approx(
        vf.weekdag_niveau(reeks, doel).iloc[2]
    )


def test_feestdagcorrectie_kent_onbekende_kenmerken_niet():
    reeks = _reeks(_weekpatroon(10))
    kalender = _kalender_met([], "feestdag")
    model = vf.met_feestdagcorrectie(
        vf.weekdag_niveau, kalender, kenmerken=("feestdag", "bestaat_niet")
    )
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    # Geen crash: het onbekende kenmerk wordt genegeerd.
    assert len(model(reeks, doel)) == 7


def test_feestdagcorrectie_klemt_de_factor():
    waarden = _weekpatroon(10)
    reeks = _reeks(waarden)
    feestdagen = [reeks.index[i] for i in (9, 23, 37, 51)]
    for d in feestdagen:
        reeks[d] *= 20  # absurde uitschieters
    kalender = _kalender_met(
        feestdagen + [reeks.index[-1] + dt.timedelta(days=3)], "feestdag"
    )
    model = vf.met_feestdagcorrectie(vf.weekdag_niveau, kalender, kenmerken=("feestdag",))
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7, freq="D")
    met = model(reeks, doel)
    zonder = vf.weekdag_niveau(reeks, doel)
    # De uitschieters zijn ×20, dus de ruwe factor slaat ver door en de klem
    # moet vol aangrijpen: precies 2,0 — als getal, niet als vf.KLEM[1],
    # anders verandert de belofte stil mee met de constante (audit 15 aug).
    assert met.iloc[2] / zonder.iloc[2] == pytest.approx(2.0)

def test_opbouw_is_exact_de_voorspeller_in_kolommen():
    """De opbouw op het scherm mag nooit een tweede, net iets ander model
    worden: het product van de kolommen is de voorspelling, op de cent."""
    reeks = _reeks(_weekpatroon(10))
    vakantiedagen = [reeks.index[9], reeks.index[23], reeks.index[37],
                     reeks.index[51]]
    for d in vakantiedagen:
        reeks[d] *= 0.8
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1), periods=7,
                         freq="D")
    kalender = _kalender_met(list(vakantiedagen) + [doel[2]], "schoolvakantie")

    model = vf.met_feestdagcorrectie(vf.weekdag_niveau, kalender,
                                     kenmerken=("schoolvakantie",))
    voorspeld = model(reeks, doel)
    ob = vf.opbouw(reeks, doel, kalender, kenmerken=("schoolvakantie",))

    assert list(ob["verwacht"]) == pytest.approx(list(voorspeld))
    assert list(ob["basis"] * ob["niveau"] * ob["kalenderfactor"]) == \
        pytest.approx(list(voorspeld))
    # De actieve kenmerknaam staat op de vakantiedag, en nergens anders.
    assert ob.loc[2, "kenmerk"] == "schoolvakantie"
    assert (ob.loc[ob.index != 2, "kenmerk"] == "").all()
    assert ob.loc[2, "kalenderfactor"] != 1.0
    assert (ob.loc[ob.index != 2, "kalenderfactor"] == 1.0).all()
