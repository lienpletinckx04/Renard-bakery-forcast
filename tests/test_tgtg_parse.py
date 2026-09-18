"""Tests op de TGTG-parser.

Alle teksten hier zijn verzonnen en nagebouwd naar de vorm van de documenten.
Er staat bewust geen enkele echte klantregel in: de tests moeten in de repo
kunnen staan zonder dat er verkoopcijfers van de eindklant in git belanden.
"""
import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from bakkerij.sources.tgtg_parse import (
    TgtgFormaatFout,
    id_uit_pad,
    klopt_met_maand,
    lees_bedrag,
    lees_datum,
    maand_uit_pad,
    parse_factuur,
    parse_rekeningoverzicht,
    parse_verkoopoverzicht,
)

VERKOOP = """\
Verkoopoverzicht Voorbeeldzaak , mei 2024

Datum                         Nummer bestelling            Nummer document              Aantal eenheden

1/05/2024                         aa1bbcc2d3ee4              abcd_1111-22222                            1

3/05/2024                         bb2ccdd3e4ff5              abcd_1111-22223                            2

31/05/2024                        cc3ddee4f5gg6              abcd_1111-22224                            1
"""

FACTUUR = """\
Factuur
Voorbeeld BVBA

         Aantal   Omschrijving                                      Verkoopprijs (EUR)    Totaal
            42    Verkochte pakketten 1/5 - 31/5, winkel               € 1,79            € 75,18

Netto bedrag                                                                             € 75,18
BTW, 21 %                                                                                € 15,79
Totale kosten                                                                            € 90,97
"""

REKENING = """\
Accountoverzicht
Voorbeeld BVBA

Datum           Omschrijving                                 Boekstuk       Bedrag
01/05/2024      Saldo                                               0       € 0,00
31/05/2024      42 verkochte items, winkel                     1234567      -€ 209,58

Totaal (negatief getal = wat je krijgt van Too Good To Go)                   -€ 209,58
"""


# --- de oudere bouwjaren -----------------------------------------------------
# 2020 en eerder: datums met streepjes, kopregelletters uit elkaar getrokken,
# euroteken achteraan.
VERKOOP_2020 = """\
Verkoopoverzicht voor Voorbeeldzaak, 01/06 2020-30/06 2020

Datu m                     N u mmer b estellin g       N u mmer d o cu men t      A an tal een h ed en :   Bed rag:
01-06-2020                         aabbccddeef         TGTG-1234567-8901                              1     4,99 €
15-06-2020                         bbccddeeffg         TGTG-1234567-8902                              2     9,98 €
"""

# 2021: jaartal met twee cijfers.
VERKOOP_2021 = """\
Verkoopoverzicht Voorbeeldzaak, september 2021

Datum                     Nummer bestelling            Nummer document           Aantal eenheden        Bedrag
1/09/21                        aabbccddeef             TGTG-1234567-8901                       1        4,99 €
30/09/21                       bbccddeeffg             TGTG-1234567-8902                       1        4,99 €
"""

# Factuur van vóór 2023: geen euroteken, artikelregel heet 'Servicekosten'.
FACTUUR_2020 = """\
Factuur
Voorbeeld BVBA
       Aantal Omschrijving                                     Verkoopprijs        Totaal
          123 Servicekosten 01/06 - 30/06, Voorbeeldzaak               1,19        146,37
Netto bedrag                                                                       146,37
"""


def test_oud_formaat_2020_streepjesdatum_en_euro_achteraan():
    regels = parse_verkoopoverzicht(VERKOOP_2020)
    assert [r.datum for r in regels] == [datetime.date(2020, 6, 1), datetime.date(2020, 6, 15)]
    assert sum(r.aantal for r in regels) == 3
    assert regels[1].bedrag == Decimal("9.98")


def test_oud_formaat_2021_jaartal_van_twee_cijfers():
    regels = parse_verkoopoverzicht(VERKOOP_2021)
    assert [r.datum for r in regels] == [datetime.date(2021, 9, 1), datetime.date(2021, 9, 30)]
    assert klopt_met_maand(regels, 2021, 9) == regels


def test_oude_factuur_zonder_euroteken():
    f = parse_factuur(FACTUUR_2020)
    assert f.aantal == 123
    assert f.prijs_per_stuk == Decimal("1.19")


def test_nieuw_formaat_heeft_bedrag_per_bestelling():
    regels = parse_verkoopoverzicht(VERKOOP_MET_PRIJS)
    assert regels[0].bedrag == Decimal("4.99")


VERKOOP_MET_PRIJS = """\
Verkoopoverzicht Voorbeeldzaak , mei 2024

Datum                         Nummer bestelling            Nummer document              Aantal eenheden

1/05/2024                         aa1bbcc2d3ee4              abcd_1111-22222                            1          € 4,99
"""


def test_bedragen():
    assert lees_bedrag("€ 1,79") == Decimal("1.79")
    assert lees_bedrag("-€ 209,58") == Decimal("-209.58")
    assert lees_bedrag("€ 1.234,56") == Decimal("1234.56")
    assert lees_bedrag("geen bedrag") is None


def test_datum_is_dag_eerst():
    # 3/05 is 3 mei, niet 5 maart. Dat onderscheid is de gevaarlijkste leesfout.
    assert lees_datum("3/05/2024") == datetime.date(2024, 5, 3)
    assert lees_datum("31/05/2024") == datetime.date(2024, 5, 31)
    assert lees_datum("geen datum") is None


def test_verkoopoverzicht():
    regels = parse_verkoopoverzicht(VERKOOP)
    assert len(regels) == 3
    assert sum(r.aantal for r in regels) == 4
    assert regels[0].datum == datetime.date(2024, 5, 1)
    assert regels[0].documentnummer == "abcd_1111-22222"


def test_verkoopoverzicht_zonder_kopregel_faalt_luid():
    # Een gewijzigd documentformaat moet een fout geven en geen lege maand.
    with pytest.raises(TgtgFormaatFout):
        parse_verkoopoverzicht("Verkoopoverzicht\n\nniets bruikbaars hier\n")


def test_verkoopoverzicht_zonder_regels_faalt_luid():
    with pytest.raises(TgtgFormaatFout):
        parse_verkoopoverzicht("Datum  Nummer bestelling  Aantal eenheden\n")


def test_factuur():
    f = parse_factuur(FACTUUR)
    assert f.aantal == 42
    assert f.prijs_per_stuk == Decimal("1.79")
    assert f.netto == Decimal("75.18")
    assert f.totaal == Decimal("90.97")


def test_rekeningoverzicht_geeft_uitbetaling_positief():
    assert parse_rekeningoverzicht(REKENING) == Decimal("209.58")


def test_rekeningoverzicht_positief_saldo_is_geen_uitbetaling():
    tekst = REKENING.replace("-€ 209,58\n", "€ 12,00\n")
    assert parse_rekeningoverzicht(tekst) == Decimal("0.00")


def test_maandcontrole_vangt_omgewisselde_dag_en_maand():
    regels = parse_verkoopoverzicht(VERKOOP)
    assert klopt_met_maand(regels, 2024, 5) == regels
    with pytest.raises(TgtgFormaatFout, match="dag/maand"):
        klopt_met_maand(regels, 2024, 3)


def test_pad_ontleding():
    pad = Path("data/raw/TGTG overzicht/TGTG-Export(3)/2024-05/storeId 8113/itemId 8191/x.pdf")
    assert maand_uit_pad(pad) == (2024, 5)
    assert id_uit_pad(pad, "storeId") == "8113"
    assert id_uit_pad(pad, "itemId") == "8191"
