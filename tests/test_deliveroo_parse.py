"""Tests op de Deliveroo-parser.

Tot 18 september 2026 stond hier geen nagebouwde CSV-tekst, met een reden: de
vorm van de echte export was onbekend, en een test op een bedachte kopregel
bewijst alleen dat de parser de verzinner begrijpt. Die reden is vervallen --
de opdrachtgever leverde 23 downloads uit Partner Hub, september 2025 t/m
september 2026 -- dus de ordertests hieronder draaien op de kopregel van die
échte bestanden, letterlijk overgenomen.

`parse_items_sold` blijft weigeren, en dat is geen half werk. Dat rapport
draagt geen datum en geen bestelnummer: het telt op over de hele
downloadperiode. Het heeft dus een ontwerpbeslissing nodig (hoe verdeel je een
periodetotaal over dagen) en geen parser, en die beslissing hoort niet in een
commit die "de parser is af" heet.
"""
import datetime
from decimal import Decimal

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


def test_items_sold_weigert_luid_zolang_er_geen_lezer_is():
    """Geen stille lege lijst: wie dit aanroept, moet het merken."""
    with pytest.raises(NotImplementedError) as fout:
        parse_items_sold("wat voor tekst dan ook")
    # De melding moet de weg wijzen, niet alleen 'nog niet gebouwd' zeggen.
    assert "Partner Hub" in str(fout.value)


# --- parse_orders, op de echte kopregel -------------------------------------

KOP = ("Naam restaurant,Bestelnummer,Bestelstatus,Datum ingediend,"
       "Tijdstip ingediend,Bezorgdatum,Tijdstip bezorging,Subtotaal,"
       "Deliveroo-commissie,Btw op Deliveroo-commissie")


def test_orders_leest_een_afgeronde_bestelling():
    tekst = KOP + "\n" + (
        "Renard Bakery Ixelles,6549,Afgerond,2026-09-02,18:28:46,"
        "2026-09-02,18:59:32,35.1,7.02,1.47"
    )
    regels = parse_orders(tekst)
    assert len(regels) == 1
    r = regels[0]
    assert r.datum == D(2026, 9, 2)
    assert r.store_id == "Renard Bakery Ixelles"
    assert r.order_id == "6549"
    assert r.subtotaal == Decimal("35.1")
    assert r.commissie == Decimal("7.02")
    assert r.btw_op_commissie == Decimal("1.47")


def test_orders_telt_een_geannuleerde_bestelling_niet_als_omzet():
    """De meting die deze filter afdwong: 76 niet-afgeronde bestellingen over
    twaalf maanden dragen samen EUR 1.885,25 subtotaal en nul commissie.
    Meetellen overschat de omzet en verlaagt het commissiepercentage."""
    afgerond = ("Renard Bakery Ixelles,1,Afgerond,2026-09-02,10:00:00,"
                "2026-09-02,10:30:00,20.00,4.00,0.84")
    geannuleerd = ("Renard Bakery Ixelles,2,Geannuleerd,2026-09-02,11:00:00,"
                   "2026-09-02,11:30:00,27.60,0,0")
    tekst = f"{KOP}\n{afgerond}\n{geannuleerd}"
    assert [r.order_id for r in parse_orders(tekst)] == ["1"]


def test_orders_laat_elke_onbekende_status_vallen():
    """Witte lijst, geen zwarte: een status die Deliveroo er morgen bij
    verzint, mag geen stille omzet worden."""
    tekst = KOP + "\n" + (
        "Renard Bakery Uccle,3,Iets Nieuws Van Deliveroo,2026-09-02,"
        "10:00:00,2026-09-02,10:30:00,99.00,19.80,4.16"
    )
    assert parse_orders(tekst) == []


def test_orders_weigert_een_export_zonder_commissiekolom():
    """Een leverancier die een kolom hernoemt, mag geen leeg kwartaal
    opleveren dat niemand opvalt."""
    tekst = KOP.replace(",Deliveroo-commissie", ",Commission") + "\n" + (
        "Renard Bakery Ixelles,1,Afgerond,2026-09-02,10:00:00,"
        "2026-09-02,10:30:00,20.00,4.00,0.84"
    )
    with pytest.raises(DeliverooFormaatFout, match="Deliveroo-commissie"):
        parse_orders(tekst)


def test_orders_weigert_een_datum_die_geen_iso_is():
    """Geen eigen datumraadwerk: 05/03 en 03/05 zijn allebei geldig en geen
    enkele parser ziet het verschil."""
    tekst = KOP + "\n" + (
        "Renard Bakery Ixelles,1,Afgerond,02/09/2026,10:00:00,"
        "2026-09-02,10:30:00,20.00,4.00,0.84"
    )
    with pytest.raises(DeliverooFormaatFout, match="ISO-datum"):
        parse_orders(tekst)


def test_orders_leest_een_leeg_bedrag_als_nul():
    """Komt voor bij de commissie; leeg is nul en geen fout."""
    tekst = KOP + "\n" + (
        "Renard Bakery Ixelles,1,Afgerond,2026-09-02,10:00:00,"
        "2026-09-02,10:30:00,20.00,,"
    )
    r = parse_orders(tekst)[0]
    assert r.commissie == Decimal(0)
    assert r.btw_op_commissie == Decimal(0)


def test_orders_weigert_een_bedrag_dat_geen_getal_is():
    tekst = KOP + "\n" + (
        "Renard Bakery Ixelles,1,Afgerond,2026-09-02,10:00:00,"
        "2026-09-02,10:30:00,twintig euro,4.00,0.84"
    )
    with pytest.raises(DeliverooFormaatFout, match="geen bedrag"):
        parse_orders(tekst)


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
