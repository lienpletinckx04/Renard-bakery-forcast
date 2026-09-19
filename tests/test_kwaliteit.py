"""De kwaliteitslaag: sluitingsbewuste dodemansknop en wachters (O14/O15).

De kerntest is die van de zomersluiting: een dodemansknop die vier weken
sluiting lang alarm slaat, is op de dag van de echte storing onzichtbaar.
'stil' mag alleen wanneer de kalender zegt dat de winkel open hoorde te zijn.
"""
import datetime as dt

import pandas as pd

from bakkerij import kwaliteit as kw

D = dt.date


def _verkopen(rijen):
    return pd.DataFrame(
        rijen,
        columns=["datum", "filiaal_id", "product_id", "product_naam",
                 "kanaal", "aantal", "omzet_excl_btw"],
    )


def _winkelrij(datum, omzet=100.0, product="7"):
    return (datum, "Kassa 1", product, "Brood", "winkel", 5.0, omzet)


def _deliveroorij(datum, omzet=8.0):
    """Eén dagrij Deliveroo, in de vorm die `orders_naar_canoniek` maakt:
    één synthetisch product per vestiging per dag."""
    return (datum, "Renard Bakery", "dl-bestellingen", "Deliveroo-bestellingen",
            "deliveroo", 2.0, omzet)


def _kalender(dagen):
    return pd.DataFrame(dagen, columns=["datum", "winkel_gemeten", "winkel_open"])


def _kalender_met_sluiting(dagen):
    """Dezelfde kalender, plus de aangekondigde sluitingen.

    Een aparte helper zodat de bestaande tests zonder de kolom blijven draaien:
    de kolom is optioneel, en een kalender zonder sluitingskennis moet zich
    precies zo gedragen als voorheen.
    """
    kal = pd.DataFrame(
        dagen,
        columns=["datum", "winkel_gemeten", "winkel_open", "gepland_dicht"],
    )
    kal["gepland_dicht_reden"] = [
        "Jaarlijkse sluiting" if d else "" for d in kal["gepland_dicht"]
    ]
    return kal


def _week_verkopen(tot, dagen=14):
    """Dagelijkse winkelverkoop t/m `tot`."""
    start = tot - dt.timedelta(days=dagen - 1)
    return [_winkelrij(start + dt.timedelta(days=i)) for i in range(dagen)]


def test_zomersluiting_is_gesloten_en_geen_stil():
    tot = D(2026, 7, 31)
    vandaag = D(2026, 8, 13)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender(
        [(tot - dt.timedelta(days=i), True, True) for i in range(14)]
        + [(tot + dt.timedelta(days=i), True, False) for i in range(1, 13)]
    )
    standen = {b.bron: b for b in kw.bronstanden(verkopen, kal, vandaag=vandaag)}
    assert standen["odoo-kassa"].status == "gesloten"
    assert "geen alarm" in standen["odoo-kassa"].toelichting


def test_echte_stilte_op_verwachte_open_dagen_slaat_alarm():
    tot = D(2026, 5, 10)
    vandaag = D(2026, 5, 15)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender(
        [(tot - dt.timedelta(days=i), True, True) for i in range(14)]
        + [(tot + dt.timedelta(days=i), True, True) for i in range(1, 5)]
    )
    standen = {b.bron: b for b in kw.bronstanden(verkopen, kal, vandaag=vandaag)}
    assert standen["odoo-kassa"].status == "stil"
    uit = kw.stand(verkopen, kal, vandaag=vandaag)
    assert uit["ergste"] == "fout"


def test_niet_gemeten_dagen_zijn_achter_en_nooit_stil():
    tot = D(2026, 5, 10)
    vandaag = D(2026, 5, 20)
    verkopen = _verkopen(_week_verkopen(tot))
    # De kalender stopt op de laatste meetdag: alles erna is onbekend.
    kal = _kalender([(tot - dt.timedelta(days=i), True, True) for i in range(14)])
    standen = {b.bron: b for b in kw.bronstanden(verkopen, kal, vandaag=vandaag)}
    assert standen["odoo-kassa"].status == "achter"


def test_een_aangekondigde_sluiting_is_geen_achterstand():
    """De fout van 18 augustus 2026, aan de kant van de dodemansknop.

    De meting stopt op 7 augustus omdat er daarna geen dag meer geopend is. De
    tien dagen erna zijn niet gemeten, maar de kalender kent ze wél: ze staan
    alle tien als `gepland_dicht`. Dan is er geen achterstand en geen alarm — en
    zonder dat onderscheid zou deze bron vier weken zomersluiting lang 'achter'
    melden, precies het permanente alarm dat op de dag van de echte storing
    niemand meer opvalt.
    """
    tot = D(2026, 8, 7)
    vandaag = D(2026, 8, 18)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender_met_sluiting(
        [(tot - dt.timedelta(days=i), True, True, False) for i in range(14)]
        + [(tot + dt.timedelta(days=i), False, False, True) for i in range(1, 17)]
    )
    standen = {b.bron: b for b in kw.bronstanden(verkopen, kal, vandaag=vandaag)}
    assert standen["odoo-kassa"].status == "gesloten"
    assert "vooraf als gesloten aangekondigd" in standen["odoo-kassa"].toelichting


def test_ongemeten_dagen_die_geen_sluiting_verklaart_blijven_achter():
    """Dezelfde vorm, maar de sluitingskennis houdt op na drie dagen. Wat daarna
    komt, verklaart niemand — en dat is wél achterstand."""
    tot = D(2026, 8, 7)
    vandaag = D(2026, 8, 18)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender_met_sluiting(
        [(tot - dt.timedelta(days=i), True, True, False) for i in range(14)]
        + [(tot + dt.timedelta(days=i), False, False, i <= 3) for i in range(1, 17)]
    )
    standen = {b.bron: b for b in kw.bronstanden(verkopen, kal, vandaag=vandaag)}
    assert standen["odoo-kassa"].status == "achter"


def test_deliveroo_dat_ontbreekt_is_sinds_de_lading_een_let_op():
    """Tot 19 september 2026 stond Deliveroo in `BEKEND_AFWEZIG` en telde een
    ontbrekend kanaal niet mee in 'ergste': de bron was er nog nooit geweest.
    Sinds de historiek geladen is, is een lege Deliveroo geen bekende
    afwezigheid meer maar verdwenen data -- en dat hoort de stand te melden.
    De reden blijft die van Partner Hub: dáár komt het kanaal vandaan."""
    tot = D(2026, 5, 10)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender(
        [(tot - dt.timedelta(days=i), True, True) for i in range(14)]
        + [(tot + dt.timedelta(days=i), False, False) for i in range(1, 21)]
    )
    uit = kw.stand(verkopen, kal, vandaag=D(2026, 5, 11))
    deliveroo = next(b for b in uit["bronnen"] if b["bron"] == "deliveroo")
    assert deliveroo["status"] == "ontbreekt"
    assert "Partner Hub" in deliveroo["toelichting"]
    assert uit["ergste"] == "let_op"


def test_deliveroo_met_data_is_een_periodieke_bron_met_een_lat_van_21_dagen():
    """Het kanaal routeert naar `_stand_periodiek` via `ACHTER_DAGEN_PER_KANAAL`
    en niet naar de dagelijkse tak: een jongste dag van 14 dagen oud is 'vers'
    (binnen de lat, ver voorbij de twee dagen van de dagelijkse tak), een van
    100 dagen oud is 'achter'."""
    tot = D(2026, 5, 10)
    winkel = _week_verkopen(tot)
    vers = _verkopen(winkel + [_deliveroorij(D(2026, 4, 27))])
    kal = _kalender(
        [(tot - dt.timedelta(days=i), True, True) for i in range(14)]
        + [(tot + dt.timedelta(days=i), False, False) for i in range(1, 21)]
    )
    uit = kw.stand(vers, kal, vandaag=D(2026, 5, 11))
    d = next(b for b in uit["bronnen"] if b["bron"] == "deliveroo")
    assert d["status"] == "vers"

    oud = _verkopen(winkel + [_deliveroorij(D(2026, 1, 31))])
    uit = kw.stand(oud, kal, vandaag=D(2026, 5, 11))
    d = next(b for b in uit["bronnen"] if b["bron"] == "deliveroo")
    assert d["status"] == "achter"
    assert "21" in d["toelichting"]


def test_een_tweede_bevroren_kanaal_krijgt_dezelfde_behandeling(monkeypatch):
    """Bewijst dat de bevroren tak op `BEVROREN` staat en niet op één naam.

    Waarom dit een eigen test verdient: de dag dat er een tweede kanaal
    bijkomt dat niet meer aangevuld wordt, mag niemand er nog aan hoeven denken
    om óók een kanaalnaam in `bronstanden` bij te schrijven. Zakt die tak ooit
    terug naar één naam, dan valt dit verzonnen kanaal in `_stand_dagelijks`,
    met de lat van twee dagen op een bron die per definitie niet dagelijks
    bijkomt — permanent 'achter', en dat is het alarm dat op de dag van de
    echte storing niemand meer opvalt.

    Het kanaal is met opzet verzonnen, zodat de test niet afhangt van welke
    echte kanalen er vandaag in `BEVROREN` staan. Deliveroo krijgt een verse
    dagrij mee: sinds de lading van 19 september 2026 is een lege Deliveroo
    verdwenen data (let_op), en dat zou 'ergste' hier vervuilen.
    """
    monkeypatch.setattr(kw, "BRONNEN",
                        kw.BRONNEN + (("marktkraam", "marktkraam"),))
    monkeypatch.setattr(kw, "BEVROREN", ("marktkraam",))

    laatste_kraam = D(2026, 6, 20)
    tot = D(2027, 3, 10)
    vandaag = D(2027, 3, 11)
    verkopen = _verkopen(
        _week_verkopen(tot)
        + [(laatste_kraam, "1", "9", "Pakket", "marktkraam", 2.0, 8.0)]
        + [_deliveroorij(tot)]
    )
    kal = _kalender(
        [(tot - dt.timedelta(days=i), True, True) for i in range(14)]
        + [(tot + dt.timedelta(days=i), False, False) for i in range(1, 21)]
    )

    uit = kw.stand(verkopen, kal, vandaag=vandaag)
    kraam = next(b for b in uit["bronnen"] if b["bron"] == "marktkraam")

    # Bijna negen maanden oud, en toch geen alarm: de bevriezing werkt.
    assert kraam["status"] == "bevroren"
    assert kraam["laatste_meetdag"] == laatste_kraam.isoformat()
    assert laatste_kraam.isoformat() in kraam["toelichting"]
    assert uit["ergste"] == "goed"


def test_een_periodiek_kanaal_zonder_bevriezing_mijdt_de_dagelijkse_tak(monkeypatch):
    """Het geval dat vandaag nog niet bestaat en morgen wél: bijkomend, maar niet
    dagelijks.

    Dit is de derde mogelijkheid uit het commentaar bij `BEKEND_AFWEZIG`: een
    bron die niet afwezig is en niet bevroren, maar met de hand periodiek
    opgeladen wordt. Zonder deze test zou zo'n kanaal in `_stand_dagelijks`
    vallen — met `MAX_ONGEMETEN_DAGEN` op twee, dus twee dagen na de laatste
    oplading permanent 'achter'.

    De test toetst dus twee dingen tegelijk: dat de eigen lat gebruikt wordt
    (ver voorbij de twee dagen van de dagelijkse tak, en toch 'vers'), en dat
    het kanaal ná die lat wél gewoon 'achter' meldt — want deze bron komt nog
    bij, en dan is een achterstand weer een echt signaal.

    Het kanaal is met opzet verzonnen. Deliveroo staat in `BEKEND_AFWEZIG` en
    hoort daar te blijven tot het echt laadt; een test die het kanaal alvast
    een lat zou geven, loopt op dat besluit vooruit.
    """
    monkeypatch.setattr(kw, "BRONNEN",
                        kw.BRONNEN + (("marktkraam", "marktkraam"),))
    monkeypatch.setattr(kw, "ACHTER_DAGEN_PER_KANAAL",
                        dict(kw.ACHTER_DAGEN_PER_KANAAL, marktkraam=90))
    # `BEVROREN` blijft ongemoeid: dit kanaal wordt nog wél aangevuld.

    tot = D(2026, 5, 10)
    vandaag = D(2026, 5, 11)
    kal = _kalender([(tot - dt.timedelta(days=i), True, True)
                     for i in range(14)])

    def _stand_van_de_kraam(laatste_oplading):
        verkopen = _verkopen(
            _week_verkopen(tot)
            + [(laatste_oplading, "1", "9", "Pakket", "marktkraam", 2.0, 8.0)]
        )
        standen = kw.bronstanden(verkopen, kal, vandaag=vandaag)
        return {b.bron: b for b in standen}["marktkraam"]

    # 60 dagen sinds de laatste oplading: dertig keer de dagelijkse lat, en
    # toch geen alarm, want het ritme van dit kanaal is een ander.
    binnen = _stand_van_de_kraam(D(2026, 3, 12))
    assert binnen.status == "vers"
    # De kanaalnaam staat in de zin; de bron is niet meer hardgecodeerd.
    assert "marktkraam" in binnen.toelichting

    # 100 dagen: voorbij de eigen lat van 90, en dan is het wél een signaal.
    assert _stand_van_de_kraam(D(2026, 1, 31)).status == "achter"


def test_een_kanaal_zonder_eigen_lat_valt_terug_op_de_maandlat():
    """De terugval bestaat om de dodemansknop niet zelf te laten omvallen.

    Via `bronstanden` is dit onbereikbaar: die routeert op de sleutels van
    `ACHTER_DAGEN_PER_KANAAL`, dus wie daar komt heeft een lat. Bij een
    rechtstreekse aanroep zou een ontbrekende regel een KeyError geven, en die
    zou de hele `stand()` meenemen — de laag die moet melden dat het platform
    stilstaat, zwijgt dan zelf. Vandaar de terugval, en vandaar deze test.
    """
    deel = _verkopen([(D(2026, 3, 12), "1", "9", "Pakket", "kar", 2.0, 8.0)])
    # 60 dagen oud: voorbij de 45 van de maandelijkse bron, dus 'achter'.
    assert kw._stand_periodiek("kar", deel, D(2026, 5, 11)).status == "achter"


def test_dubbele_sleutels_zijn_fout_en_unieke_zijn_goed():
    tot = D(2026, 5, 10)
    schoon = _verkopen(_week_verkopen(tot))
    assert kw.dubbele_sleutels(schoon).uitkomst == "goed"
    dubbel = _verkopen(_week_verkopen(tot) + [_winkelrij(tot)])
    w = kw.dubbele_sleutels(dubbel)
    assert w.uitkomst == "fout"
    assert "1 rij" in w.toelichting


def test_negatieve_waarden_zijn_let_op():
    verkopen = _verkopen([_winkelrij(D(2026, 5, 1)),
                          (D(2026, 5, 2), "Kassa 1", "7", "Brood", "winkel",
                           -1.0, -3.5)])
    assert kw.negatieve_waarden(verkopen).uitkomst == "let_op"
    assert kw.negatieve_waarden(_verkopen([_winkelrij(D(2026, 5, 1))])).uitkomst == "goed"


def test_gat_in_de_reeks_onderscheidt_gesloten_van_gat():
    dagen = [D(2026, 5, 1) + dt.timedelta(days=i) for i in range(6)]
    # Dag 3 gesloten (geen gat), dag 4 open zonder rijen (echt gat).
    verkopen = _verkopen([_winkelrij(d) for d in dagen if d.day not in (3, 4)])
    kal = _kalender([(d, True, d.day != 3) for d in dagen])
    w = kw.gat_in_de_reeks(verkopen, kal)
    assert w.uitkomst == "fout"
    assert "2026-05-04" in w.toelichting

    zonder_gat = _verkopen([_winkelrij(d) for d in dagen if d.day != 3])
    assert kw.gat_in_de_reeks(zonder_gat, kal).uitkomst == "goed"


def test_kalenderdekking_eist_veertien_dagen_vooruit():
    vandaag = D(2026, 5, 10)
    kort = _kalender([(vandaag + dt.timedelta(days=i), False, False)
                      for i in range(5)])
    assert kw.kalenderdekking(kort, vandaag).uitkomst == "let_op"
    lang = _kalender([(vandaag + dt.timedelta(days=i), False, False)
                      for i in range(20)])
    assert kw.kalenderdekking(lang, vandaag).uitkomst == "goed"


def test_drempelrand_ziet_een_dubbeltje_op_zijn_kant():
    # Negen maandagen: acht op 100, één op 10,50 — vlak bij de drempel van 10.
    maandagen = [D(2026, 3, 2) + dt.timedelta(weeks=i) for i in range(9)]
    verkopen = _verkopen(
        [_winkelrij(d, omzet=100.0) for d in maandagen[:8]]
        + [_winkelrij(maandagen[8], omzet=10.5)]
    )
    w = kw.drempelrand(verkopen)
    assert w.uitkomst == "let_op"
    assert maandagen[8].isoformat() in w.toelichting

    zonder = _verkopen([_winkelrij(d, omzet=100.0) for d in maandagen])
    assert kw.drempelrand(zonder).uitkomst == "goed"


# --- de wachters op bon- en uurniveau (O23) --------------------------------


def _bonnen(rijen):
    return pd.DataFrame(rijen, columns=["datum", "filiaal_id", "bonnen"])


def _uren(rijen):
    return pd.DataFrame(
        rijen, columns=["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"]
    )


START = D(2026, 5, 1)


def _dekkingsdagen(aantal=6, start=START):
    return [start + dt.timedelta(days=i) for i in range(aantal)]


def test_bonnen_omzetdekking_ziet_een_dag_met_omzet_zonder_bonnen():
    dagen = _dekkingsdagen()
    verkopen = _verkopen([_winkelrij(d) for d in dagen])
    kal = _kalender([(d, True, True) for d in dagen])
    # De bonnentelling mist dag 4, midden in het bereik: een gat, geen achterstand.
    bonnen = _bonnen([(d, "Kassa 1", 12) for d in dagen if d.day != 4])
    w = kw.bonnen_omzetdekking(verkopen, bonnen, kal)
    assert w.uitkomst == "fout"
    assert "2026-05-04" in w.toelichting
    assert "€ 100,00" in w.toelichting  # het bedrag dat uit het bonritme valt

    volledig = _bonnen([(d, "Kassa 1", 12) for d in dagen])
    goed = kw.bonnen_omzetdekking(verkopen, volledig, kal)
    assert goed.uitkomst == "goed"
    assert "6 dag(en)" in goed.toelichting


def test_bonnen_omzetdekking_ziet_een_dag_met_bonnen_zonder_verkoopregels():
    # Het verkoopextract mist dag 4. De kalender is uit diezelfde verkopen
    # gebouwd en leest dat als een sluiting; de bonnen zijn de enige getuige
    # dat er die dag wel degelijk over de toonbank ging.
    dagen = _dekkingsdagen()
    verkopen = _verkopen([_winkelrij(d) for d in dagen if d.day != 4])
    kal = _kalender([(d, True, d.day != 4) for d in dagen])
    bonnen = _bonnen([(d, "Kassa 1", 12) for d in dagen])
    w = kw.bonnen_omzetdekking(verkopen, bonnen, kal)
    assert w.uitkomst == "fout"
    assert "2026-05-04" in w.toelichting


def test_bonnen_omzetdekking_slaat_geen_alarm_op_sluiting_en_achterstand():
    dagen = _dekkingsdagen(aantal=10)
    # Dag 4 en 5 gesloten: in beide extracties leeg, dus geen alarm.
    open_dagen = [d for d in dagen if d.day not in (4, 5)]
    verkopen = _verkopen([_winkelrij(d) for d in open_dagen])
    kal = _kalender([(d, True, d.day not in (4, 5)) for d in dagen])
    # De bonnenextractie loopt drie dagen achter: dat verkort het bereik.
    bonnen = _bonnen([(d, "Kassa 1", 12) for d in open_dagen if d.day <= 7])
    w = kw.bonnen_omzetdekking(verkopen, bonnen, kal)
    assert w.uitkomst == "goed"
    assert "2 gemeten gesloten dag(en)" in w.toelichting
    assert "achterstand, geen gat" in w.toelichting


def test_bonnen_omzetdekking_verdraagt_een_gesloten_dag_met_losse_bonnen():
    # De drempelregel maakt een dag met verwaarloosbare omzet dicht, niet leeg:
    # dag 4 heeft één bonregel van € 3 en twee bonnen. Beide extracties zien
    # hem, dus dat is geen mismatch — anders stond deze wachter permanent rood.
    dagen = _dekkingsdagen()
    verkopen = _verkopen(
        [_winkelrij(d) for d in dagen if d.day != 4]
        + [(D(2026, 5, 4), "Kassa 1", "7", "Brood", "winkel", 1.0, 3.0)]
    )
    kal = _kalender([(d, True, d.day != 4) for d in dagen])
    bonnen = _bonnen([(d, "Kassa 1", 2 if d.day == 4 else 12) for d in dagen])
    w = kw.bonnen_omzetdekking(verkopen, bonnen, kal)
    assert w.uitkomst == "goed"
    assert "6 dag(en)" in w.toelichting


def test_bonnen_omzetdekking_verdraagt_afwezige_bonnen():
    dagen = _dekkingsdagen()
    verkopen = _verkopen([_winkelrij(d) for d in dagen])
    kal = _kalender([(d, True, True) for d in dagen])
    for leeg in (None, _bonnen([])):
        w = kw.bonnen_omzetdekking(verkopen, leeg, kal)
        assert w.uitkomst == "goed"
        assert "Niet gecontroleerd" in w.toelichting
    stuk = pd.DataFrame({"dag": [D(2026, 5, 1)], "aantal": [3]})
    assert kw.bonnen_omzetdekking(verkopen, stuk, kal).uitkomst == "fout"


def _urenreeks(dagen, laatste_uren, product_id=1, bonnen=20):
    """Eén rij per dag voor één product; `laatste_uren` mag een lijst zijn."""
    if isinstance(laatste_uren, int):
        laatste_uren = [laatste_uren] * len(dagen)
    return [(d, product_id, 7, uur, bonnen)
            for d, uur in zip(dagen, laatste_uren, strict=True)]


def _censureringsdata(dagen, uren_a, uren_b):
    """Twee producten: A draagt het signaal, B houdt de winkelsluiting op 17u."""
    return _uren(_urenreeks(dagen, uren_a, product_id=1)
                 + _urenreeks(dagen, uren_b, product_id=9))


def test_censureringsdrempel_ziet_een_verschuiving_in_het_leeg_reksignaal():
    # 150 open dagen: precies genoeg (90 recent + 60 ervoor). In de eerste 60
    # is product 1 nooit vroeg op, in de laatste 90 elke dag — dat is een
    # verschuiving van 0 naar 100%, ver voorbij de marge.
    dagen = _dekkingsdagen(aantal=150, start=D(2026, 1, 1))
    kal = _kalender([(d, True, True) for d in dagen])
    uren = _censureringsdata(dagen, [17] * 60 + [10] * 90, [17] * 150)
    w = kw.censureringsdrempel(uren, kal)
    assert w.uitkomst == "let_op"
    assert "procentpunt" in w.toelichting
    assert dagen[-1].isoformat() in w.toelichting


def test_censureringsdrempel_zwijgt_bij_een_stabiel_aandeel():
    # Elke tiende dag is product 1 vroeg op, over de hele reeks: ~10% in beide
    # periodes, dus geen verschuiving.
    dagen = _dekkingsdagen(aantal=150, start=D(2026, 1, 1))
    kal = _kalender([(d, True, True) for d in dagen])
    uren = _censureringsdata(
        dagen, [10 if i % 10 == 0 else 17 for i in range(150)], [17] * 150
    )
    w = kw.censureringsdrempel(uren, kal)
    assert w.uitkomst == "goed"
    assert "binnen de" in w.toelichting


def test_censureringsdrempel_telt_in_meetdagen_en_niet_in_kalenderdagen():
    # Vier weken sluiting midden in de reeks. De vensters lopen over gemeten
    # open dagen, dus de sluiting verschuift niets en de wachter zwijgt.
    dagen = _dekkingsdagen(aantal=178, start=D(2026, 1, 1))
    gesloten = set(dagen[60:88])
    open_dagen = [d for d in dagen if d not in gesloten]
    kal = _kalender([(d, True, d not in gesloten) for d in dagen])
    uren = _censureringsdata(
        open_dagen,
        [10 if i % 10 == 0 else 17 for i in range(len(open_dagen))],
        [17] * len(open_dagen),
    )
    w = kw.censureringsdrempel(uren, kal)
    assert w.uitkomst == "goed"
    assert f"laatste {kw.CENSURERING_VENSTER} gemeten open dagen" in w.toelichting


def test_censureringsdrempel_vergelijkt_niet_op_een_korte_reeks():
    dagen = _dekkingsdagen(aantal=100, start=D(2026, 1, 1))
    kal = _kalender([(d, True, True) for d in dagen])
    uren = _censureringsdata(dagen, [17] * 40 + [10] * 60, [17] * 100)
    w = kw.censureringsdrempel(uren, kal)
    assert w.uitkomst == "goed"
    assert "Niet vergeleken" in w.toelichting


def test_censureringsdrempel_verdraagt_afwezige_uren():
    kal = _kalender([(D(2026, 5, 1) + dt.timedelta(days=i), True, True)
                     for i in range(14)])
    for leeg in (None, _uren([])):
        w = kw.censureringsdrempel(leeg, kal)
        assert w.uitkomst == "goed"
        assert "Niet gecontroleerd" in w.toelichting
    stuk = pd.DataFrame({"datum": [D(2026, 5, 1)], "product_id": [1]})
    assert kw.censureringsdrempel(stuk, kal).uitkomst == "fout"
    # Zonder open dagen in de kalender valt er niets te meten, en dat is geen fout.
    dicht = _kalender([(D(2026, 5, 1) + dt.timedelta(days=i), True, False)
                       for i in range(14)])
    volle_uren = _censureringsdata(_dekkingsdagen(), [17] * 6, [17] * 6)
    assert kw.censureringsdrempel(volle_uren, dicht).uitkomst == "goed"


def test_stand_serialiseert_datums_naar_iso():
    tot = D(2026, 5, 10)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender([(tot - dt.timedelta(days=i), True, True) for i in range(14)])
    uit = kw.stand(verkopen, kal, vandaag=D(2026, 5, 11))
    kassa = next(b for b in uit["bronnen"] if b["bron"] == "odoo-kassa")
    assert kassa["laatste_meetdag"] == "2026-05-10"
    # `>=` en niet `==` sinds 19 augustus 2026: deze test gaat over ISO-datums,
    # niet over het aantal wachters. Met een vast aantal brak een achtste
    # wachter deze test terwijl er niets stuk was -- een rood dat je leert
    # wegklikken. Dat het aantal niet nul is, is hier het enige dat telt.
    assert len(uit["wachters"]) >= 7
    assert all(w["uitkomst"] in ("goed", "let_op", "fout") for w in uit["wachters"])
    namen = [w["naam"] for w in uit["wachters"]]
    assert namen[-2:] == ["bonnen_omzetdekking", "censureringsdrempel"]
    # Zonder bonnen- en urenextract blijven de twee nieuwe wachters stil: een
    # alarm op een optionele extractie zou permanent afgaan.
    assert all(w["toelichting"] for w in uit["wachters"])
    nieuw = [w for w in uit["wachters"] if w["naam"] in namen[-2:]]
    assert all(w["uitkomst"] == "goed" for w in nieuw)
    assert all("Niet gecontroleerd" in w["toelichting"] for w in nieuw)


def test_elke_wachter_heeft_een_leesbaar_label_in_de_briefing():
    """Voorkomt dat een machinenaam op het scherm van de klant belandt.

    `briefing.WACHTERLABELS` vertaalt de sleutel van een wachter naar iets wat
    een mens leest, en `briefing._wachterlabel` valt bij een onbekende sleutel
    terug op de sleutel zelf. Die terugval geeft geen fout en geen waarschuwing:
    ze zet doodleuk "censureringsdrempel" op de instellingenpagina. Tot
    19 augustus 2026 was er geen enkele koppeling tussen de twee lijsten, dus
    een achtste wachter in `kwaliteit.wachters()` zou stil zijn eigen
    machinenaam publiceren.

    De test legt de twee verzamelingen naast elkaar in plaats van het aantal te
    tellen: wie een wachter toevoegt, hernoemt of weghaalt, wordt hier gestuit
    met de naam die ontbreekt.
    """
    from bakkerij.briefing import WACHTERLABELS, _wachterlabel

    tot = D(2026, 5, 10)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender([(tot - dt.timedelta(days=i), True, True) for i in range(14)])
    namen = {w.naam for w in kw.wachters(verkopen, kal, vandaag=D(2026, 5, 11))}

    assert namen, "kwaliteit.wachters() leverde niets — dan meet deze test niets"
    assert namen == set(WACHTERLABELS), (
        f"zonder label: {sorted(namen - set(WACHTERLABELS))}; "
        f"label zonder wachter: {sorted(set(WACHTERLABELS) - namen)}"
    )
    # En de terugval is echt nooit nodig: geen enkel label is de machinenaam.
    for naam in namen:
        assert _wachterlabel(naam) != naam


def test_de_stand_bestaat_in_het_frans_zonder_nederlandse_resten():
    """Tweetaligheid als gedrag: dezelfde bouw in Franse context levert Franse
    toelichtingen, met dezelfde statussleutels (machinewaarden) als in het
    Nederlands. Er wordt niet op volzinnen getoetst maar op kernwoorden die in
    elke Nederlandse variant voorkomen — dat overleeft een herformulering."""
    from bakkerij import taal as tl

    tot = D(2026, 5, 10)
    verkopen = _verkopen(_week_verkopen(tot))
    kal = _kalender([(tot - dt.timedelta(days=i), True, True) for i in range(14)])

    nl = kw.stand(verkopen, kal, vandaag=D(2026, 5, 11))
    with tl.in_taal("fr"):
        fr = kw.stand(verkopen, kal, vandaag=D(2026, 5, 11))

    # Dezelfde machinewaarden: sleutels, namen en oordelen veranderen niet mee.
    assert [w["naam"] for w in fr["wachters"]] == [w["naam"] for w in nl["wachters"]]
    assert [w["uitkomst"] for w in fr["wachters"]] == [w["uitkomst"] for w in nl["wachters"]]
    assert [b["status"] for b in fr["bronnen"]] == [b["status"] for b in nl["bronnen"]]

    nederlands = ("gecontroleerd", "ingeladen", "dagen", "rijen", "meting",
                  "aangeleverd", "bonnentelling")
    teksten = ([w["toelichting"] for w in fr["wachters"]]
               + [b["toelichting"] for b in fr["bronnen"]])
    for tekst in teksten:
        laag = tekst.lower()
        for woord in nederlands:
            assert woord not in laag, (tekst, woord)
