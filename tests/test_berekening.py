"""Tests voor de berekeningslaag.

Alle fixtures zijn verzonnen. Geen enkele rij komt uit klantdata.

De tests bewaken vooral de dingen die stil fout gaan: sluitingsdagen die als nul
meetellen, een jaar-op-jaarvergelijking over ongelijke periodes, een product dat
uit een groepering verdwijnt omdat het geen naam heeft, en een bandbreedte die
niet uit de backtest komt.
"""
import datetime
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij import berekening as bk
from bakkerij import canoniek

MAANDAGEN = ["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27",
             "2025-02-03", "2025-02-10", "2025-02-17", "2025-02-24",
             "2025-03-03", "2025-03-10"]


def _verkopen(rijen) -> pd.DataFrame:
    """rijen: (datum, product_id, naam, kanaal, aantal, omzet)."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": "Kassa 1",
          "product_id": p, "product_naam": n, "kanaal": k,
          "aantal": a, "omzet_excl_btw": o}
         for d, p, n, k, a, o in rijen]
    )


def _dagen(omzetten, start="2025-01-01", kanaal="winkel") -> pd.DataFrame:
    """Eén rij per opeenvolgende dag, met de opgegeven dagomzet."""
    datums = pd.date_range(start, periods=len(omzetten), freq="D")
    return _verkopen([
        (d.date().isoformat(), "10", "Brood", kanaal, 1.0, o)
        for d, o in zip(datums, omzetten, strict=True)
    ])


# --- euro -------------------------------------------------------------------

def test_euro_rondt_af_op_centen_half_naar_boven():
    assert bk.euro(1.005) == Decimal("1.01")
    assert bk.euro(2.344) == Decimal("2.34")
    assert isinstance(bk.euro(3.0), Decimal)


# --- sluitingsdagen ---------------------------------------------------------

def test_open_verkopen_gooit_de_bon_van_een_sluitingsdag_eruit():
    """De koppeling met de drempelregel uit canoniek.py.

    Tien maandagen, negen normaal en één met € 0,50: die laatste is een
    sluitingsdag met één losse bon en mag niet in de berekening belanden.
    """
    winkel = _verkopen([
        (d, "10", "Brood", "winkel", 1.0, o)
        for d, o in zip(MAANDAGEN, [1000.0] * 9 + [0.50], strict=True)
    ])
    kal = canoniek.bouw_kalender(winkel)
    uit = bk.open_verkopen(winkel, kal)
    assert len(uit) == 9
    assert pd.Timestamp("2025-03-10") not in set(uit["datum"])


def test_gemiddelde_dagomzet_rekent_sluitingsdagen_niet_mee():
    """Zonder deze regel is elk gemiddelde te laag, en niemand ziet waarom."""
    winkel = _verkopen([
        (d, "10", "Brood", "winkel", 1.0, o)
        for d, o in zip(MAANDAGEN, [1000.0] * 9 + [0.50], strict=True)
    ])
    kal = canoniek.bouw_kalender(winkel)
    totalen = bk.dagtotalen(bk.open_verkopen(winkel, kal))
    tot = bk.peildatum(bk.open_verkopen(winkel, kal))
    cijfers = {c.label: c for c in bk.kerncijfers(totalen, tot)}
    gem = cijfers["Gemiddelde dagomzet"]
    assert gem.waarde == Decimal("1000.00")


# --- dagtotalen en peildatum ------------------------------------------------

def test_dagtotalen_telt_per_datum_en_kanaal():
    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 2.0, 6.0),
        ("2025-01-06", "11", "Koek", "winkel", 1.0, 4.0),
        ("2025-01-06", "70", "Pakket", "tgtg", 1.0, 3.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    uit = bk.dagtotalen(bk.open_verkopen(verkopen, kal)).set_index("kanaal")
    assert uit.loc["winkel", "omzet"] == pytest.approx(10.0)
    assert uit.loc["winkel", "stuks"] == pytest.approx(3.0)
    assert uit.loc["tgtg", "omzet"] == pytest.approx(3.0)


def test_peildatum_is_de_laatste_gemeten_dag_en_niet_vandaag():
    verkopen = _dagen([100.0] * 10)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    assert bk.peildatum(open_v) == pd.Timestamp("2025-01-10")


def test_peildatum_zonder_data_faalt_luid():
    verkopen = _dagen([100.0] * 5, kanaal="tgtg")
    kal = canoniek.bouw_kalender(verkopen)
    with pytest.raises(ValueError, match="Geen gemeten dagen"):
        bk.peildatum(bk.open_verkopen(verkopen, kal), "winkel")


# --- venster en jaar-op-jaar ------------------------------------------------

def test_venster_neemt_de_laatste_n_open_dagen():
    verkopen = _dagen([100.0] * 40)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    v = bk.venster(totalen, pd.Timestamp("2025-02-09"), 7)
    assert v.dagen == 7
    assert v.van == pd.Timestamp("2025-02-03")
    assert v.tot == pd.Timestamp("2025-02-09")


def test_venster_zonder_vorig_jaar_is_niet_volledig():
    """En dan hoort er geen percentage te verschijnen."""
    verkopen = _dagen([100.0] * 40)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    v = bk.venster(totalen, pd.Timestamp("2025-02-09"), 7)
    assert v.vorig_dagen == 0
    assert v.vorig_volledig is False


def test_kerncijfer_laat_het_verschil_weg_als_vorig_jaar_ontbreekt():
    verkopen = _dagen([100.0] * 40)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    cijfers = bk.kerncijfers(totalen, pd.Timestamp("2025-02-09"))
    week = next(c for c in cijfers if "7 open dagen" in c.label)
    assert week.verschil_pct is None
    assert week.richting is None
    # De toelichting moet zeggen waarom er geen vergelijking is, niet zwijgen.
    assert "scheef" in week.toelichting
    assert "0 open dagen" in week.toelichting


def test_geen_enkel_kerncijfer_vergelijkt_als_vorig_jaar_ontbreekt():
    """De wacht geldt voor alle vier, niet voor drie.

    Tot 18 aug 2026 rekende "Gemiddelde dagomzet" zijn percentage kaal uit,
    terwijl de andere drie zwegen. Op het scherm stond dan een pijl omhoog
    naast drie cijfers die zeiden dat vergelijken niet kon. Deze test bestaat
    om dat verschil nooit meer te laten ontstaan -- ook niet voor een vijfde
    kerncijfer dat er later bij komt.
    """
    verkopen = _dagen([100.0] * 40)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    cijfers = bk.kerncijfers(totalen, pd.Timestamp("2025-02-09"))

    assert len(cijfers) == 4
    for c in cijfers:
        assert c.verschil_pct is None, f"{c.label} vergelijkt met een leeg jaar"
        assert c.richting is None, f"{c.label} toont een richting zonder grond"
        # Harde regel 8: onbeschikbaar mét reden, nooit stilzwijgend weggelaten.
        assert "scheef" in c.toelichting, f"{c.label} zwijgt over het waarom"


def test_de_jaarschuif_legt_dezelfde_weekdag_naast_elkaar():
    """364 en niet 365: anders komt zaterdag naast vrijdag te liggen.

    In een bakkerij is de weekdag de sterkste verklarende variabele die er is.
    Een schuif die geen veelvoud van zeven is, zet een structurele fout in élk
    jaar-op-jaarcijfer -- gemeten bijna vijf procentpunt op het maandcijfer.
    """
    assert bk.JAARSCHUIF == pd.Timedelta(days=364)

    verkopen = _dagen([100.0] * 40)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    v = bk.venster(totalen, pd.Timestamp("2025-02-09"), 7)

    assert v.tot.weekday() == v.vorig_tot.weekday()
    assert v.van.weekday() == v.vorig_van.weekday()


def test_maandomzet_geeft_het_aantal_open_dagen_mee():
    """Nodig om te weten of twee staven naast elkaar mogen staan."""
    verkopen = _dagen([100.0] * 45)  # jan volledig, feb deels
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    per = bk.maandomzet(totalen).set_index(["jaar", "maand"])
    assert per.loc[(2025, 1), "open_dagen"] == 31
    assert per.loc[(2025, 2), "open_dagen"] == 14


# --- kanalen en producten ---------------------------------------------------

def test_kanaalverdeling_telt_op_tot_honderd_procent():
    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 1.0, 75.0),
        ("2025-01-06", "70", "Pakket", "tgtg", 1.0, 25.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    per = bk.kanaalverdeling(totalen, pd.Timestamp("2025-01-06")).set_index("kanaal")
    assert per.loc["winkel", "aandeel_pct"] == pytest.approx(75.0)
    assert per.loc["tgtg", "aandeel_pct"] == pytest.approx(25.0)


def test_topproducten_rangschikt_op_omzet():
    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 10.0, 30.0),
        ("2025-01-06", "11", "Taart", "winkel", 2.0, 60.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    top = bk.topproducten(bk.open_verkopen(verkopen, kal), pd.Timestamp("2025-01-06"))
    assert list(top["product_naam"]) == ["Taart", "Brood"]


def test_omzet_per_groep_verliest_geen_omzet_aan_een_ontbrekende_categorie():
    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 1.0, 60.0),
        ("2025-01-06", "99", "Onbekend", "winkel", 1.0, 40.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    groepen = pd.Series({"10": "Brood"})
    per = bk.omzet_per_groep(
        bk.open_verkopen(verkopen, kal), groepen, pd.Timestamp("2025-01-06")
    ).set_index("groep")
    assert per.loc["Overige", "omzet"] == pytest.approx(40.0)
    assert float(per["omzet"].sum()) == pytest.approx(100.0)


def test_topproducten_verliest_geen_product_zonder_naam():
    """Groeperen op (id, naam) gooit met de standaard dropna elke naamloze rij
    weg. In de echte data zijn dat 4 producten; die mogen niet verdwijnen."""
    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 1.0, 60.0),
        ("2025-01-06", "77", None, "winkel", 1.0, 40.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    top = bk.topproducten(bk.open_verkopen(verkopen, kal), pd.Timestamp("2025-01-06"))
    assert set(top["product_id"]) == {"10", "77"}
    assert float(top["omzet"].sum()) == pytest.approx(100.0)
    naamloos = top[top["product_id"] == "77"].iloc[0]
    # Geen verzonnen naam in de berekeningslaag: het label ontbreekt, het cijfer niet.
    assert pd.isna(naamloos["product_naam"])
    assert float(naamloos["aandeel_pct"]) == pytest.approx(40.0)


def test_productdekking_neemt_ook_een_product_zonder_naam_mee():
    """Juist bij dekking mag niets wegvallen: deze tabel bepaalt of een product
    voorspelbaar is."""
    rijen = [(d, "10", "Brood", "winkel", 1.0, 10.0) for d in MAANDAGEN]
    rijen += [(d, "77", None, "winkel", 1.0, 5.0) for d in MAANDAGEN]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    dekking = bk.productdekking(
        bk.open_verkopen(verkopen, kal), kal
    ).set_index("product_id")
    assert "77" in dekking.index
    assert bool(dekking.loc["77", "kern"]) is True


def test_productdekking_markeert_de_kernproducten():
    # Product 10 verkoopt elke dag, product 11 op één van de tien.
    rijen = [(d, "10", "Brood", "winkel", 1.0, 10.0) for d in MAANDAGEN]
    rijen.append((MAANDAGEN[0], "11", "Seizoen", "winkel", 1.0, 5.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    dekking = bk.productdekking(
        bk.open_verkopen(verkopen, kal), kal
    ).set_index("product_id")
    assert bool(dekking.loc["10", "kern"]) is True
    assert bool(dekking.loc["11", "kern"]) is False


# De prognosetests stonden hier tot 18 augustus 2026: ze testten
# `berekening.residu_kwantielen` en `berekening.prognose`, een tweede
# prognosepad zonder productie-aanroepers. Dat pad is verwijderd; het echte
# pad (kalibreer_kwantielen + band_naar_prognose) test tests/test_rolling.py.

# --- as-ticks ---------------------------------------------------------------

def test_as_ticks_begint_op_nul_en_reikt_boven_het_maximum():
    ticks = bk.as_ticks(12748.0)
    assert ticks[0] == 0
    assert ticks[-1] >= 12748.0
    assert len(ticks) >= 3


def test_as_ticks_op_nul_valt_niet_om():
    assert bk.as_ticks(0.0) == [0.0, 1.0]


# --- periodecontext ---------------------------------------------------------

def test_periodecontext_geeft_totaal_gemiddelde_en_beste_dag():
    """Twintig dagen: tien van 100 en dan tien van 200, met één uitschieter."""
    omzetten = [100.0] * 10 + [200.0] * 9 + [350.0]
    verkopen = _dagen(omzetten)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    ctx = bk.periodecontext(totalen, pd.Timestamp("2025-01-20"), dagen=10)
    assert ctx.totaal == Decimal("2150.00")
    assert ctx.gemiddelde == Decimal("215.00")
    assert ctx.beste_datum == pd.Timestamp("2025-01-20")
    assert ctx.beste_omzet == Decimal("350.00")
    # vorige periode: tien dagen van 100 (totaal 1000) -> +115%
    assert ctx.verschil_pct == Decimal("115.0")
    assert ctx.richting == "op"


def test_periodecontext_zonder_volledige_vorige_periode_geen_percentage():
    """Twaalf dagen historiek en een venster van tien: de vorige periode telt
    er maar twee, dus geen vergelijking en zeker geen nul."""
    verkopen = _dagen([100.0] * 12)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    ctx = bk.periodecontext(totalen, pd.Timestamp("2025-01-12"), dagen=10)
    assert ctx.vorig_dagen == 2
    assert ctx.verschil_pct is None
    assert ctx.richting is None


# --- weekdagprofiel ---------------------------------------------------------

def test_weekdagprofiel_middelt_per_weekdag():
    """Vier weken met een vast patroon: maandag 100, dinsdag 300, rest 200."""
    omzetten = []
    for _ in range(4):
        omzetten += [100.0, 300.0] + [200.0] * 5
    verkopen = _dagen(omzetten, start="2025-01-06")  # 6 jan 2025 is een maandag
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    profiel = bk.weekdagprofiel(totalen, pd.Timestamp("2025-02-02"), weken=4)
    per = profiel.set_index("weekdag")
    assert per.loc[0, "gemiddelde"] == 100.0
    assert per.loc[1, "gemiddelde"] == 300.0
    assert per.loc[6, "gemiddelde"] == 200.0
    assert (per["meetdagen"] == 4).all()


def test_weekdagprofiel_toont_geen_staaf_voor_een_dag_zonder_meting():
    """Een vaste sluitingsdag hoort te ontbreken, niet als nul te verschijnen."""
    # Drie weken ma t/m za; de zondag bestaat niet in de data.
    rijen = []
    start = pd.Timestamp("2025-01-06")
    for week in range(3):
        for dag in range(6):
            d = start + pd.Timedelta(days=7 * week + dag)
            rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, 150.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    profiel = bk.weekdagprofiel(totalen, pd.Timestamp("2025-01-25"), weken=3)
    assert 6 not in set(profiel["weekdag"])


def _profiel_met_een_eenmalige_zaterdag() -> pd.DataFrame:
    """Vier weken ma t/m vr, plus één enkele zaterdag. Zondag nooit gemeten."""
    rijen = []
    start = pd.Timestamp("2025-01-06")  # maandag
    for week in range(4):
        for dag in range(5):
            d = start + pd.Timedelta(days=7 * week + dag)
            rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, 200.0))
    rijen.append(("2025-01-11", "10", "Brood", "winkel", 1.0, 900.0))  # één zaterdag
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    return bk.weekdagprofiel(totalen, pd.Timestamp("2025-02-02"), weken=4)


def test_weekdagprofiel_geeft_het_aantal_meetdagen_per_weekdag_mee():
    """Een gemiddelde uit één meting is iets anders dan een gemiddelde uit vier.

    Het getal heet in de uitvoer `meetdagen`, zoals het contract het noemt: in
    dit bestand betekent `dagen` op drie andere plekken al iets anders (de lengte
    van een venster, kalenderdagen met data, en dagen waarop een product
    verkocht is). Zonder dit getal in de uitvoer kan de contractlaag het niet
    doorgeven en staat de eenmalige zaterdag op het scherm even hard als de
    maandag met vier metingen.
    """
    per = _profiel_met_een_eenmalige_zaterdag().set_index("weekdag")
    assert per.loc[0, "meetdagen"] == 4
    assert per.loc[5, "meetdagen"] == 1
    assert per.loc[5, "gemiddelde"] == 900.0
    # De zondag is nooit gemeten en hoort te ontbreken (geen nulstaaf); de
    # contractlaag maakt daar een onbeschikbaar-reden van.
    assert 6 not in set(per.index)


# --- productverschuiving ----------------------------------------------------

def _open_vk(rijen) -> pd.DataFrame:
    verkopen = _verkopen(rijen)
    return bk.open_verkopen(verkopen, canoniek.bouw_kalender(verkopen))


def test_productverschuiving_rangschikt_op_euroverschil():
    """Croissant stijgt € 60, brood daalt € 200: brood is het grotere nieuws
    en staat onderaan; procenten zouden het omdraaien."""
    rijen = []
    # vorige periode: 1 t/m 10 jan; huidige: 11 t/m 20 jan
    for dag in range(1, 11):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
        rijen.append((f"2025-01-{dag:02d}", "2", "Croissant", "winkel", 5.0, 2.0))
    for dag in range(11, 21):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 5.0, 20.0))
        rijen.append((f"2025-01-{dag:02d}", "2", "Croissant", "winkel", 20.0, 8.0))
    schuif = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-20"), dagen=10
    )
    assert schuif.vergelijkbaar is True
    assert (schuif.dagen, schuif.vorig_dagen) == (10, 10)
    uit = schuif.rijen
    assert list(uit["product_naam"]) == ["Croissant", "Brood"]
    assert uit.iloc[0]["verschil"] == 60.0
    assert uit.iloc[-1]["verschil"] == -200.0
    assert uit.iloc[-1]["verschil_pct"] == -50.0


def test_productverschuiving_nieuw_product_krijgt_geen_percentage():
    rijen = []
    for dag in range(1, 11):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 100.0))
    for dag in range(11, 21):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 100.0))
        rijen.append((f"2025-01-{dag:02d}", "9", "Nieuwigheid", "winkel", 2.0, 30.0))
    uit = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-20"), dagen=10
    ).rijen
    nieuw = uit[uit["product_naam"] == "Nieuwigheid"].iloc[0]
    assert bool(nieuw["nieuw"]) is True
    assert nieuw["verschil_pct"] is None


def test_productverschuiving_houdt_een_product_zonder_naam_bij_de_dalers():
    """Bevinding 3. Product 77 heeft geen naam en halveert bijna: € 800 minder.

    Met een groepering op (product_id, product_naam) gooit pandas die rijen weg
    en staat de grootste daler helemaal niet in de tabel.
    """
    rijen = []
    for dag in range(1, 11):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
        rijen.append((f"2025-01-{dag:02d}", "77", None, "winkel", 10.0, 100.0))
    for dag in range(11, 21):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
        rijen.append((f"2025-01-{dag:02d}", "77", None, "winkel", 2.0, 20.0))
    uit = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-20"), dagen=10
    ).rijen
    assert set(uit["product_id"]) == {"1", "77"}
    naamloos = uit[uit["product_id"] == "77"].iloc[0]
    assert naamloos["verschil"] == pytest.approx(-800.0)
    assert naamloos["verschil_pct"] == pytest.approx(-80.0)
    assert pd.isna(naamloos["product_naam"])
    # De grootste daler staat onderaan, waar de contractlaag de dalers ophaalt.
    assert uit.iloc[-1]["product_id"] == "77"


def test_productverschuiving_ziet_een_naamswijziging_niet_als_nieuw_product():
    """Bevinding 3, tweede helft. Hetzelfde product_id, halverwege een andere
    naam: dat is één product met een gelijke omzet, geen nieuw product plus een
    volledige daling. De jongste naam is de naam."""
    rijen = []
    for dag in range(1, 11):
        rijen.append((f"2025-01-{dag:02d}", "1", "Boerenbrood", "winkel", 10.0, 40.0))
    for dag in range(11, 21):
        rijen.append(
            (f"2025-01-{dag:02d}", "1", "Boerenbrood groot", "winkel", 10.0, 40.0)
        )
    uit = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-20"), dagen=10
    ).rijen
    assert len(uit) == 1
    assert uit.iloc[0]["product_naam"] == "Boerenbrood groot"
    assert uit.iloc[0]["verschil"] == pytest.approx(0.0)
    assert bool(uit.iloc[0]["nieuw"]) is False


def test_productverschuiving_weigert_te_vergelijken_over_ongelijke_vensters():
    """Bevinding 4. Zes open dagen, dan acht dagen sluiting, dan tien open dagen.

    In kalenderdagen gerekend telt het vorige venster maar twee verkoopdagen mee
    en lijkt elk product te verdubbelen. Er is hier geen vergelijking, en dat
    hoort de uitkomst te zeggen in plaats van een verschil te verzinnen.
    """
    rijen = []
    for dag in list(range(1, 7)) + list(range(15, 25)):  # gat: 7 t/m 14 jan
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
    schuif = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-24"), dagen=10
    )
    assert schuif.dagen == 10
    assert schuif.vorig_dagen == 6
    assert schuif.vergelijkbaar is False
    assert schuif.rijen.empty
    # De kolommen blijven bestaan, zodat de contractlaag niet hoeft te raden en
    # een filter op stijgers of dalers ook op een leeg antwoord werkt.
    # Als letterlijke lijst, niet als bk.VERSCHUIVING_KOLOMMEN: dit is de
    # vorm die het contract belooft, en die belofte mag niet stil meebewegen
    # met de module (audit 15 aug, punt d).
    assert list(schuif.rijen.columns) == [
        "product_id", "product_naam", "omzet_nu", "omzet_vorig",
        "verschil", "verschil_pct", "nieuw",
    ]
    assert schuif.rijen[schuif.rijen["verschil"] > 0].empty


def test_productverschuiving_vergelijkt_over_open_dagen_en_niet_over_de_kalender():
    """Bevinding 4, de andere kant: mét een sluitingsdag in beide vensters blijft
    de vergelijking bestaan, want beide tellen tien gemeten open dagen."""
    dagen_nu = list(range(12, 17)) + list(range(18, 23))  # 17 jan gesloten
    dagen_toen = list(range(1, 6)) + list(range(7, 12))   # 6 jan gesloten
    rijen = []
    for dag in dagen_toen:
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
    for dag in dagen_nu:
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 5.0, 20.0))
    schuif = bk.productverschuiving(
        _open_vk(rijen), pd.Timestamp("2025-01-22"), dagen=10
    )
    assert (schuif.dagen, schuif.vorig_dagen) == (10, 10)
    assert schuif.vergelijkbaar is True
    assert schuif.rijen.iloc[0]["verschil"] == pytest.approx(-200.0)


# --- heleweken --------------------------------------------------------------

def test_heleweken_geeft_de_laatste_volledige_weken_oudste_eerst():
    verkopen = _dagen([100.0] * 35, start="2025-01-06")  # ma t/m zo, 5 weken
    kal = canoniek.bouw_kalender(verkopen)
    weken = bk.heleweken(kal, pd.Timestamp("2025-02-09"), weken=4)
    assert len(weken) == 4
    assert weken[0].van == pd.Timestamp("2025-01-13")
    assert weken[-1].tot == pd.Timestamp("2025-02-09")
    assert all(w.van.dayofweek == 0 for w in weken)
    assert all(w.tot - w.van == pd.Timedelta(days=6) for w in weken)
    assert [w.open_dagen for w in weken] == [7, 7, 7, 7]


def test_heleweken_neemt_de_lopende_halve_week_nooit_mee():
    """Peildatum op woensdag: de week van die woensdag is niet af en telt niet.

    Anders vergelijkt een week-op-weekcijfer drie dagen met zeven en toont het
    een daling die er niet is.
    """
    verkopen = _dagen([100.0] * 38, start="2025-01-06")  # t/m wo 12 feb
    kal = canoniek.bouw_kalender(verkopen)
    weken = bk.heleweken(kal, pd.Timestamp("2025-02-12"), weken=2)
    assert weken[-1].tot == pd.Timestamp("2025-02-09")  # de laatste zondag
    assert weken[0].van == pd.Timestamp("2025-01-27")


def test_heleweken_telt_de_gemeten_open_dagen_per_week():
    """Week twee mist de zondag; een week vóór het meetbereik telt nul."""
    rijen = []
    for dag in range(6, 13):   # ma 6 t/m zo 12 jan: volledig
        rijen.append((f"2025-01-{dag:02d}", "10", "Brood", "winkel", 1.0, 100.0))
    for dag in range(13, 19):  # ma 13 t/m za 18 jan: zondag ontbreekt
        rijen.append((f"2025-01-{dag:02d}", "10", "Brood", "winkel", 1.0, 100.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    weken = bk.heleweken(kal, pd.Timestamp("2025-01-19"), weken=3)
    assert [w.open_dagen for w in weken] == [0, 7, 6]


# --- weekomzet --------------------------------------------------------------

def test_weekomzet_hangt_omzet_aan_de_volledige_weken():
    verkopen = _dagen([100.0] * 21, start="2025-01-06")  # ma 6 jan, 3 weken
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.weekomzet(totalen, kal, pd.Timestamp("2025-01-26"), weken=3)
    assert list(uit["van"]) == [pd.Timestamp("2025-01-06"),
                                pd.Timestamp("2025-01-13"),
                                pd.Timestamp("2025-01-20")]
    assert list(uit["omzet"]) == [Decimal("700.00")] * 3
    assert list(uit["omzet_per_dag"]) == [Decimal("100.00")] * 3
    assert list(uit["open_dagen"]) == [7, 7, 7]
    assert list(uit["reden"]) == [None, None, None]


def test_weekomzet_geeft_een_korte_week_zijn_dagcijfer_en_geen_daling():
    """Week twee mist de zondag: het weektotaal zakt, het dagcijfer niet.

    Zonder omzet per open dag leest zo'n week als een instorting van 14%,
    terwijl er die week gewoon een dag minder open was.
    """
    rijen = [(f"2025-01-{dag:02d}", "10", "Brood", "winkel", 1.0, 100.0)
             for dag in list(range(6, 13)) + list(range(13, 19))]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.weekomzet(totalen, kal, pd.Timestamp("2025-01-19"), weken=2)
    assert list(uit["open_dagen"]) == [7, 6]
    assert list(uit["omzet"]) == [Decimal("700.00"), Decimal("600.00")]
    assert list(uit["omzet_per_dag"]) == [Decimal("100.00"), Decimal("100.00")]


def test_weekomzet_zegt_van_een_dichte_week_dat_ze_dicht_was():
    """Een week zonder gemeten open dag krijgt None met een reden, geen nul.

    Nul zou een week zonder omzet tonen; dat is iets heel anders dan een week
    zonder meting, en het verschil valt niet meer terug te zien.
    """
    rijen = [(f"2025-01-{dag:02d}", "10", "Brood", "winkel", 1.0, 100.0)
             for dag in list(range(6, 13)) + list(range(20, 27))]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.weekomzet(totalen, kal, pd.Timestamp("2025-01-26"), weken=3)
    assert list(uit["open_dagen"]) == [7, 0, 7]
    assert uit["omzet"].iloc[1] is None
    assert uit["omzet_per_dag"].iloc[1] is None
    assert uit["reden"].iloc[1] == "geen gemeten open dagen"
    # De rij verdwijnt niet: een gat in de tabel is onzichtbaar, een reden niet.
    assert len(uit) == 3


# --- concentratie -----------------------------------------------------------

def test_concentratie_telt_de_kop_en_de_staart():
    """Vier producten met 50/30/15/5: precies op de grenzen van 50, 80 en 95%."""
    rijen = [
        ("2025-01-06", "1", "Brood", "winkel", 1.0, 50.0),
        ("2025-01-06", "2", "Croissant", "winkel", 1.0, 30.0),
        ("2025-01-06", "3", "Taart", "winkel", 1.0, 15.0),
        ("2025-01-06", "4", "Koek", "winkel", 1.0, 5.0),
    ]
    uit = bk.concentratie(_open_vk(rijen), pd.Timestamp("2025-01-06"))
    assert uit is not None
    assert uit.voor_50 == 1
    assert uit.voor_80 == 2
    assert uit.voor_95 == 3
    assert uit.totaal_producten == 4
    assert uit.staart_omzet == Decimal("5.00")
    assert uit.dagen == 1


def test_concentratie_kijkt_alleen_naar_het_gevraagde_kanaal():
    """Een groot TGTG-pakket mag de winkelconcentratie niet vertekenen."""
    rijen = [
        ("2025-01-06", "1", "Brood", "winkel", 1.0, 50.0),
        ("2025-01-06", "2", "Croissant", "winkel", 1.0, 50.0),
        ("2025-01-06", "70", "Pakket", "tgtg", 1.0, 500.0),
    ]
    uit = bk.concentratie(_open_vk(rijen), pd.Timestamp("2025-01-06"))
    assert uit.totaal_producten == 2
    assert uit.voor_50 == 1


def test_concentratie_zonder_omzet_is_geen_verdeling():
    """Een open dag met per saldo nul omzet: geen Pareto verzinnen maar None,
    en de contractlaag maakt daar een onbeschikbaar-reden van."""
    rijen = [
        ("2025-01-06", "1", "Brood", "winkel", 1.0, 10.0),
        ("2025-01-06", "1", "Brood", "winkel", -1.0, -10.0),
    ]
    assert bk.concentratie(_open_vk(rijen), pd.Timestamp("2025-01-06")) is None


# --- ontbinding prijs/volume ------------------------------------------------

def test_ontbinding_telt_exact_op_tot_het_omzetverschil():
    """Brood halveert in volume en wordt duurder, Oud verdwijnt, Nieuw komt op.

    p0=4 en p1=5 voor Brood: volume (50-100)*4 = -200, prijs 100*(5-4) = +100,
    kruisterm (-50)*(+1) = -50. Oud droeg 100, Nieuw brengt 30. Alles samen:
    -220, en dat is exact het omzetverschil tussen de vensters.
    """
    rijen = []
    for dag in range(1, 11):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
        rijen.append((f"2025-01-{dag:02d}", "2", "Oud", "winkel", 2.0, 10.0))
    for dag in range(11, 21):
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 5.0, 25.0))
        rijen.append((f"2025-01-{dag:02d}", "3", "Nieuw", "winkel", 1.0, 3.0))
    uit = bk.ontbinding_prijs_volume(
        _open_vk(rijen), pd.Timestamp("2025-01-20"), dagen=10
    )
    assert uit.vergelijkbaar is True
    assert (uit.dagen, uit.vorig_dagen) == (10, 10)
    assert uit.verschil == Decimal("-220.00")
    assert uit.volume == Decimal("-200.00")
    assert uit.prijs == Decimal("100.00")
    assert uit.kruisterm == Decimal("-50.00")
    assert uit.nieuw == Decimal("30.00")
    assert uit.verdwenen == Decimal("100.00")
    # De invariant, op de cent: een ontbinding die niet optelt is er geen.
    assert (
        uit.volume + uit.prijs + uit.kruisterm + uit.nieuw - uit.verdwenen
        == uit.verschil
    )


def test_ontbinding_weigert_ongelijke_vensters():
    """Zelfde redenlogica als productverschuiving: geen vergelijking verzinnen."""
    rijen = []
    for dag in list(range(1, 7)) + list(range(15, 25)):  # gat: 7 t/m 14 jan
        rijen.append((f"2025-01-{dag:02d}", "1", "Brood", "winkel", 10.0, 40.0))
    uit = bk.ontbinding_prijs_volume(
        _open_vk(rijen), pd.Timestamp("2025-01-24"), dagen=10
    )
    assert uit.vergelijkbaar is False
    assert (uit.dagen, uit.vorig_dagen) == (10, 6)
    assert uit.verschil is None
    assert uit.volume is None
    assert uit.prijs is None
    assert uit.kruisterm is None
    assert uit.nieuw is None
    assert uit.verdwenen is None


# --- maandritme -------------------------------------------------------------

def test_maandritme_geeft_omzet_per_open_dag_en_zwijgt_niet_over_een_dichte_maand():
    """Januari tien dagen van 100, februari dicht, maart vijf dagen van 200.

    Februari krijgt None met een reden — geen nul (dat zou een ramp
    suggereren) en geen extrapolatie (dat zou een meting verzinnen).
    """
    rijen = [(f"2025-01-{dag:02d}", "10", "Brood", "winkel", 1.0, 100.0)
             for dag in range(1, 11)]
    rijen += [(f"2025-03-{dag:02d}", "10", "Brood", "winkel", 1.0, 200.0)
              for dag in range(1, 6)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.maandritme(totalen, pd.Timestamp("2025-03-05"))
    assert len(uit) == 12
    assert (uit.iloc[0]["jaar"], uit.iloc[0]["maand"]) == (2024, 4)
    per = uit.set_index(["jaar", "maand"])
    assert per.loc[(2025, 1), "omzet_per_dag"] == Decimal("100.00")
    assert per.loc[(2025, 1), "open_dagen"] == 10
    assert per.loc[(2025, 1), "reden"] is None
    assert per.loc[(2025, 2), "omzet_per_dag"] is None
    assert per.loc[(2025, 2), "open_dagen"] == 0
    assert per.loc[(2025, 2), "reden"] == "geen gemeten open dagen"
    assert per.loc[(2025, 3), "omzet_per_dag"] == Decimal("200.00")


# --- weekdagmix -------------------------------------------------------------

def test_weekdagmix_middelt_per_weekdag_en_de_aandelen_tellen_op_tot_honderd():
    """Twee weken: maandag 100, dinsdag 300, de rest 200."""
    omzetten = ([100.0, 300.0] + [200.0] * 5) * 2
    verkopen = _dagen(omzetten, start="2025-01-06")
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    mix = bk.weekdagmix(totalen, pd.Timestamp("2025-01-19"), dagen=14)
    per = mix.set_index("weekdag")
    assert per.loc[0, "gemiddelde"] == pytest.approx(100.0)
    assert per.loc[1, "gemiddelde"] == pytest.approx(300.0)
    assert per.loc[0, "weekdag_kort"] == "ma"
    assert per.loc[6, "weekdag_kort"] == "zo"
    assert (per["meetdagen"] == 2).all()
    assert float(per["aandeel_pct"].sum()) == pytest.approx(100.0)
    assert per.loc[1, "aandeel_pct"] == pytest.approx(100.0 * 600.0 / 2800.0)


def test_weekdagmix_toont_geen_weekdag_zonder_meting():
    """De vaste sluitingsdag ontbreekt, net als bij weekdagprofiel."""
    rijen = []
    start = pd.Timestamp("2025-01-06")
    for week in range(2):
        for dag in range(6):  # ma t/m za, geen zondag
            d = start + pd.Timedelta(days=7 * week + dag)
            rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, 150.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    mix = bk.weekdagmix(totalen, pd.Timestamp("2025-01-18"), dagen=12)
    assert 6 not in set(mix["weekdag"])


# --- afwijkende dagen -------------------------------------------------------

def test_afwijkende_dagen_vindt_de_uitschieter_tegen_zijn_eigen_weekdag():
    """Tien maandagen rond de 100, één van 300: mediaan 100.5, MAD 1.5."""
    waarden = [100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 97.0, 100.0, 101.0, 300.0]
    verkopen = _verkopen([
        (d, "10", "Brood", "winkel", 1.0, o)
        for d, o in zip(MAANDAGEN, waarden, strict=True)
    ])
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.afwijkende_dagen(totalen, pd.Timestamp("2025-03-10"))
    assert len(uit) == 1
    assert uit.iloc[0]["datum"] == pd.Timestamp("2025-03-10")
    assert uit.iloc[0]["omzet"] == pytest.approx(300.0)
    assert uit.iloc[0]["verwacht_mediaan"] == pytest.approx(100.5)
    assert uit.iloc[0]["z"] == pytest.approx(0.6745 * 199.5 / 1.5)


def test_afwijkende_dagen_zwijgt_bij_te_weinig_waarnemingen_of_mad_nul():
    """Drie dinsdagen met een uitschieter: te weinig voor een mediaan. Tien
    woensdagen waarvan negen identiek: MAD nul, elke afwijking zou oneindig
    zijn. Beide weekdagen doen niet mee, en het antwoord blijft leeg mét
    kolommen zodat de aanroeper geen uitzondering hoeft te schrijven."""
    rijen = []
    for week, o in enumerate([100.0, 100.0, 1000.0]):
        d = pd.Timestamp("2025-01-07") + pd.Timedelta(days=7 * week)
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, o))
    for week, o in enumerate([150.0] * 9 + [900.0]):
        d = pd.Timestamp("2025-01-08") + pd.Timedelta(days=7 * week)
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, o))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.afwijkende_dagen(totalen, pd.Timestamp("2025-03-12"))
    assert uit.empty
    # Letterlijk, niet bk.AFWIJKING_KOLOMMEN (audit 15 aug, punt d).
    assert list(uit.columns) == ["datum", "omzet", "verwacht_mediaan", "z"]


def test_afwijkende_dagen_nieuwste_eerst():
    waarden = [100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 97.0, 100.0, 300.0, 320.0]
    verkopen = _verkopen([
        (d, "10", "Brood", "winkel", 1.0, o)
        for d, o in zip(MAANDAGEN, waarden, strict=True)
    ])
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    uit = bk.afwijkende_dagen(totalen, pd.Timestamp("2025-03-10"))
    assert list(uit["datum"]) == [
        pd.Timestamp("2025-03-10"), pd.Timestamp("2025-03-03")
    ]


# --- bonritme ---------------------------------------------------------------

def _bonnen(rijen) -> pd.DataFrame:
    """rijen: (datum, filiaal_id, bonnen). Zelfde vorm als laad_bonnen levert."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": f, "bonnen": b}
         for d, f, b in rijen]
    )


def _bonnen_totalen(omzetten, start="2025-01-01"):
    verkopen = _dagen(omzetten, start=start)
    kal = canoniek.bouw_kalender(verkopen)
    return bk.dagtotalen(bk.open_verkopen(verkopen, kal))


def test_bonritme_ontbindt_de_omzet_in_klanten_en_mandje():
    """Vorig venster 20 bonnen van 5, huidig 25 bonnen van 6: het verschil van
    50 per dag valt uiteen in 25 (meer klanten), 20 (groter mandje) en 5
    (kruisterm). De bonnen van het huidige venster staan over twee kassa's
    verdeeld: de som per dag is de juiste telling."""
    totalen = _bonnen_totalen([100.0] * 5 + [150.0] * 5)
    rijen = [(f"2025-01-{dag:02d}", "Kassa 1", 20) for dag in range(1, 6)]
    rijen += [(f"2025-01-{dag:02d}", "Kassa 1", 15) for dag in range(6, 11)]
    rijen += [(f"2025-01-{dag:02d}", "Kassa 2", 10) for dag in range(6, 11)]
    rit = bk.bonritme(_bonnen(rijen), totalen, pd.Timestamp("2025-01-10"), dagen=5)
    assert rit.vergelijkbaar is True
    assert (rit.dagen, rit.vorig_dagen) == (5, 5)
    assert rit.bonnen_per_dag == Decimal("25.0")
    assert rit.gemiddeld_bonbedrag == Decimal("6.00")
    assert rit.verschil == Decimal("50.00")
    assert rit.bonneneffect == Decimal("25.00")
    assert rit.bonbedrag_effect == Decimal("20.00")
    assert rit.kruisterm == Decimal("5.00")
    assert rit.dagen_zonder_bonnen == 0
    # De invariant, op de cent.
    assert rit.bonneneffect + rit.bonbedrag_effect + rit.kruisterm == rit.verschil


def test_bonritme_laat_een_dag_zonder_bonnen_uit_de_vergelijking_en_telt_hem():
    """Dag acht heeft omzet maar geen bonnen: die dag doet niet mee (bonnen nul
    verzinnen zou het bonbedrag oneindig maken) en wordt geteld, zodat de UI de
    beperking kan tonen."""
    totalen = _bonnen_totalen([100.0] * 10)
    rijen = [(f"2025-01-{dag:02d}", "Kassa 1", 20)
             for dag in range(1, 11) if dag != 8]
    rit = bk.bonritme(_bonnen(rijen), totalen, pd.Timestamp("2025-01-10"), dagen=4)
    assert rit.vergelijkbaar is True
    assert (rit.dagen, rit.vorig_dagen) == (4, 4)
    assert rit.dagen_zonder_bonnen == 1
    assert rit.verschil == Decimal("0.00")


def test_bonritme_zonder_gelijk_vorig_venster_geen_ontbinding():
    """Zeven dagen historiek en een venster van vijf: het huidige cijfer
    bestaat, de vergelijking niet."""
    totalen = _bonnen_totalen([100.0] * 7)
    rijen = [(f"2025-01-{dag:02d}", "Kassa 1", 20) for dag in range(1, 8)]
    rit = bk.bonritme(_bonnen(rijen), totalen, pd.Timestamp("2025-01-07"), dagen=5)
    assert rit.vergelijkbaar is False
    assert (rit.dagen, rit.vorig_dagen) == (5, 2)
    assert rit.bonnen_per_dag == Decimal("20.0")
    assert rit.gemiddeld_bonbedrag == Decimal("5.00")
    assert rit.verschil is None
    assert rit.bonneneffect is None
    assert rit.bonbedrag_effect is None
    assert rit.kruisterm is None


def test_bonritme_zonder_enige_bonnen_is_geen_cijfer():
    """Geen overlap tussen de bronnen: geen gemiddelde verzinnen, wel tellen
    hoeveel open dagen zonder bonnen zitten."""
    totalen = _bonnen_totalen([100.0] * 10)
    leeg = pd.DataFrame(columns=["datum", "filiaal_id", "bonnen"])
    rit = bk.bonritme(leeg, totalen, pd.Timestamp("2025-01-10"), dagen=5)
    assert (rit.dagen, rit.vorig_dagen) == (0, 0)
    assert rit.vergelijkbaar is False
    assert rit.bonnen_per_dag is None
    assert rit.gemiddeld_bonbedrag is None
    assert rit.dagen_zonder_bonnen == 5


# --- marge --------------------------------------------------------------------

def _marge_verkopen() -> tuple[pd.DataFrame, pd.Series, pd.Timestamp]:
    """Tien dagen, twee groepen: Brood € 100/dag, Patisserie € 50/dag."""
    dagen = pd.date_range("2025-01-01", periods=10, freq="D")
    rijen = []
    for d in dagen:
        rijen.append((d.date().isoformat(), "10", "Brood wit", "winkel", 1.0, 100.0))
        rijen.append((d.date().isoformat(), "20", "Eclair", "winkel", 1.0, 50.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    groepen = pd.Series({"10": "Brood", "20": "Patisserie"})
    return open_v, groepen, bk.peildatum(open_v)


def test_marge_per_groep_rekent_omzet_min_kosten_in_centen():
    """Brutomarge = 100 - som criteria: Brood 45% kost -> 55% marge."""
    open_v, groepen, tot = _marge_verkopen()
    beeld = bk.marge_per_groep(
        open_v, groepen,
        {"Brood": {"Grondstoffen": Decimal(40), "Verlies": Decimal(5)},
         "Patisserie": {"Grondstoffen": Decimal("37.5")}},
        tot, criteria_volgorde=("Grondstoffen", "Verlies"), dagen=10)
    per = beeld.rijen.set_index("groep")
    assert per.loc["Brood", "marge_pct"] == Decimal(55)
    assert per.loc["Brood", "marge_eur"] == Decimal("550.00")
    assert per.loc["Patisserie", "marge_eur"] == Decimal("312.50")
    assert beeld.marge_eur == Decimal("862.50")
    assert beeld.totale_omzet == Decimal("1500.00")
    assert beeld.dekking_pct == Decimal("100.0")
    # gewogen: 862.50 / 1500 = 57.5%
    assert beeld.gewogen_pct == Decimal("57.5")
    assert beeld.dagen == 10
    # de opbouw per groep volgt de modelvolgorde en telt op tot de kost
    opbouw = per.loc["Brood", "opbouw"]
    assert [p["criterium"] for p in opbouw] == ["Grondstoffen", "Verlies"]
    assert sum(p["eur"] for p in opbouw) == Decimal("450.00")


def test_marge_per_criterium_aggregeert_over_de_juiste_basis():
    """Een criterium weegt alleen over de omzet van de groepen waar het is
    ingevuld — anders drukt gedekte omzet zonder dat criterium het percentage."""
    open_v, groepen, tot = _marge_verkopen()
    beeld = bk.marge_per_groep(
        open_v, groepen,
        {"Brood": {"Grondstoffen": Decimal(30), "Verlies": Decimal(5)},
         "Patisserie": {"Grondstoffen": Decimal(40)}},
        tot, criteria_volgorde=("Grondstoffen", "Verlies"), dagen=10)
    per = beeld.per_criterium.set_index("criterium")
    # Grondstoffen: 30% van 1000 + 40% van 500 = 500, basis 1500, 2 groepen
    assert per.loc["Grondstoffen", "kost_eur"] == Decimal("500.00")
    assert per.loc["Grondstoffen", "omzet_basis"] == Decimal("1500.00")
    # Verlies: alleen Brood -> 50 op basis 1000
    assert per.loc["Verlies", "kost_eur"] == Decimal("50.00")
    assert per.loc["Verlies", "omzet_basis"] == Decimal("1000.00")
    assert per.loc["Verlies", "groepen_n"] == 1
    # identiteit op de cent: gedekte omzet - alle kosten = marge
    assert (beeld.gedekte_omzet - per["kost_eur"].sum()) == beeld.marge_eur


def test_marge_weegt_alleen_over_gedekte_groepen():
    """Een groep zonder ingevulde kosten dikt het gemiddelde niet aan en
    verdwijnt niet: ze staat in de rijen met marge None."""
    open_v, groepen, tot = _marge_verkopen()
    beeld = bk.marge_per_groep(open_v, groepen,
                               {"Brood": {"Totale kost": Decimal(50)}},
                               tot, dagen=10)
    per = beeld.rijen.set_index("groep")
    assert per.loc["Patisserie", "marge_pct"] is None
    assert per.loc["Patisserie", "marge_eur"] is None
    assert beeld.gedekte_omzet == Decimal("1000.00")
    assert beeld.gewogen_pct == Decimal("50.0")
    # de som van de gevulde rijen is het geheel, op de cent
    gevuld = beeld.rijen[beeld.rijen["marge_eur"].notna()]
    assert sum(gevuld["marge_eur"], Decimal(0)) == beeld.marge_eur


def test_marge_boven_100_procent_kost_wordt_negatief_getoond():
    open_v, groepen, tot = _marge_verkopen()
    beeld = bk.marge_per_groep(
        open_v, groepen,
        {"Brood": {"Grondstoffen": Decimal(80), "Verlies": Decimal(30)}},
        tot, dagen=10)
    per = beeld.rijen.set_index("groep")
    assert per.loc["Brood", "marge_pct"] == Decimal(-10)
    assert per.loc["Brood", "marge_eur"] == Decimal("-100.00")


def test_marge_zonder_omzet_is_geen_beeld():
    open_v, groepen, tot = _marge_verkopen()
    ver_weg = tot + pd.Timedelta(days=400)
    assert bk.marge_per_groep(open_v, groepen,
                              {"Brood": {"Totale kost": Decimal(50)}},
                              ver_weg, dagen=10) is None


def test_marge_zonder_enige_invoer_heeft_geen_gewogen_cijfer():
    open_v, groepen, tot = _marge_verkopen()
    beeld = bk.marge_per_groep(open_v, groepen, {}, tot, dagen=10)
    assert beeld is not None
    assert beeld.gewogen_pct is None
    assert beeld.gedekte_omzet == Decimal("0.00")
    assert list(beeld.rijen["groep"]) == ["Brood", "Patisserie"]


# --- periodeblok ---------------------------------------------------------------

def test_periodeblok_somt_en_middelt_over_open_dagen():
    totalen = bk.dagtotalen(bk.open_verkopen(
        _dagen([100.0, 200.0, 300.0]),
        canoniek.bouw_kalender(_dagen([100.0, 200.0, 300.0])),
    ))
    blok = bk.periodeblok(totalen, pd.Timestamp("2025-01-01"),
                          pd.Timestamp("2025-01-03"))
    assert blok.omzet == Decimal("600.00")
    assert blok.open_dagen == 3
    assert blok.gemiddelde == Decimal("200.00")


def test_periodeblok_zonder_meting_heeft_geen_gemiddelde():
    totalen = bk.dagtotalen(bk.open_verkopen(
        _dagen([100.0]), canoniek.bouw_kalender(_dagen([100.0]))))
    blok = bk.periodeblok(totalen, pd.Timestamp("2024-01-01"),
                          pd.Timestamp("2024-01-31"))
    assert blok.omzet == Decimal("0.00")
    assert blok.open_dagen == 0
    assert blok.gemiddelde is None


# --- kanaalfinanciën -------------------------------------------------------------

def test_kanaalfinancien_maakt_de_tgtg_wig_zichtbaar():
    """De canonieke TGTG-omzet is netto; bruto = netto + stuks × commissie
    van de maand waarin de verkoop viel."""
    rijen = [("2025-01-0" + str(d), "10", "Brood", "winkel", 1.0, 100.0)
             for d in range(1, 6)]
    rijen += [("2025-01-0" + str(d), "99", "Verrassingszak", "tgtg", 2.0, 8.0)
              for d in range(1, 6)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    kost = pd.DataFrame({
        "kanaal": ["tgtg"], "maand": ["2025-01"], "stuks": [10.0],
        "bruto_per_stuk": [5.69], "commissie_per_stuk": [1.69],
        "inhouding_pct": [0.297],
    })
    fin = {f.kanaal: f for f in bk.kanaalfinancien(
        totalen, kost, pd.Timestamp("2025-01-05"), dagen=5)}
    assert fin["winkel"].commissie == Decimal("0.00")
    assert fin["winkel"].bruto == fin["winkel"].netto == Decimal("500.00")
    assert fin["winkel"].inhouding_pct is None
    # tgtg: 5 dagen × 2 stuks × € 1,69 = € 16,90 commissie op € 40 netto
    assert fin["tgtg"].netto == Decimal("40.00")
    assert fin["tgtg"].commissie == Decimal("16.90")
    assert fin["tgtg"].bruto == Decimal("56.90")
    assert fin["tgtg"].inhouding_pct == Decimal("29.7")


def test_kanaalfinancien_zonder_kosttabel_rekent_tgtg_niet_bruto():
    rijen = [("2025-01-01", "99", "Zak", "tgtg", 2.0, 8.0),
             ("2025-01-01", "10", "Brood", "winkel", 1.0, 100.0)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    fin = {f.kanaal: f for f in bk.kanaalfinancien(
        totalen, None, pd.Timestamp("2025-01-01"), dagen=5)}
    # zonder tarief geen wig: commissie nul, en de contractlaag zet de reden erbij
    assert fin["tgtg"].commissie == Decimal("0.00")


# --- drill-down per groep ---------------------------------------------------------

def test_groepen_detail_weegt_binnen_de_eigen_groep():
    rijen = []
    for d in ("2025-01-01", "2025-01-02"):
        rijen.append((d, "10", "Brood wit", "winkel", 1.0, 60.0))
        rijen.append((d, "11", "Brood bruin", "winkel", 1.0, 40.0))
        rijen.append((d, "20", "Eclair", "winkel", 1.0, 50.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    detail = bk.groepen_detail(
        open_v, pd.Series({"10": "Brood", "11": "Brood", "20": "Patisserie"}),
        pd.Timestamp("2025-01-02"), dagen=2)
    # zwaarste groep eerst (Brood 200 > Patisserie 100), binnen de groep op omzet
    assert list(detail["groep"]) == ["Brood", "Brood", "Patisserie"]
    assert list(detail["product_naam"])[:2] == ["Brood wit", "Brood bruin"]
    wit = detail[detail["product_naam"] == "Brood wit"].iloc[0]
    assert round(float(wit["aandeel_in_groep_pct"]), 1) == 60.0


def test_groepen_detail_product_zonder_groep_valt_onder_overige():
    rijen = [("2025-01-01", "99", "Mysterie", "winkel", 1.0, 10.0)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    detail = bk.groepen_detail(open_v, pd.Series(dtype=str),
                               pd.Timestamp("2025-01-01"), dagen=1)
    assert list(detail["groep"]) == ["Overige"]


# --- TGTG-restwaarde per kwartaal (A5) --------------------------------------------

def test_tgtg_restwaarde_per_kwartaal_met_en_zonder_kosttabel():
    rijen = [("2025-01-15", "99", "Zak", "tgtg", 2.0, 8.0),
             ("2025-02-15", "99", "Zak", "tgtg", 1.0, 4.0),
             ("2025-04-01", "99", "Zak", "tgtg", 1.0, 4.0),
             ("2025-01-15", "10", "Brood", "winkel", 1.0, 100.0)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    kost = pd.DataFrame({
        "kanaal": ["tgtg"], "maand": ["2025-01"], "stuks": [3.0],
        "bruto_per_stuk": [5.69], "commissie_per_stuk": [1.69],
        "inhouding_pct": [0.297],
    })
    tabel = bk.tgtg_restwaarde_per_kwartaal(totalen, kost)
    assert list(tabel["kwartaal"]) == ["2025K1", "2025K2"]
    k1 = tabel.iloc[0]
    assert k1["netto"] == Decimal("12.00")
    # 3 stuks × € 1,69 (jan-tarief geldt ook voor feb, terugvalregel)
    assert k1["commissie"] == Decimal("5.07")
    assert k1["bruto"] == Decimal("17.07")
    # zonder kosttabel: netto blijft, wig eerlijk afwezig
    kaal = bk.tgtg_restwaarde_per_kwartaal(totalen, None)
    assert kaal.iloc[0]["netto"] == Decimal("12.00")
    assert kaal.iloc[0]["commissie"] is None
    assert kaal.iloc[0]["bruto"] is None


def test_tgtg_restwaarde_zonder_tgtg_is_leeg():
    rijen = [("2025-01-15", "10", "Brood", "winkel", 1.0, 100.0)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    assert bk.tgtg_restwaarde_per_kwartaal(totalen, None).empty


def test_kerncijfers_bestaan_in_het_frans_met_dezelfde_cijfers():
    """De labels en toelichtingen volgen de taal, de waarden niet: één
    berekening, twee talen (de belofte van het contract)."""
    from bakkerij import taal as tl

    verkopen = _dagen([100.0] * 80)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    tot = bk.peildatum(bk.open_verkopen(verkopen, kal))

    nl = bk.kerncijfers(totalen, tot)
    with tl.in_taal("fr"):
        fr = bk.kerncijfers(totalen, tot)

    assert [k.waarde for k in fr] == [k.waarde for k in nl]
    assert [k.soort for k in fr] == [k.soort for k in nl]
    labels_fr = [k.label for k in fr]
    assert "Chiffre d'affaires, 7 derniers jours d'ouverture" in labels_fr
    assert "Chiffre d'affaires, 30 derniers jours d'ouverture" in labels_fr
    assert "Unités, 7 derniers jours d'ouverture" in labels_fr
    assert "Chiffre d'affaires moyen par jour" in labels_fr
    for k in fr:
        assert "open dagen" not in k.toelichting, k.toelichting
    # En de sleutel doet precies het omgekeerde van het label: hij beweegt
    # niet mee. Dat is het hele punt van het onderscheid (19 aug 2026).
    assert [k.sleutel for k in fr] == [k.sleutel for k in nl]


#: De vier machinesleutels van de kerncijfers. Ze staan hier voluit en niet
#: afgeleid uit de code: een lijst die zichzelf uit de implementatie haalt,
#: bevestigt alleen dat de implementatie zichzelf gelijk is. Dit is een
#: afspraak met de leeskant, en een afspraak schrijf je op.
KERNCIJFERSLEUTELS = ("omzet_7", "omzet_30", "stuks_7", "gemiddelde_dagomzet")


def test_de_kerncijfersleutels_liggen_vast_en_zijn_geen_tekst_voor_een_mens():
    """De sleutel is een machinenaam, in elke taal dezelfde.

    Tot 19 augustus 2026 bouwde `contract.py` de sleutel van een ontbrekende
    jaarvergelijking uit het lábel, en dat label is tweetalig. Dezelfde toestand
    heette daardoor in het Frans anders dan in het Nederlands, terwijl
    `platform/lib/toelichting.ts` over `veld` uitdrukkelijk belooft dat hij een
    hertaling overleeft.
    """
    from bakkerij import taal as tl

    verkopen = _dagen([100.0] * 80)
    kal = canoniek.bouw_kalender(verkopen)
    totalen = bk.dagtotalen(bk.open_verkopen(verkopen, kal))
    tot = bk.peildatum(bk.open_verkopen(verkopen, kal))

    for taalcode in ("nl", "fr"):
        with tl.in_taal(taalcode):
            sleutels = tuple(k.sleutel for k in bk.kerncijfers(totalen, tot))
        assert sleutels == KERNCIJFERSLEUTELS, taalcode
        for s in sleutels:
            assert s == s.lower(), f"{s}: een sleutel draagt geen hoofdletters"
            assert " " not in s, f"{s}: een sleutel is geen zin"


def test_elk_kerncijfer_heeft_een_label_in_het_platform():
    """De wacht op de koppeling: sleutel hier, label daar.

    Een nieuw kerncijfer zonder regel in `platform/lib/toelichting.ts` valt op
    het voorvoegselvangnet en verschijnt als "Kerncijfer: omzet 7" — een
    machinenaam op het scherm, precies wat O12 dichtgezet heeft. Er is geen
    andere koppeling tussen die twee bestanden dan deze test.
    """
    from pathlib import Path

    bron = (Path(__file__).resolve().parents[1]
            / "platform" / "lib" / "toelichting.ts").read_text(encoding="utf-8")
    for sleutel in KERNCIJFERSLEUTELS:
        assert f'"kerncijfer.{sleutel}"' in bron, (
            f'kerncijfer.{sleutel} heeft geen label in '
            f'platform/lib/toelichting.ts'
        )


def test_producten_zonder_categorie_heten_in_het_frans_autres():
    """Dezelfde restgroep, per taal zijn eigen naam — en niets valt weg."""
    from bakkerij import taal as tl

    verkopen = _verkopen([
        ("2025-01-06", "10", "Brood", "winkel", 1.0, 60.0),
        ("2025-01-06", "99", "Onbekend", "winkel", 1.0, 40.0),
    ])
    kal = canoniek.bouw_kalender(verkopen)
    groepen = pd.Series({"10": "Brood"})
    with tl.in_taal("fr"):
        per = bk.omzet_per_groep(
            bk.open_verkopen(verkopen, kal), groepen, pd.Timestamp("2025-01-06")
        ).set_index("groep")
    assert per.loc["Autres", "omzet"] == pytest.approx(40.0)
    assert "Overige" not in per.index
