"""De censureringsmeting (O8/O11) op synthetische data.

Elke test pint één valkuil vast die de eerste versie van de meting echt had:
schaarse aankopen die op een leeg rek lijken, de korte zondag die tegen een
vaste sluittijd als uitverkoop leest, gewoonteproducten in de ondergrens, en
een referentie op te weinig dagen.
"""
import datetime as dt

import pandas as pd
import pytest

from bakkerij import censurering as cz


def _uren(rijen):
    return pd.DataFrame(rijen, columns=cz.KOLOMMEN)


def _reeks(product_id, laatste_uren, bonnen=20, start=dt.date(2025, 3, 1)):
    """Eén rij per dag voor een product. `bonnen` mag een lijst zijn."""
    if isinstance(bonnen, int):
        bonnen = [bonnen] * len(laatste_uren)
    return [
        (start + dt.timedelta(days=i), product_id, 7, uur, b)
        for i, (uur, b) in enumerate(zip(laatste_uren, bonnen))
    ]


def test_sluitproxy_is_het_maximum_over_de_dag():
    uren = _uren(_reeks(1, [17, 17]) + _reeks(2, [10, 16]))
    proxy = cz.sluitproxy_per_dag(uren)
    assert proxy[dt.date(2025, 3, 1)] == 17
    assert proxy[dt.date(2025, 3, 2)] == 17


def test_uitverkochte_drukke_dag_geeft_het_signaal():
    # 40 drukke dagen tot 17u, 10 drukke dagen om 10u op: p90 = 17, de vroege
    # dagen vlaggen. Product 9 houdt de winkelproxy op 17u — met één product
    # zou de proxy meezakken naar het product zelf.
    uren = _uren(_reeks(1, [17] * 40 + [10] * 10) + _reeks(9, [17] * 50))
    m = cz.meet(uren)
    assert m.loc[1, "dagen"] == 50
    assert m.loc[1, "dagen_gewogen"] == 50
    assert m.loc[1, "referentie_uur"] == 17
    assert m.loc[1, "gecensureerd"] == pytest.approx(0.2)


def test_schaarse_aankopen_zijn_geen_leeg_rek():
    # Hetzelfde uurpatroon, maar de vroege dagen hebben maar 3 bonnen: een
    # traag product, geen uitverkoop. Geen enkel signaal.
    uren = _uren(
        _reeks(1, [17] * 40 + [10] * 10, bonnen=[20] * 40 + [3] * 10)
        + _reeks(9, [17] * 50)
    )
    m = cz.meet(uren)
    assert m.loc[1, "dagen"] == 50
    assert m.loc[1, "dagen_gewogen"] == 40
    assert m.loc[1, "gecensureerd"] == pytest.approx(0.0)


def test_korte_zondag_is_geen_uitverkoop():
    # De hele winkel stopt op dag 41-50 om 13u (korte dag). Product 1 stopt
    # mee om 13u: referentie 17, dus vroeg t.o.v. zichzelf — maar niet vroeg
    # t.o.v. de winkel van die dag. Geen signaal.
    uren = _uren(
        _reeks(1, [17] * 40 + [13] * 10) + _reeks(9, [17] * 40 + [13] * 10)
    )
    m = cz.meet(uren)
    assert m.loc[1, "gecensureerd"] == pytest.approx(0.0)
    assert m.loc[1, "bovengrens"] == pytest.approx(0.0)


def test_ochtendproduct_telt_alleen_in_de_bovengrens():
    # Product 2 verkoopt áltijd druk tot 10u terwijl de winkel tot 17u draait:
    # gewoonte of censurering is niet te onderscheiden. Bovengrens 100%,
    # ondergrens 0% — de waarheid ligt ertussen en het rapport zegt dat.
    uren = _uren(_reeks(1, [17] * 40) + _reeks(2, [10] * 40))
    m = cz.meet(uren)
    assert m.loc[2, "bovengrens"] == pytest.approx(1.0)
    assert m.loc[2, "gecensureerd"] == pytest.approx(0.0)


def test_te_weinig_drukke_dagen_geeft_geen_referentie():
    uren = _uren(_reeks(1, [17] * 40) + _reeks(2, [10, 16, 17]))
    m = cz.meet(uren)
    assert pd.isna(m.loc[2, "referentie_uur"])
    assert pd.isna(m.loc[2, "gecensureerd"])
    # De bovengrens werkt wel: alleen de 10u-dag ligt >= 2u voor sluit.
    assert m.loc[2, "bovengrens"] == pytest.approx(1 / 3)


def test_gesloten_dagen_tellen_niet_mee():
    dagen = _reeks(1, [17] * 10)
    open_dagen = {r[0] for r in dagen[:7]}
    m = cz.meet(_uren(dagen), open_dagen=open_dagen, min_dagen=5)
    assert m.loc[1, "dagen"] == 7


def test_drempel_scheidt_ruis_van_leeg_rek():
    # Eén uur onder de referentie is ruis (drukte golft), twee uur niet.
    uren = _uren(_reeks(1, [17] * 40 + [16, 15]) + _reeks(9, [17] * 42))
    m = cz.meet(uren)
    assert m.loc[1, "gecensureerd"] == pytest.approx(1 / 42)


def test_ontbrekende_kolom_faalt_luid():
    with pytest.raises(ValueError, match="mist kolommen"):
        cz.meet(pd.DataFrame({"datum": [], "product_id": []}))


def test_samenvatting_weegt_naar_gewogen_dagen_en_telt_structureel():
    uren = _uren(
        _reeks(1, [17] * 40 + [10] * 10)  # 20% gecensureerd: structureel
        + _reeks(2, [17] * 50)  # nooit
    )
    s = cz.samenvatting(cz.meet(uren))
    assert s["producten"] == 2
    assert s["productdagen"] == 100
    assert s["productdagen_gewogen"] == 100
    assert s["aandeel_gecensureerd"] == pytest.approx(0.1)
    assert s["structureel_gecensureerde_producten"] == 1


def test_lege_invoer_geeft_lege_meting():
    m = cz.meet(_uren([]), open_dagen=set())
    assert m.empty
    s = cz.samenvatting(m)
    assert s["producten"] == 0
    assert pd.isna(s["aandeel_bovengrens"])
