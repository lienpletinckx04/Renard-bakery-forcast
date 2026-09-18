"""Tests op de beslislaag. Dit is de rekenkern, dus hier hoort de dekking te zitten."""

import pytest

from bakkerij.decide.newsvendor import (
    Economie,
    bakaantal,
    kost_van_beslissing,
)

KWANTIELEN = {0.1: 20.0, 0.25: 28.0, 0.5: 38.0, 0.75: 46.0, 0.9: 55.0, 0.95: 62.0}


def test_kritiek_percentiel_boven_helft_bij_hoge_marge():
    """Hoge marge, lage productiekost: je bakt bewust boven de mediaan."""
    e = Economie(verkoopprijs=2.40, productiekost=0.80)
    assert e.kost_te_weinig == pytest.approx(1.60)
    assert e.kost_te_veel == pytest.approx(0.80)
    assert e.kritiek_percentiel == pytest.approx(2 / 3)


def test_tgtg_verhoogt_het_optimum():
    """De kern van het project: restwaarde verschuift het optimum omhoog.

    Too Good To Go is geen opruimkanaal maar een instelknop.
    """
    zonder = Economie(verkoopprijs=2.40, productiekost=0.80, restwaarde=0.0)
    met = Economie(verkoopprijs=2.40, productiekost=0.80, restwaarde=0.50)
    assert met.kritiek_percentiel > zonder.kritiek_percentiel
    assert bakaantal(KWANTIELEN, met) > bakaantal(KWANTIELEN, zonder)


def test_kanaalcommissie_verlaagt_het_optimum():
    """Deliveroo-commissie eet de marge, dus wordt een gemiste verkoop minder erg."""
    winkel = Economie(verkoopprijs=2.40, productiekost=0.80)
    deliveroo = Economie(verkoopprijs=2.40, productiekost=0.80, kanaalcommissie=0.30)
    assert deliveroo.kritiek_percentiel < winkel.kritiek_percentiel


def test_bakaantal_respecteert_veelvoud_en_minimum():
    e = Economie(verkoopprijs=2.40, productiekost=0.80)
    assert bakaantal(KWANTIELEN, e, veelvoud=12) % 12 == 0
    assert bakaantal({0.5: 1.0, 0.9: 2.0}, e, minimum=10) >= 10


def test_bakaantal_interpoleert_tussen_kwantielen():
    e = Economie(verkoopprijs=2.0, productiekost=1.0)  # q* = 0.5
    assert bakaantal(KWANTIELEN, e) == 38


def test_kost_asymmetrie():
    """Te weinig moet duurder zijn dan te veel bij een hoge marge."""
    e = Economie(verkoopprijs=2.40, productiekost=0.80)
    te_veel = kost_van_beslissing(gebakken=50, werkelijke_vraag=40, economie=e)
    te_weinig = kost_van_beslissing(gebakken=30, werkelijke_vraag=40, economie=e)
    assert te_weinig > te_veel
    assert kost_van_beslissing(40, 40, e) == 0


def test_restwaarde_boven_productiekost_wordt_geweigerd():
    """Anders is overproduceren winstgevend en loopt het model op hol."""
    with pytest.raises(ValueError):
        Economie(verkoopprijs=2.0, productiekost=0.5, restwaarde=0.9)
