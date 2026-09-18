"""Tests voor de categorieprognose (bakkerij/model/categorie.py).

Het kernrisico is dubbel: een categoriebundel die niet meer optelt tot de
dagomzet (dan spreekt het blok de rest van het scherm tegen), en een
som-voorspeller die bij het snijden op de trainingsgrens toekomst lekt —
een gelekte dag maakt elke gemeten fout te mooi.
"""
import datetime

import pandas as pd

from bakkerij import berekening as bk
from bakkerij import canoniek
from bakkerij.model.baseline import seizoen_naive
from bakkerij.model.categorie import (
    categorie_prognoses,
    categorie_reeksen,
    som_van_categorieen,
)


def _open_verkopen(dagen: int = 250) -> pd.DataFrame:
    datums = pd.date_range("2025-01-06", periods=dagen, freq="D")
    rijen = []
    for d in datums:
        rijen.append({"datum": d.date(), "filiaal_id": "Kassa 1",
                      "product_id": "10", "product_naam": "Brood wit",
                      "kanaal": "winkel", "aantal": 1.0, "omzet_excl_btw": 100.0})
        rijen.append({"datum": d.date(), "filiaal_id": "Kassa 1",
                      "product_id": "20", "product_naam": "Eclair",
                      "kanaal": "winkel", "aantal": 1.0, "omzet_excl_btw": 40.0})
        rijen.append({"datum": d.date(), "filiaal_id": "Kassa 1",
                      "product_id": "30", "product_naam": "Koffie",
                      "kanaal": "winkel", "aantal": 1.0, "omzet_excl_btw": 10.0})
    verkopen = pd.DataFrame(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    return bk.open_verkopen(verkopen, kal)


GROEPEN = pd.Series({"10": "Brood", "20": "Patisserie", "30": "Dranken"})


def test_categorie_reeksen_bundelt_de_staart_en_behoudt_de_som():
    open_v = _open_verkopen()
    reeksen = categorie_reeksen(open_v, GROEPEN, top_n=2)
    namen = [n for n, _, _ in reeksen]
    assert namen == ["Brood", "Patisserie", "Overige categorieën"]
    # de som van de categorieën is de dagomzet, elke dag
    som = None
    for _, r, _ in reeksen:
        som = r if som is None else som.add(r, fill_value=0.0)
    dag = open_v.groupby("datum")["omzet_excl_btw"].sum()
    pd.testing.assert_series_equal(som.sort_index(), dag.sort_index(),
                                   check_names=False)


def test_som_voorspeller_snijdt_op_de_trainingsgrens():
    """De som-voorspeller mag alleen categoriedagen t/m het einde van de
    training zien. Een reeks met een omzetsprong ná die grens verraadt een
    lek onmiddellijk: de voorspelling zou de sprong al kennen."""
    open_v = _open_verkopen()
    reeksen = categorie_reeksen(open_v, GROEPEN, top_n=2)
    # sprong in de laatste 30 dagen van één categorie
    naam, reeks, aandeel = reeksen[0]
    gesprongen = reeks.copy()
    gesprongen.iloc[-30:] *= 10
    reeksen[0] = (naam, gesprongen, aandeel)

    dag = open_v.groupby("datum")["omzet_excl_btw"].sum()
    dag.index = pd.to_datetime(dag.index)
    train_eind = dag.index[-40]  # ruim vóór de sprong
    doel = dag.index[-39:-32]
    voorspeld = som_van_categorieen(reeksen, seizoen_naive)(
        dag[dag.index <= train_eind], doel
    )
    # zonder lek blijft de voorspelling op het oude niveau (~150/dag)
    assert float(voorspeld.max()) < 400


def test_categorie_prognoses_slaat_korte_historiek_over_met_naam():
    open_v = _open_verkopen(dagen=250)
    reeksen = categorie_reeksen(open_v, GROEPEN, top_n=2)
    # één categorie kunstmatig inkorten tot onder de meetdrempel
    naam, reeks, aandeel = reeksen[1]
    reeksen[1] = (naam, reeks.iloc[-60:], aandeel)
    doeldagen = pd.date_range("2025-09-15", periods=7, freq="D")
    prognoses, overgeslagen = categorie_prognoses(
        reeksen, seizoen_naive, doeldagen, min_train=180)
    assert naam in overgeslagen
    assert all(p.categorie != naam for p in prognoses)
    # wie wél meedoet, draagt een gemeten fout en een band per dag
    assert all(p.wape >= 0 and len(p.band) == 7 for p in prognoses)


def test_categorie_prognose_band_ligt_om_de_verwachting():
    open_v = _open_verkopen()
    reeksen = categorie_reeksen(open_v, GROEPEN, top_n=2)
    doeldagen = pd.date_range(
        datetime.date(2025, 9, 15), periods=7, freq="D")
    prognoses, _ = categorie_prognoses(reeksen, seizoen_naive, doeldagen,
                                       min_train=180)
    for p in prognoses:
        assert (p.band["onder"] <= p.band["verwacht"]).all()
        assert (p.band["verwacht"] <= p.band["boven"]).all()
        assert p.weektotaal > 0


# --- schoolvakantieregimes (features/calendar.py) --------------------------------

def test_beide_vakantieregimes_markeren_hun_eigen_dagen():
    from bakkerij.features.calendar import (
        SCHOOLVAKANTIES_FR,
        SCHOOLVAKANTIES_VL,
        markeer_schoolvakanties,
    )
    dagen = pd.DataFrame({"datum": pd.date_range("2025-02-20", "2025-03-12")})
    vl = markeer_schoolvakanties(dagen, SCHOOLVAKANTIES_VL)
    fr = markeer_schoolvakanties(dagen, SCHOOLVAKANTIES_FR)
    # 25 februari 2025: FR-carnaval (24 feb–9 mrt), geen VL-krokus (3–9 mrt)
    d25 = pd.Timestamp("2025-02-25")
    assert bool(fr.loc[fr["datum"] == d25, "schoolvakantie"].iloc[0]) is True
    assert bool(vl.loc[vl["datum"] == d25, "schoolvakantie"].iloc[0]) is False
    # 5 maart 2025: allebei vakantie
    d5 = pd.Timestamp("2025-03-05")
    assert bool(fr.loc[fr["datum"] == d5, "schoolvakantie"].iloc[0]) is True
    assert bool(vl.loc[vl["datum"] == d5, "schoolvakantie"].iloc[0]) is True
