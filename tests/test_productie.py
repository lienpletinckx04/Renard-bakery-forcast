"""Eén constructie van de productievoorspeller (bakkerij/model/productie.py).

Deze tests bestaan om één reden: er waren er drie, en ze liepen uiteen. De
contractbouw had de echte, het backtest-rapport leende die, en de diagnose
bouwde hem na — met de ná-vakantiedagen uit `reeks.index` in plaats van uit
`open_of_gepland_open`. Diezelfde ene afwijking gaf twee tegengestelde
verdicten over de heropeningscorrectie (+0,12 punt tegen -0,002), en die
patstelling hield twee sessies lang elke eerlijke beslissing tegen.

Wat hier vastligt is dus niet zozeer een berekening als wel een AFSPRAAK: dat
de drie scripts hun voorspeller uit deze module halen en hem nergens nabouwen.
Een bronwacht, zoals `test_schermen_lopen_gelijk_met_de_ui` er een is.
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from bakkerij.model import productie as pr

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

#: De drie scripts die met de productievoorspeller rekenen.
GEBRUIKERS = ("contract_bouw.py", "backtest_diagnose.py", "backtest_rapport.py")


def _kalender(van: str, tot: str, *, gemeten_tot: str) -> pd.DataFrame:
    """Een kalender in de vorm die de canoniekbouw oplevert.

    `winkel_open` staat buiten het gemeten bereik op False — net als in het
    echt, en juist dat maakte de eerste versie van `open_of_gepland_open` stil
    fout.
    """
    dagen = pd.date_range(van, tot, freq="D")
    grens = pd.Timestamp(gemeten_tot)
    return pd.DataFrame({
        "datum": dagen,
        "winkel_gemeten": dagen <= grens,
        "winkel_open": dagen <= grens,
    })


# --- de afspraak: één bouwplaats --------------------------------------------

@pytest.mark.parametrize("script", GEBRUIKERS)
def test_de_scripts_lenen_de_voorspeller_en_bouwen_hem_niet_na(script):
    bron = (SCRIPTS / script).read_text(encoding="utf-8")
    assert "from bakkerij.model.productie import" in bron, (
        f"{script} haalt de productievoorspeller niet uit "
        "bakkerij/model/productie.py"
    )


@pytest.mark.parametrize("script", GEBRUIKERS)
def test_geen_script_definieert_zijn_eigen_bouw_voorspeller(script):
    """De diagnose deed dit tot 19 augustus 2026, onder de kop "identiek
    herbouwd". Ze was niet identiek."""
    bron = (SCRIPTS / script).read_text(encoding="utf-8")
    assert "def bouw_voorspeller" not in bron, (
        f"{script} definieert een eigen bouw_voorspeller; er hoort er één te "
        "zijn, in bakkerij/model/productie.py"
    )
    assert "\nBASIS = " not in bron, (
        f"{script} zet zijn eigen BASIS; die staat in productie.py"
    )


# --- wat de constructie oplevert --------------------------------------------

def test_kenmerken_bepaalt_wat_er_gecorrigeerd_wordt():
    """KENMERKEN ís de definitie van "wat in productie is". Staat er iets in
    dat de kalender niet draagt, dan corrigeert het model met een vlag die
    nergens vandaan komt."""
    kalender = _kalender("2026-01-01", "2026-03-31", gemeten_tot="2026-02-28")
    kolommen = set(pr.prognosekalender(kalender).columns)
    for kenmerk in pr.KENMERKEN:
        assert kenmerk in kolommen, (
            f"KENMERKEN noemt {kenmerk!r}, maar prognosekalender levert die "
            "kolom niet"
        )


def test_de_heropeningsvlag_bestaat_maar_corrigeert_niets():
    """Ze wordt berekend omdat de diagnose ermee meet; ze staat niet in
    KENMERKEN en raakt de prognose dus niet aan. Beide helften horen waar te
    blijven — anders is de vlag ofwel dood, ofwel stil in productie."""
    kalender = _kalender("2026-01-01", "2026-03-31", gemeten_tot="2026-02-28")
    assert "heropening" in pr.prognosekalender(kalender).columns
    assert "heropening" not in pr.KENMERKEN


def test_bouw_voorspeller_is_de_wikkel_op_de_prognosekalender():
    """De twee wegen naar dezelfde voorspeller moeten hetzelfde opleveren; de
    scenario's lopen langs `wikkel`, de rest langs `bouw_voorspeller`."""
    kalender = _kalender("2025-01-01", "2026-06-30", gemeten_tot="2026-05-31")
    reeks = pd.Series(
        1000.0 + pd.Series(range(400)) * 0.5,
        index=pd.date_range("2025-01-01", periods=400, freq="D"),
    )
    doeldagen = pd.DatetimeIndex(
        [dt.date(2026, 6, d) for d in range(1, 8)]
    )
    langs_bouw = pr.bouw_voorspeller(kalender)(reeks, doeldagen)
    langs_wikkel = pr.wikkel(pr.prognosekalender(kalender))(reeks, doeldagen)
    pd.testing.assert_series_equal(langs_bouw, langs_wikkel)


def test_een_kandidaat_draagt_niet_de_productienaam():
    """De naam reist mee als naam van de voorspelde reeks, en die naam komt in
    het backtest-rapport terecht. Zou een kandidaat hem dragen, dan staat er
    "weekdag_niveau_vakantie_fr" boven een meting van iets anders — precies de
    verwarring van 18 augustus."""
    kalender = _kalender("2025-01-01", "2026-06-30", gemeten_tot="2026-05-31")
    reeks = pd.Series(
        1000.0 + pd.Series(range(400)) * 0.5,
        index=pd.date_range("2025-01-01", periods=400, freq="D"),
    )
    doeldagen = pd.DatetimeIndex([dt.date(2026, 6, d) for d in range(1, 8)])

    productie = pr.bouw_voorspeller(kalender)(reeks, doeldagen)
    kandidaat = pr.bouw_voorspeller(
        kalender, kenmerken=("schoolvakantie", "heropening")
    )(reeks, doeldagen)

    assert productie.name == pr.MODELNAAM
    assert kandidaat.name != pr.MODELNAAM


#: Per kenmerk uit `productie.KENMERKEN`: het woord dat in de Nederlandse naam,
#: in de Franse naam en in de machinenaam moet staan. Deze tabel is met opzet
#: met de hand bijgehouden — juist het uitbreiden ervan is het moment waarop
#: iemand merkt dat de modelkaart nog bijgewerkt moet worden.
KENMERKWOORDEN = {
    "schoolvakantie": ("schoolvakantie", "vacances scolaires", "vakantie"),
}


def test_de_modelkaart_noemt_elk_kenmerk_dat_het_model_gebruikt():
    """Voorkomt dat de modelkaart iets anders belooft dan het model doet.

    `KENMERKEN`, `VOORSPELLER_NAAM(_FR)` en `MODELNAAM` stonden tot 19 augustus
    2026 volledig los van elkaar: drie constanten onder elkaar, zonder enige
    controle dat ze hetzelfde zeggen. Wie een kenmerk toevoegt, verandert
    daarmee wat het model doet, maar niet wat het scherm erover zegt — en dan
    staat er "met schoolvakantiecorrectie" boven een voorspelling die
    intussen ook op feestdagen corrigeert.

    Dat is geen cosmetisch verschil. Harde regel 7 zegt dat een voorspelling
    zonder backtest een mening is; een modelkaart die het verkeerde model
    beschrijft, presenteert een backtest van iets anders dan wat draait, en
    dat is dezelfde fout met een geruststellend etiket erop.

    De assert op de sleutels van de tabel is de eigenlijke wacht: een nieuw
    kenmerk laat deze test vallen vóór iemand aan de teksten toekomt.
    """
    assert set(pr.KENMERKEN) == set(KENMERKWOORDEN), (
        "KENMERKEN en KENMERKWOORDEN lopen uiteen — vul de tabel aan en "
        "werk VOORSPELLER_NAAM, VOORSPELLER_NAAM_FR en MODELNAAM bij"
    )
    for kenmerk in pr.KENMERKEN:
        nl, fr, machine = KENMERKWOORDEN[kenmerk]
        assert nl in pr.VOORSPELLER_NAAM, (kenmerk, pr.VOORSPELLER_NAAM)
        assert fr in pr.VOORSPELLER_NAAM_FR, (kenmerk, pr.VOORSPELLER_NAAM_FR)
        assert machine in pr.MODELNAAM, (kenmerk, pr.MODELNAAM)
