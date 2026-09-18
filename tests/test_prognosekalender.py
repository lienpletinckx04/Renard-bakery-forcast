"""Tests voor de kalender die de productievoorspeller ziet.

Deze tests bestaan omdat er niets was. De zwakke-plekken-audit van 15 augustus
2026 vond dat `prognosekalender` de heropeningscorrectie nooit liet vuren op de
getoonde prognose: de open dagen kwamen uit `winkel_open`, en die staat voor
elke toekomstige dag op False. De modelkaart beloofde "met heropeningscorrectie"
en WAPE 7,6%, terwijl het cijfer op het scherm uit een ander model kwam — op
precies de dagen waar de diagnose de grootste fout had gemeten.

Geen enkele test raakte die functie. Dat is de eigenlijke bevinding: de
correctie was gemeten, geadopteerd, gedocumenteerd in twee bestanden en in
docs/beslissingen.md, en deed niets.
"""
import datetime as dt

import pandas as pd

# Sinds 19 augustus 2026 uit bakkerij/ en niet meer uit scripts/: de
# constructie van de productievoorspeller stond op drie plaatsen en staat nu
# op één. Zie de kop van bakkerij/model/productie.py.
from bakkerij.model.productie import (
    HEROPENING_DAGEN,
    open_of_gepland_open,
    prognosekalender,
)


def _kalender(van: str, tot: str, *, gemeten_tot: str,
              gepland_dicht: tuple[str, ...] = ()) -> pd.DataFrame:
    """Een kalender in de vorm die de canoniekbouw oplevert.

    `winkel_gemeten` is waar tot en met `gemeten_tot`; `winkel_open` is waar op
    gemeten dagen en — net als in de echte canoniekbouw — False daarbuiten.
    Juist dat laatste is wat de fout veroorzaakte.
    """
    dagen = pd.date_range(van, tot, freq="D")
    grens = pd.Timestamp(gemeten_tot)
    dicht = {pd.Timestamp(d) for d in gepland_dicht}
    return pd.DataFrame({
        "datum": dagen,
        "winkel_gemeten": dagen <= grens,
        "winkel_open": dagen <= grens,
        "gepland_dicht": [d in dicht for d in dagen],
    })


# --- open_of_gepland_open ---------------------------------------------------

def test_een_toekomstige_dag_telt_als_open_en_niet_als_gesloten():
    """De kern van de fout: buiten het gemeten bereik is winkel_open False,
    maar niet-gemeten is niet hetzelfde als dicht."""
    kal = _kalender("2026-07-01", "2026-08-31", gemeten_tot="2026-07-31")
    open_ = open_of_gepland_open(kal)
    toekomst = kal["datum"] > pd.Timestamp("2026-07-31")
    assert open_[toekomst].all()


def test_een_gemeten_gesloten_dag_telt_niet_als_open():
    kal = _kalender("2026-07-01", "2026-07-31", gemeten_tot="2026-07-31")
    kal.loc[kal["datum"] == pd.Timestamp("2026-07-15"), "winkel_open"] = False
    open_ = open_of_gepland_open(kal)
    assert not open_[kal["datum"] == pd.Timestamp("2026-07-15")].iloc[0]


def test_een_aangekondigde_sluiting_telt_niet_als_open():
    kal = _kalender("2026-07-01", "2026-08-31", gemeten_tot="2026-07-31",
                    gepland_dicht=("2026-08-17", "2026-08-18"))
    open_ = open_of_gepland_open(kal)
    dicht = kal["datum"].isin([pd.Timestamp("2026-08-17"),
                               pd.Timestamp("2026-08-18")])
    assert not open_[dicht].any()
    assert open_[~dicht & (kal["datum"] > pd.Timestamp("2026-07-31"))].all()


def test_zonder_de_kolom_gepland_dicht_verandert_er_niets():
    kal = _kalender("2026-07-01", "2026-08-31", gemeten_tot="2026-07-31")
    assert open_of_gepland_open(kal.drop(columns=["gepland_dicht"])).equals(
        open_of_gepland_open(kal)
    )


def test_waarheidskolommen_uit_een_csv_worden_niet_omgekeerd_gelezen():
    """Een kalender die over schijf is gegaan draagt "True"/"False" als tekst.
    `astype(bool)` maakt van de string "False" een True, en dan zou elke dag
    gesloten heten en de heropening nergens meer vuren."""
    kal = _kalender("2026-07-01", "2026-08-31", gemeten_tot="2026-07-31")
    tekst = kal.assign(
        winkel_gemeten=kal["winkel_gemeten"].map(str),
        winkel_open=kal["winkel_open"].map(str),
        gepland_dicht=kal["gepland_dicht"].map(str),
    )
    assert open_of_gepland_open(tekst).equals(open_of_gepland_open(kal))


# --- prognosekalender -------------------------------------------------------

def test_de_heropening_vuurt_op_de_dagen_na_een_toekomstige_vakantie():
    """Het geval van 15 augustus 2026: de Franstalige zomervakantie eindigt op
    23 augustus, de meting stopt op 31 juli. De eerste drie open dagen erna
    horen de heropeningsvlag te dragen."""
    kal = _kalender("2026-06-01", "2026-09-15", gemeten_tot="2026-07-31",
                    gepland_dicht=tuple(
                        str(dt.date(2026, 8, d)) for d in range(1, 24)
                    ))
    vk = prognosekalender(kal).set_index("datum")

    for dag in ("2026-08-24", "2026-08-25", "2026-08-26"):
        assert vk.loc[pd.Timestamp(dag), "heropening"], dag
    # De dag ná het venster van drie draagt hem niet meer.
    assert not vk.loc[pd.Timestamp("2026-08-27"), "heropening"]
    # En een gesloten dag binnen de vakantie evenmin.
    assert not vk.loc[pd.Timestamp("2026-08-20"), "heropening"]


def test_precies_zoveel_heropeningsdagen_als_de_constante_zegt():
    kal = _kalender("2026-06-01", "2026-09-15", gemeten_tot="2026-07-31",
                    gepland_dicht=tuple(
                        str(dt.date(2026, 8, d)) for d in range(1, 24)
                    ))
    vk = prognosekalender(kal)
    na_vakantie = vk[vk["datum"] > pd.Timestamp("2026-08-23")]
    assert int(na_vakantie["heropening"].sum()) == HEROPENING_DAGEN


def test_een_aangekondigde_sluiting_schuift_de_heropening_door():
    """Gaat de zaak ná de vakantie nóg twee dagen dicht, dan zijn de eerste
    open dagen later — de vlag hoort mee te schuiven en niet op een gesloten
    dag te blijven staan."""
    dicht = tuple(str(dt.date(2026, 8, d)) for d in range(1, 26))
    kal = _kalender("2026-06-01", "2026-09-15", gemeten_tot="2026-07-31",
                    gepland_dicht=dicht)
    vk = prognosekalender(kal).set_index("datum")

    assert not vk.loc[pd.Timestamp("2026-08-24"), "heropening"]
    assert not vk.loc[pd.Timestamp("2026-08-25"), "heropening"]
    for dag in ("2026-08-26", "2026-08-27", "2026-08-28"):
        assert vk.loc[pd.Timestamp(dag), "heropening"], dag


def test_de_schoolvakantievlag_blijft_wat_ze_was():
    """De heropening is een toevoeging; de vakantievlag zelf mag er niet door
    verschuiven, anders verandert de correctie die al gebackt is."""
    kal = _kalender("2026-06-01", "2026-09-15", gemeten_tot="2026-07-31")
    vk = prognosekalender(kal).set_index("datum")
    assert vk.loc[pd.Timestamp("2026-07-15"), "schoolvakantie"]
    assert not vk.loc[pd.Timestamp("2026-09-15"), "schoolvakantie"]
