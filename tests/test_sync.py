"""De poortwachter van de nachtelijke sync (bakkerij/db/sync.py).

Gedrag, geen implementatie: elke test zegt wat de sync in een situatie moet
doen, niet hoe de vergelijking geschreven is.
"""
import datetime as dt

import pytest

from bakkerij.db.sync import beslis_sync

UTC = dt.UTC


def _t(uur: int, dag: int = 15) -> dt.datetime:
    return dt.datetime(2026, 8, dag, uur, 0, tzinfo=UTC)


def test_eerste_run_draait_altijd():
    besluit = beslis_sync(jongste_wijziging=_t(6), laatste_geslaagde_run=None)
    assert besluit.draaien


def test_wijzigingen_na_de_vorige_run_starten_een_run():
    besluit = beslis_sync(jongste_wijziging=_t(9),
                          laatste_geslaagde_run=_t(3))
    assert besluit.draaien


def test_niets_gewijzigd_sinds_de_vorige_run_slaat_over():
    # De zomersluiting: Odoo staat stil, de sync hoort dat te zien en de
    # database met rust te laten in plaats van elke nacht alles te herladen.
    besluit = beslis_sync(jongste_wijziging=_t(9, dag=1),
                          laatste_geslaagde_run=_t(3, dag=15))
    assert not besluit.draaien
    assert "geen wijzigingen" in besluit.reden


def test_een_wijziging_tijdens_de_vorige_run_valt_binnen_de_marge():
    # Een order die binnenkwam terwijl de vorige run al bezig was: de
    # write_date ligt dan nét vóór de starttijd van die run. Zonder marge zou
    # die order permanent tussen wal en schip vallen.
    besluit = beslis_sync(jongste_wijziging=_t(3) - dt.timedelta(minutes=30),
                          laatste_geslaagde_run=_t(3))
    assert besluit.draaien


def test_lege_bron_draait_niet_maar_meldt_het():
    besluit = beslis_sync(jongste_wijziging=None, laatste_geslaagde_run=_t(3))
    assert not besluit.draaien
    assert "na te kijken" in besluit.reden


def test_naieve_tijden_worden_geweigerd():
    # Odoo geeft UTC zonder aanduiding; wie dat vergeet te labelen vergelijkt
    # appels met peren. Python weigert dat, en dat hoort hardop te gebeuren
    # in plaats van stil in een except te verdwijnen.
    naief = dt.datetime(2026, 8, 15, 9, 0)  # noqa: DTZ001 - het foute geval zelf
    with pytest.raises(TypeError):
        beslis_sync(jongste_wijziging=naief, laatste_geslaagde_run=_t(3))
