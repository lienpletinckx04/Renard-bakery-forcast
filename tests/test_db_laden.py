"""Tests op de laadlaag. Zonder database: dit zijn pure functies.

Alle data in dit bestand is verzonnen. Er staat geen enkele echte productnaam
en geen enkel echt bedrag in -- ook een test is een plek waar klantdata niet
hoort.
"""
import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij.db.laden import (
    NAAM_ONTBREEKT,
    controleer_kolommen,
    kies_productnaam,
    naar_decimaal,
    onbekende_verwijzingen,
    ontdubbel,
    upsert_sql,
)

# --- controleer_kolommen ----------------------------------------------------


def test_gewone_kolommen_zijn_toegestaan():
    df = pd.DataFrame({"datum": [], "product_id": [], "omzet_excl_btw": []})
    controleer_kolommen(df, "test")  # werpt niet


def test_klantveld_wordt_geweigerd():
    """Harde regel 3, als vangrail in code.

    Niet omdat de huidige extractie dit veld levert -- dat doet ze niet --
    maar omdat een wijziging aan een bron er stil een kolom bij kan zetten.
    """
    df = pd.DataFrame({"datum": [], "partner_id": []})
    with pytest.raises(ValueError, match="partner_id"):
        controleer_kolommen(df, "test")


def test_klantveld_ongeacht_hoofdletters():
    df = pd.DataFrame({"Klantnaam": []})
    with pytest.raises(ValueError, match="klantnaam"):
        controleer_kolommen(df, "test")


def test_alle_verboden_velden_worden_gemeld_niet_alleen_het_eerste():
    df = pd.DataFrame({"partner_id": [], "adres": []})
    with pytest.raises(ValueError) as fout:
        controleer_kolommen(df, "test")
    assert "partner_id" in str(fout.value)
    assert "adres" in str(fout.value)


def test_samengesteld_klantveld_wordt_geweigerd():
    """Stam-matching, niet exacte namen.

    De oude vangrail vergeleek exacte kolomnamen en liet `customer_note` en
    `partner_street` dus door -- precies de vormen waarin een Odoo-bron
    klantvelden aanlevert. Een stam ergens in de naam volstaat om te weigeren.
    """
    for kolom in ("customer_note", "partner_street", "email_adres_klant"):
        with pytest.raises(ValueError, match=kolom):
            controleer_kolommen(pd.DataFrame({kolom: []}), "test")


def test_de_echte_laadkolommen_blijven_toegestaan():
    """De stammen mogen geen kolom raken die de laadpaden echt aanleveren.

    In het bijzonder `omzet_excl_btw`: het kale 'btw' als stam zou de
    omzetkolom zelf weigeren, en daarmee elke laadrun. Dit is de volledige
    kolomlijst uit scripts/db_laad.py, zodat een nieuwe stam die een echte
    kolom raakt hier meteen omvalt.
    """
    kolommen = [
        # dim_kalender
        "datum", "weekdag", "weekdagnaam", "is_weekend", "feestdag",
        "feestdagnaam", "dag_voor_feestdag", "dag_na_feestdag", "brugdag",
        "maand", "weeknr", "dag_van_jaar", "winkel_gemeten", "winkel_open",
        # dim_product en fact_verkoop
        "product_id", "product_naam", "kanaal", "filiaal_id", "aantal",
        "omzet_excl_btw",
        # fact_bonnen, fact_product_uren, fact_kanaalkost
        "bonnen", "eerste_uur", "laatste_uur", "stuks", "bruto_per_stuk",
        "commissie_per_stuk", "inhouding_pct",
    ]
    controleer_kolommen(pd.DataFrame(columns=kolommen), "test")  # werpt niet


# --- naar_decimaal ----------------------------------------------------------


def test_float_wordt_decimal_op_twee_plaatsen():
    uit = naar_decimaal(pd.Series([1.005, 2.0, 3.456]))
    assert list(uit) == [Decimal("1.01"), Decimal("2.00"), Decimal("3.46")]


def test_afronding_is_half_up_en_niet_bankiers():
    """Een boekhouder rekent 2,5 naar 3, niet naar 2.

    Python's standaard is ROUND_HALF_EVEN. Dat is statistisch netter en het
    is niet wat er nagerekend wordt.
    """
    uit = naar_decimaal(pd.Series([0.125, 0.135]), plaatsen="0.01")
    assert list(uit) == [Decimal("0.13"), Decimal("0.14")]


def test_negatieve_bedragen_blijven_negatief():
    """Retours en correcties bestaan; ze mogen niet wegvallen."""
    assert list(naar_decimaal(pd.Series([-1.234]))) == [Decimal("-1.23")]


def test_vier_decimalen_voor_tarieven():
    uit = naar_decimaal(pd.Series([0.12345]), plaatsen="0.0001")
    assert list(uit) == [Decimal("0.1235")]


# --- kies_productnaam -------------------------------------------------------


def _verkoop(product_id, naam, datum):
    return {"product_id": product_id, "product_naam": naam, "datum": datum}


def test_een_product_een_naam():
    df = pd.DataFrame([_verkoop("p1", "Alfa", dt.date(2026, 1, 1))])
    uit = kies_productnaam(df)
    assert list(uit["product_naam"]) == ["Alfa"]


def test_de_jongste_naam_wint():
    """Een hernoeming in de bron mag de historie niet in tweeën splitsen.

    Het scherm toont het assortiment van vandaag, dus de naam van vandaag.
    """
    df = pd.DataFrame([
        _verkoop("p1", "Oude naam", dt.date(2026, 1, 1)),
        _verkoop("p1", "Nieuwe naam", dt.date(2026, 6, 1)),
    ])
    uit = kies_productnaam(df)
    assert list(uit["product_naam"]) == ["Nieuwe naam"]


def test_rijvolgorde_verandert_de_uitkomst_niet():
    """Reproduceerbaarheid: dezelfde bron, dezelfde tabel.

    Een `drop_duplicates` zonder expliciete sortering geeft de eerste rij uit
    het bestand, en dan hangt `dim_product` af van de volgorde waarin de
    extractie toevallig schreef.
    """
    rijen = [
        _verkoop("p1", "Beta", dt.date(2026, 3, 1)),
        _verkoop("p1", "Alfa", dt.date(2026, 3, 1)),
    ]
    heen = kies_productnaam(pd.DataFrame(rijen))
    terug = kies_productnaam(pd.DataFrame(list(reversed(rijen))))
    assert list(heen["product_naam"]) == list(terug["product_naam"]) == ["Alfa"]


def test_meerdere_producten_blijven_gescheiden():
    df = pd.DataFrame([
        _verkoop("p1", "Alfa", dt.date(2026, 1, 1)),
        _verkoop("p2", "Beta", dt.date(2026, 1, 1)),
    ])
    uit = kies_productnaam(df).sort_values("product_id")
    assert list(uit["product_id"]) == ["p1", "p2"]


def test_elk_product_komt_precies_een_keer_voor():
    """`dim_product.product_id` is een primaire sleutel; een dubbel breekt de laadrun."""
    df = pd.DataFrame([
        _verkoop("p1", "Alfa", dt.date(2026, 1, 1)),
        _verkoop("p1", "Beta", dt.date(2026, 2, 1)),
        _verkoop("p1", "Gamma", dt.date(2026, 3, 1)),
    ])
    uit = kies_productnaam(df)
    assert len(uit) == 1
    assert uit["product_id"].is_unique


def test_lege_invoer_geeft_lege_tabel_met_de_juiste_kolommen():
    uit = kies_productnaam(pd.DataFrame(columns=["product_id", "product_naam", "datum"]))
    assert list(uit.columns) == ["product_id", "product_naam"]
    assert uit.empty


def test_een_naamloze_rij_verliest_van_een_rij_met_naam():
    """Heeft hetzelfde product ergens wél een naam, dan wint die."""
    df = pd.DataFrame([
        _verkoop("p1", None, dt.date(2026, 6, 1)),
        _verkoop("p1", "Alfa", dt.date(2026, 1, 1)),
    ])
    assert list(kies_productnaam(df)["product_naam"]) == ["Alfa"]


def test_een_product_dat_nergens_een_naam_heeft_blijft_bestaan():
    """Het mag niet uit dim_product vallen, want dan valt zijn omzet weg.

    Gemeten op de echte data: vier product_id's dragen nergens een naam, samen
    EUR 400,91. Zouden ze verdwijnen, dan moet hun omzet uit fact_verkoop
    geschrapt worden om de refereert-naar-beperking te halen, en dan sluiten
    de kanaaltotalen niet meer aan op de bron.
    """
    df = pd.DataFrame([
        _verkoop("p1", None, dt.date(2026, 1, 1)),
        _verkoop("p2", "Alfa", dt.date(2026, 1, 1)),
    ])
    uit = kies_productnaam(df).sort_values("product_id")
    assert list(uit["product_id"]) == ["p1", "p2"]
    assert list(uit["product_naam"]) == [NAAM_ONTBREEKT, "Alfa"]


def test_de_markering_is_leesbaar_en_geen_technische_sleutel():
    """Deze tekst komt op een scherm, dus geen 'None', 'NaN' of 'UNKNOWN'."""
    assert NAAM_ONTBREEKT == NAAM_ONTBREEKT.strip()
    assert " " in NAAM_ONTBREEKT
    assert "_" not in NAAM_ONTBREEKT
    assert NAAM_ONTBREEKT.lower() not in ("none", "nan", "unknown", "null")


def test_elk_product_id_uit_de_verkopen_komt_in_dim_product():
    """De eigenschap waar de refereert-naar-beperking op steunt."""
    df = pd.DataFrame([
        _verkoop("p1", None, dt.date(2026, 1, 1)),
        _verkoop("p2", "Alfa", dt.date(2026, 2, 1)),
        _verkoop("p3", None, dt.date(2026, 3, 1)),
        _verkoop("p2", "Beta", dt.date(2026, 4, 1)),
    ])
    uit = kies_productnaam(df)
    assert set(uit["product_id"]) == {"p1", "p2", "p3"}
    assert uit["product_id"].is_unique


def test_ontbrekende_kolom_werpt():
    with pytest.raises(ValueError, match="mist kolommen"):
        kies_productnaam(pd.DataFrame({"product_id": ["p1"]}))


# --- upsert_sql -------------------------------------------------------------


def test_upsert_werkt_bij_en_doet_niet_niets():
    """De stille fout die deze test vangt.

    Vergeet je de `do update`, dan doet de tweede run niets: geen fout, geen
    melding, en de cijfers blijven op de stand van gisteren staan.
    """
    sql = upsert_sql("fact_bonnen", ["datum", "filiaal_id", "bonnen"],
                     ["datum", "filiaal_id"])
    assert "on conflict (datum, filiaal_id) do update set" in sql
    assert "bonnen = excluded.bonnen" in sql


def test_sleutelkolommen_worden_niet_bijgewerkt():
    """`set datum = excluded.datum` is zinloos en in sommige gevallen een fout."""
    sql = upsert_sql("fact_bonnen", ["datum", "filiaal_id", "bonnen"],
                     ["datum", "filiaal_id"])
    assert "datum = excluded.datum" not in sql
    assert "filiaal_id = excluded.filiaal_id" not in sql


def test_tabel_zonder_bij_te_werken_kolommen_krijgt_do_nothing():
    """`do update set` zonder kolommen is een syntaxfout."""
    sql = upsert_sql("iets", ["a", "b"], ["a", "b"])
    assert "do nothing" in sql
    assert "do update" not in sql


def test_sleutel_die_niet_in_de_kolommen_staat_werpt():
    with pytest.raises(ValueError, match="sleutelkolommen"):
        upsert_sql("iets", ["a"], ["b"])


def test_zonder_kolommen_werpt():
    with pytest.raises(ValueError, match="zonder kolommen"):
        upsert_sql("iets", [], [])


def test_het_statement_leest_uit_de_tijdelijke_tabel():
    sql = upsert_sql("fact_verkoop", ["datum", "aantal"], ["datum"])
    assert "from tijdelijk_fact_verkoop" in sql
    assert "insert into public.fact_verkoop" in sql


# --- ontdubbel --------------------------------------------------------------


def test_zonder_dubbels_verandert_er_niets():
    df = pd.DataFrame({"k": ["a", "b"], "n": [1, 2]})
    uit, weg = ontdubbel(df, ["k"], ["n"])
    assert weg == 0
    assert len(uit) == 2


def test_dubbele_sleutel_wordt_opgeteld_en_niet_overschreven():
    """De stille fout die dit voorkomt.

    `insert ... on conflict do update` kan een rij niet twee keer in hetzelfde
    statement raken -- Postgres werpt daarop. En zou je per rij schrijven, dan
    wint stilzwijgend de laatste en is de omzet van de andere weg.
    """
    df = pd.DataFrame({"k": ["a", "a"], "n": [3, 4]})
    uit, weg = ontdubbel(df, ["k"], ["n"])
    assert weg == 1
    assert list(uit["n"]) == [7]


def test_ontdubbelen_telt_meerdere_kolommen_tegelijk_op():
    df = pd.DataFrame({"k": ["a", "a"], "aantal": [1, 2], "omzet": [10, 20]})
    uit, _ = ontdubbel(df, ["k"], ["aantal", "omzet"])
    assert list(uit["aantal"]) == [3]
    assert list(uit["omzet"]) == [30]


def test_samengestelde_sleutel():
    df = pd.DataFrame({
        "datum": ["2026-01-01", "2026-01-01", "2026-01-02"],
        "kanaal": ["winkel", "deliveroo", "winkel"],
        "omzet": [1, 2, 4],
    })
    uit, weg = ontdubbel(df, ["datum", "kanaal"], ["omzet"])
    assert weg == 0
    assert len(uit) == 3


def test_ontdubbel_op_lege_tabel():
    df = pd.DataFrame(columns=["k", "n"])
    uit, weg = ontdubbel(df, ["k"], ["n"])
    assert weg == 0
    assert uit.empty


def test_ontdubbel_met_ontbrekende_kolom_werpt():
    with pytest.raises(ValueError, match="mist kolommen"):
        ontdubbel(pd.DataFrame({"k": ["a"]}), ["k"], ["n"])


# --- onbekende_verwijzingen -------------------------------------------------


def test_alles_bekend_geeft_lege_lijst():
    feiten = pd.DataFrame({"datum": ["a", "b"]})
    assert onbekende_verwijzingen(feiten, "datum", pd.Series(["a", "b", "c"])) == []


def test_ontbrekende_verwijzing_wordt_gemeld():
    """Zonder deze controle valt de transactie om op een Postgres-melding
    die niet zegt wélke rij het probleem is."""
    feiten = pd.DataFrame({"datum": ["a", "z"]})
    assert onbekende_verwijzingen(feiten, "datum", pd.Series(["a"])) == ["z"]


def test_ontbrekende_verwijzingen_zijn_uniek_en_gesorteerd():
    feiten = pd.DataFrame({"p": ["z", "y", "z"]})
    assert onbekende_verwijzingen(feiten, "p", pd.Series([])) == ["y", "z"]


def test_lege_feitentabel_geeft_lege_lijst():
    assert onbekende_verwijzingen(pd.DataFrame(columns=["p"]), "p", pd.Series([])) == []
