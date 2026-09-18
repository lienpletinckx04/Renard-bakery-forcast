"""Tests op het skelet van de Deliveroo-parser.

Er staat hier geen nagebouwde CSV-tekst in, anders dan bij de TGTG-tests. Dat
is geen luiheid maar dezelfde beslissing als in de module zelf: de vorm van de
echte export is onbekend, en een test op een bedachte kopregel bewijst alleen
dat de parser de verzinner begrijpt. Wat hier getest wordt zijn de twee
controles die niet van de documentvorm afhangen -- het bereik uit de mapnaam en
de dag/maand-vanger -- plus de belofte dat het lezen zelf luid weigert in
plaats van stil niets te doen.
"""
import datetime

import pytest

from bakkerij.sources.deliveroo_parse import (
    DeliverooFormaatFout,
    bereik_uit_pad,
    gaten_in_dekking,
    klopt_met_bereik,
    parse_items_sold,
    parse_orders,
)

D = datetime.date


def test_lezen_weigert_luid_zolang_er_geen_bron_is():
    """Geen stille lege lijst: wie dit aanroept, moet het merken."""
    for lezer in (parse_items_sold, parse_orders):
        with pytest.raises(NotImplementedError) as fout:
            lezer("wat voor tekst dan ook")
        # De melding moet de weg wijzen, niet alleen 'nog niet gebouwd' zeggen.
        assert "Partner Hub" in str(fout.value)


def test_bereik_uit_pad_leest_de_mapnaam():
    pad = "data/raw/Deliveroo/2025-08-25_2025-11-22/orders.csv"
    assert bereik_uit_pad(pad) == (D(2025, 8, 25), D(2025, 11, 22))


def test_bereik_uit_pad_zonder_map_is_geen_fout():
    """None betekent 'de map draagt geen bereik'; de aanroeper beslist."""
    assert bereik_uit_pad("data/raw/Deliveroo/orders.csv") is None


def test_bereik_uit_pad_weigert_een_omgekeerd_bereik():
    """Een bereik dat achteruit loopt is een typefout in een mapnaam."""
    with pytest.raises(DeliverooFormaatFout, match="achteruit"):
        bereik_uit_pad("data/raw/Deliveroo/2025-11-22_2025-08-25/orders.csv")


def test_bereik_uit_pad_weigert_een_onbestaande_datum():
    with pytest.raises(DeliverooFormaatFout, match="geldige datums"):
        bereik_uit_pad("data/raw/Deliveroo/2025-02-30_2025-03-15/orders.csv")


def test_klopt_met_bereik_laat_de_reeks_ongemoeid():
    datums = [D(2025, 8, 25), D(2025, 9, 1), D(2025, 11, 22)]
    assert klopt_met_bereik(datums, D(2025, 8, 25), D(2025, 11, 22)) == datums


def test_klopt_met_bereik_betrapt_de_dag_maand_omwisseling():
    """De hele reden dat deze functie bestaat.

    Een export over 25 augustus tot 22 november die als eerste datum
    3 mei oplevert, is een export waarvan de datums omgedraaid gelezen zijn.
    """
    datums = [D(2025, 9, 3), D(2025, 5, 9)]
    with pytest.raises(DeliverooFormaatFout, match="dag/maand"):
        klopt_met_bereik(datums, D(2025, 8, 25), D(2025, 11, 22))


def test_klopt_met_bereik_noemt_hoeveel_er_buiten_vallen():
    """Eén dag ernaast en negentig dagen ernaast zijn twee verschillende
    verhalen; de melding moet het verschil dragen."""
    datums = [D(2025, 8, 25), D(2026, 1, 1), D(2026, 1, 2)]
    with pytest.raises(DeliverooFormaatFout, match="2 van 3"):
        klopt_met_bereik(datums, D(2025, 8, 25), D(2025, 11, 22))


def test_gaten_in_dekking_vindt_de_ontbrekende_dagen():
    bereiken = [(D(2025, 1, 1), D(2025, 3, 31)),
                (D(2025, 5, 1), D(2025, 7, 31))]
    assert gaten_in_dekking(bereiken) == [(D(2025, 4, 1), D(2025, 4, 30))]


def test_gaten_in_dekking_ziet_aansluitende_blokken_niet_als_gat():
    bereiken = [(D(2025, 1, 1), D(2025, 3, 31)),
                (D(2025, 4, 1), D(2025, 6, 30))]
    assert gaten_in_dekking(bereiken) == []


def test_gaten_in_dekking_verdraagt_overlap():
    """Overlappende downloads zijn normaal: de ontdubbeling gebeurt later."""
    bereiken = [(D(2025, 1, 1), D(2025, 4, 15)),
                (D(2025, 3, 1), D(2025, 6, 30))]
    assert gaten_in_dekking(bereiken) == []


def test_gaten_in_dekking_is_leeg_bij_niets():
    assert gaten_in_dekking([]) == []
