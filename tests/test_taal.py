"""De taallaag van de berekening: labels volgen de taal, cijfers niet.

Aanleiding, 14 augustus 2026: de bakkerij staat in Elsene en het platform moet
tweetalig zijn. Omdat elk label dat een mens leest uit de berekeningslaag komt
(harde regel 4), kan de UI dat niet zelf oplossen — het contract wordt per taal
gebouwd.
"""

import datetime as dt

import pytest

from bakkerij import taal as tl


def test_standaard_is_nederlands():
    assert tl.huidige_taal() == "nl"
    assert tl.t("Omzet", "Chiffre d'affaires") == "Omzet"


def test_in_taal_wisselt_en_zet_terug():
    with tl.in_taal("fr"):
        assert tl.t("Omzet", "Chiffre d'affaires") == "Chiffre d'affaires"
        assert tl.is_frans()
    assert tl.huidige_taal() == "nl"
    assert not tl.is_frans()


def test_in_taal_zet_terug_ook_na_een_fout():
    """Anders lekt een halve bouw zijn taal in de volgende."""
    with pytest.raises(RuntimeError), tl.in_taal("fr"):
        raise RuntimeError("iets ging mis tijdens het bouwen")
    assert tl.huidige_taal() == "nl"


def test_een_onbekende_taal_is_een_fout_en_geen_terugval():
    with pytest.raises(ValueError, match="Onbekende taal"), tl.in_taal("de"):
        pass


def test_een_ontbrekende_vertaling_blokkeert_niets_maar_wordt_gemeld():
    """De cijfers gaan voor. Maar stil mag het niet zijn.

    Een ontbrekende vertaling die de bouw stopt, zou betekenen dat één
    onvertaald label het hele contract kost. Een ontbrekende vertaling die
    niemand meldt, betekent dat er nooit iemand naar kijkt.
    """
    tl.ONVERTAALD.clear()
    with tl.in_taal("fr"):
        assert tl.t("Nog niet vertaald") == "Nog niet vertaald"
    assert "Nog niet vertaald" in tl.ONVERTAALD
    tl.ONVERTAALD.clear()


def test_in_het_nederlands_komt_er_niets_in_de_meldlijst():
    tl.ONVERTAALD.clear()
    tl.t("Alleen Nederlands")
    assert tl.ONVERTAALD == set()


def test_maanden_en_weekdagen_in_beide_talen():
    assert tl.maand_vol(8) == "augustus"
    assert tl.maand_kort(8) == "aug"
    assert tl.weekdag(0) == "maandag"
    assert tl.weekdag_kort(0) == "ma"
    with tl.in_taal("fr"):
        assert tl.maand_vol(8) == "août"
        assert tl.maand_kort(8) == "août"
        assert tl.weekdag(0) == "lundi"
        assert tl.weekdag_kort(0) == "lu"


def test_dagnummer_is_alleen_in_het_frans_een_rangtelwoord():
    """'1er janvier' maar '2 janvier'; het Nederlands schrijft altijd het getal."""
    assert tl.dagnummer(1) == "1"
    assert tl.dagnummer(2) == "2"
    with tl.in_taal("fr"):
        assert tl.dagnummer(1) == "1er"
        assert tl.dagnummer(2) == "2"
        assert tl.dagnummer(31) == "31"


def test_elke_maand_en_weekdag_bestaat_in_beide_talen():
    for tabel in (tl.MAANDEN_VOL, tl.MAANDEN_KORT):
        assert len(tabel["nl"]) == len(tabel["fr"]) == 12
        assert all(naam for naam in tabel["nl"] + tabel["fr"])
    for tabel in (tl.WEEKDAGEN, tl.WEEKDAGEN_KORT):
        assert len(tabel["nl"]) == len(tabel["fr"]) == 7
        assert all(naam for naam in tabel["nl"] + tabel["fr"])


def test_merknamen_blijven_staan():
    """"Too Good To Go" heet in het Frans ook Too Good To Go.

    Een vertaald kanaal zou een naam tonen die in geen enkele afrekening
    voorkomt, en dan klopt het scherm niet meer met het document ernaast.
    """
    with tl.in_taal("fr"):
        assert tl.kanaalnaam("tgtg") == "Too Good To Go"
        assert tl.kanaalnaam("deliveroo") == "Deliveroo"
        assert tl.kanaalnaam("winkel") == "Magasin"
        assert tl.kanaalnaam("overig") == "Autres"


def test_een_onbekend_kanaal_komt_ongewijzigd_terug():
    assert tl.kanaalnaam("nieuwkanaal") == "nieuwkanaal"


# --- en de doorwerking in het contract --------------------------------------


def test_het_contract_bouwt_dezelfde_cijfers_in_beide_talen():
    """De kern van de belofte: één waarheid, twee talen.

    Als de cijfers per taal zouden verschillen, was de vertaling een tweede
    berekening geworden — en dan is er geen contract meer maar zijn er twee.
    """
    from bakkerij import contract as ct

    def bouw():
        return ct._datum_nl(dt.date(2026, 8, 17)), ct._dagen_nl(7)

    nl_datum, nl_dagen = bouw()
    with tl.in_taal("fr"):
        fr_datum, fr_dagen = bouw()

    assert nl_datum == "17 augustus 2026"
    assert fr_datum == "17 août 2026"
    assert nl_dagen == "7 dagen"
    assert fr_dagen == "7 jours"


def test_een_enkele_dag_krijgt_het_enkelvoud_in_beide_talen():
    from bakkerij import contract as ct

    assert ct._dagen_nl(1) == "1 dag"
    with tl.in_taal("fr"):
        assert ct._dagen_nl(1) == "1 jour"


# --- percentages in proza ----------------------------------------------------


def test_procent_tekst_volgt_de_notatie_van_de_tabellen():
    """Komma als decimaalteken en een gewone spatie vóór het procentteken,
    exact zoals `platform/lib/format.ts` (procent) de machinewaarden opmaakt.
    De visuele steekproef van 17 augustus 2026 vond "7,8%" en "80,0%" in het
    proza naast "8,1 %" in de tabellen — twee notaties op één scherm."""
    assert tl.procent_tekst(0.078) == "7,8 %"
    assert tl.procent_tekst(0.8) == "80,0 %"
    assert tl.procent_tekst(0.10, decimalen=0) == "10 %"


def test_procent_tekst_is_in_beide_talen_gelijk():
    """Getallen en bedragen blijven gelijk opgemaakt over de talen heen; zie
    de noot in platform/lib/taal.ts."""
    nl = tl.procent_tekst(0.078)
    with tl.in_taal("fr"):
        assert tl.procent_tekst(0.078) == nl
