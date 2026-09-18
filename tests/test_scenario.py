"""Scenario's op de prognose (blok 22): zelfde motor, andere kalender."""
import datetime as dt

import pandas as pd
import pytest

from bakkerij.model import verfijning as vf
from bakkerij.model.scenario import scenario_prognoses


def _reeks_met_vakantie_effect() -> tuple[pd.Series, pd.DataFrame]:
    """Twaalf weken vlakke omzet, waarvan drie vakantieweken op 130%.

    Groot genoeg om de vakantiefactor boven de klemondergrens te tillen, en
    vlak genoeg om elke variant met het blote oog na te rekenen.
    """
    start = pd.Timestamp("2026-03-02")  # een maandag
    dagen = pd.date_range(start, periods=12 * 7, freq="D")
    waarden = [100.0] * len(dagen)
    kal = pd.DataFrame({"datum": dagen, "schoolvakantie": False,
                        "heropening": False})
    for week in (3, 6, 9):  # drie losse vakantieweken
        for d in range(7):
            i = week * 7 + d
            waarden[i] = 130.0
            kal.loc[i, "schoolvakantie"] = True
    return pd.Series(waarden, index=dagen), kal


def _opstelling():
    reeks, kal = _reeks_met_vakantie_effect()
    doel = pd.date_range(reeks.index[-1] + dt.timedelta(days=1),
                         periods=7, freq="D")
    kal_met_doel = pd.concat([
        kal,
        pd.DataFrame({"datum": doel, "schoolvakantie": False,
                      "heropening": False}),
    ], ignore_index=True)

    def maak(vk: pd.DataFrame):
        return vf.met_feestdagcorrectie(
            vf.weekdag_niveau, vk, kenmerken=("schoolvakantie",))

    return reeks, doel, kal_met_doel, maak


def test_zonder_correctie_is_exact_de_basis():
    reeks, doel, kal, maak = _opstelling()
    varianten = {s.sleutel: s for s in scenario_prognoses(
        reeks, doel, kal, basis=vf.weekdag_niveau, maak_voorspeller=maak)}
    basis = vf.weekdag_niveau(reeks, doel)
    pd.testing.assert_series_equal(varianten["zonder_correctie"].dagen, basis)


def test_vakantieweek_ligt_boven_geen_vakantie():
    # De historiek verkoopt 30% meer in vakantieweken; het scenario "alsof
    # het vakantie is" hoort dus boven "alsof het geen vakantie is" te
    # liggen — met de gemeten factor, niet met een verzonnen getal.
    reeks, doel, kal, maak = _opstelling()
    varianten = {s.sleutel: s for s in scenario_prognoses(
        reeks, doel, kal, basis=vf.weekdag_niveau, maak_voorspeller=maak)}
    hoog = varianten["als_vakantieweek"].weektotaal
    laag = varianten["zonder_vakantie"].weektotaal
    assert hoog > laag
    assert hoog / laag == pytest.approx(1.3, rel=0.05)


def test_weektotaal_is_de_som_van_de_dagen():
    reeks, doel, kal, maak = _opstelling()
    for s in scenario_prognoses(reeks, doel, kal, basis=vf.weekdag_niveau,
                                maak_voorspeller=maak):
        assert s.weektotaal == pytest.approx(float(s.dagen.sum()))


def test_scenarios_laten_de_invoer_ongemoeid():
    # Wie de varianten rekent, verandert het anker niet: kalender en reeks
    # blijven byte voor byte wat ze waren.
    reeks, doel, kal, maak = _opstelling()
    reeks_voor, kal_voor = reeks.copy(), kal.copy()
    scenario_prognoses(reeks, doel, kal, basis=vf.weekdag_niveau,
                       maak_voorspeller=maak)
    pd.testing.assert_series_equal(reeks, reeks_voor)
    pd.testing.assert_frame_equal(kal, kal_voor)
