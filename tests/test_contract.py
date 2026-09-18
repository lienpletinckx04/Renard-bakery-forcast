"""Tests voor de contractlaag.

De vorm is gebonden in `platform/lib/contract.ts`. Deze tests bewaken die vorm
vanaf de Python-kant, want als de twee uit elkaar lopen, breekt het scherm pas
in de browser en niet in de build.

Wat hier vooral bewaakt wordt:
  * geen enkel bedrag verlaat het contract als float
  * `onbeschikbaar` is gevuld wanneer een cijfer ontbreekt, en niet leeg
  * de y-as komt uit de berekening, niet uit de frontend
  * de enveloppe draagt de versheid van de data (`gemeten_tot`), niet alleen het
    moment van bouwen
  * de prognose gaat over dagen die nog moeten komen en waarop de winkel open kan
    zijn — niet over een voorbije week met een zomersluiting erin
"""
import datetime
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij import berekening as bk
from bakkerij import canoniek
from bakkerij import contract as ct
from bakkerij import kostenmodel as km
from bakkerij import taal as tl

BIJGEWERKT = datetime.datetime(2026, 8, 12, 4, 0, tzinfo=ct.TIJDZONE)
METHODE = "gemiddelde van de laatste vier gelijke weekdagen"


def _verkopen(rijen) -> pd.DataFrame:
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": "Kassa 1",
          "product_id": p, "product_naam": n, "kanaal": k,
          "aantal": a, "omzet_excl_btw": o}
         for d, p, n, k, a, o in rijen]
    )


def _kalender_van(dagtotalen: pd.DataFrame) -> pd.DataFrame:
    """Een kalender waarin elke gemeten dag een open dag is.

    Voor de fixtures die geen sluitingen kennen. `ct.overzicht` heeft de
    kalender nodig voor het weekritme: uit de dagtotalen alleen is een week
    zonder rijen niet te onderscheiden van een week die buiten het meetbereik
    ligt.
    """
    dagen = pd.DatetimeIndex(sorted(dagtotalen["datum"].unique()))
    return pd.DataFrame({"datum": dagen, "winkel_gemeten": True,
                         "winkel_open": True})


def _overzicht(dagtotalen: pd.DataFrame, tot: pd.Timestamp, **kw) -> dict:
    """`ct.overzicht` met de twee toebehoren ingevuld.

    De kalender en de bonnentelling zijn verplichte argumenten van het echte
    antwoord — bewust zonder standaardwaarde, want een blok dat stilzwijgend
    verdwijnt omdat een aanroeper iets vergat, is precies wat harde regel 8
    verbiedt. Deze wrapper vult ze voor de tests die er niet over gaan.
    """
    kw.setdefault("kalender", _kalender_van(dagtotalen))
    kw.setdefault("bonnen", None)
    return ct.overzicht(dagtotalen, tot, **kw)


def _bonnen(rijen) -> pd.DataFrame:
    """rijen: (datum, aantal bonnen). Eén kassa; de som per dag mag."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": "Kassa 1",
          "bonnen": n}
         for d, n in rijen]
    )


def _twee_jaar() -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Twee volledige jaren dagomzet, zodat jaar-op-jaar bestaat."""
    dagen = pd.date_range("2025-01-01", "2026-06-30", freq="D")
    patroon = [1000.0, 950.0, 1000.0, 1050.0, 1300.0, 1600.0, 900.0]
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, patroon[d.dayofweek])
        for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    return open_v, bk.dagtotalen(open_v), bk.peildatum(open_v)


def _venster(dagen: int = 3, *, gemeten_tot="2026-06-30",
             vandaag="2026-06-30") -> canoniek.Prognosevenster:
    """Een prognosevenster zonder sluitingen, om de contractvorm te toetsen."""
    kal = pd.DataFrame({
        "datum": pd.date_range("2026-06-01", "2026-07-31", freq="D").date,
        "winkel_gemeten": False,
        "winkel_open": False,
    })
    kal.loc[kal["datum"] <= datetime.date.fromisoformat(str(gemeten_tot)),
            ["winkel_gemeten", "winkel_open"]] = True
    return canoniek.prognosevenster(kal, gemeten_tot=gemeten_tot,
                                    vandaag=vandaag, horizon=dagen)


def _blik(datums, verwacht=1000.0) -> pd.DataFrame:
    return pd.DataFrame({
        "datum": pd.DatetimeIndex(datums),
        "verwacht": [verwacht] * len(datums),
        "onder": [verwacht * 0.9] * len(datums),
        "boven": [verwacht * 1.1] * len(datums),
    })


def _alle_getallen(knoop, pad="") -> list[tuple[str, object]]:
    """Elk blad in de boom, met zijn pad. Om op types te kunnen toetsen."""
    uit = []
    if isinstance(knoop, dict):
        for k, v in knoop.items():
            uit += _alle_getallen(v, f"{pad}.{k}")
    elif isinstance(knoop, list):
        for i, v in enumerate(knoop):
            uit += _alle_getallen(v, f"{pad}[{i}]")
    else:
        uit.append((pad, knoop))
    return uit


# --- de envelope ------------------------------------------------------------

def test_envelope_heeft_alle_verplichte_velden():
    a = ct.antwoord({"x": 1}, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    gemeten_tot=pd.Timestamp("2026-07-31"))
    assert set(a) == {"versie", "bijgewerkt_op", "gemeten_tot", "bron",
                      "onbeschikbaar", "briefing", "data"}
    # De briefing is standaard leeg en nooit afwezig: de UI hoeft niet te raden
    # of een scherm er een heeft.
    assert a["briefing"] == {"punten": [], "leeg": ""}
    # Letterlijk en niet ct.VERSIE: wie de versie ophoogt, breekt bewust het
    # contract en hoort dat hier te voelen (audit 15 aug, punt d).
    assert a["versie"] == 1
    assert a["onbeschikbaar"] == []
    assert a["bijgewerkt_op"].startswith("2026-08-12T04:00")
    assert a["gemeten_tot"] == "2026-07-31"


def test_gemeten_tot_is_verplicht_en_mag_expliciet_niets_zijn():
    """Vergeten mag niet, leeg mag wel.

    De voettekst presenteerde `bijgewerkt_op` als de versheid van de data, terwijl
    de jongste verkoopdag twaalf dagen ouder was. Een enveloppe zonder
    `gemeten_tot` hoort daarom niet te bouwen; is er geen gemeten dag, dan staat
    er null en toont het scherm dat als onbekend.
    """
    with pytest.raises(TypeError):
        ct.antwoord({}, bron=["odoo"], bijgewerkt_op=BIJGEWERKT)
    leeg = ct.antwoord({}, bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=None)
    assert leeg["gemeten_tot"] is None


# --- de datasleutels, tegenover platform/lib/contract.ts --------------------

#: Per antwoord de velden die `data` hoort te dragen, met daarnaast het type in
#: `platform/lib/contract.ts` dat ze aan de leeskant beschrijft.
#:
#: WAAROM DEZE LIJST BESTAAT. Het contract heeft twee handgeschreven
#: definities: deze module bouwt hem, en `platform/lib/contract.ts` beschrijft
#: hem. Er was niets dat de twee naast elkaar legde. `laadContract.ts` doet een
#: kale `as Antwoord<T>` zonder runtimecontrole, en de tests hier pinden alleen
#: de ENVELOPPE (versie, bron, briefing, …) — nooit de inhoud. Hernoemde je in
#: `bakkerij/contract.py` een veld, dan bleven pytest, ruff, tsc en `next build`
#: alle vier groen, en zag je het pas als er in de browser `undefined` stond.
#: De contractbestanden zijn bovendien gitignored (het zijn klantcijfers), dus
#: een controle in CI op de gebouwde JSON kán niet.
#:
#: Deze lijst is de goedkoopste koppeling die dat gat dicht: geen codegeneratie,
#: geen gecommitte JSON, geen TypeScript in de Python-tests. Wie hier een veld
#: bijzet of hernoemt, moet dat bewust doen — en de foutmelding hieronder wijst
#: hem naar het bestand dat mee moet.
DATASLEUTELS = {
    "overzicht": (
        "OverzichtData",
        {
            "afwijkende_dagen", "bonritme", "jaarvergelijking", "kerncijfers",
            "maandritme", "omzetverloop", "omzetverloop_context", "periodes",
            "weekdagmix", "weekdagprofiel", "weken",
        },
    ),
    "kanalen": ("KanalenData", {"kanalen"}),
    "producten": (
        "ProductenData",
        {
            "concentratie", "groepen", "groepen_detail", "prijs_volume",
            "top", "verschuiving",
        },
    ),
    "prognose": (
        "PrognoseData",
        {
            "categorieen", "dagen", "grafiek", "modelkaart", "trackrecord",
            "weektotaal", "weektotaal_dagen",
        },
    ),
    "sluitingsdagen": (
        "SluitingsdagenData",
        {"bestandsdekking_tekst", "bestandsdekking_tot", "kandidaten"},
    ),
}


def test_de_datasleutels_staan_vast_tegenover_het_typebestand():
    open_v, totalen, tot = _twee_jaar()
    venster = _venster()
    gebouwd = {
        "overzicht": _overzicht(totalen, tot, bron=["odoo"],
                                bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                                prognose_methode=METHODE),
        "kanalen": ct.kanalen(totalen, tot, bron=["odoo"],
                              bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                              ontbrekend={}),
        "producten": ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                                  bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                                  gemeten_tot=tot),
        "prognose": ct.prognose(_blik(venster.dagen), bron=["odoo"],
                                bijgewerkt_op=BIJGEWERKT,
                                baseline_naam=METHODE, wape=0.084,
                                venster=venster),
        "sluitingsdagen": ct.sluitingsdagen(
            vandaag=datetime.date(2026, 6, 30),
            sluitingsdekking=datetime.date(2026, 8, 23),
            bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot),
    }

    for naam, (tstype, verwacht) in DATASLEUTELS.items():
        assert set(gebouwd[naam]["data"]) == verwacht, (
            f"De datasleutels van het antwoord '{naam}' zijn veranderd. Dat is "
            f"een contractwijziging: pas `{tstype}` in platform/lib/contract.ts "
            f"mee aan, en daarna de schermen die het veld lezen. Blijft dat "
            f"achterwege, dan leest de UI `undefined` zonder dat één test, "
            f"lint of build het meldt."
        )


def test_marge_zonder_kostenmodel_levert_een_leeg_dataveld():
    """De onbeschikbaar-tak van MargeData, en waarom die leeg mag zijn.

    `MargeData` is in contract.ts een unie: óf de volle vorm, óf
    `Record<string, never>`. Dat laatste is geen vergetelheid maar de tak van
    harde regel 8: zonder ingevuld kostenmodel bestaat er geen marge, en dan
    staat er geen nul en geen streepje maar een onbeschikbaar-vak met de reden
    uit `onbeschikbaar`. Deze test legt vast dat de lege tak écht leeg is —
    een half gevulde `data` zou het scherm laten kiezen, en kiezen is rekenen.
    """
    _, _, tot = _twee_jaar()
    a = ct.marge(bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"] == {}
    assert a["onbeschikbaar"], "een leeg margeveld zonder reden is een gat"


def test_alle_vijf_de_antwoorden_dragen_gemeten_tot():
    open_v, totalen, tot = _twee_jaar()
    venster = _venster()
    antwoorden = [
        _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE),
        ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, ontbrekend={}),
        ct.producten(open_v, pd.Series({"10": "Brood"}), tot, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot),
        ct.marge(bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot),
        ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster),
    ]
    for a in antwoorden:
        assert a["gemeten_tot"] == "2026-06-30"
        # en het moment van bouwen is iets anders dan de versheid van de data
        assert a["bijgewerkt_op"][:10] != a["gemeten_tot"]


# --- geen floats in bedragen ------------------------------------------------

def test_geen_bedrag_verlaat_het_contract_als_float():
    """`number` mag alleen plotgeometrie zijn: punt-y en as-ticks.

    Dit is de regel die het makkelijkst stilletjes sneuvelt, en de duurste om
    later te herstellen: een float in JSON is een afrondingsfout die onderweg
    ontstaat en die niemand meer kan navertellen.
    """
    open_v, totalen, tot = _twee_jaar()
    antwoorden = {
        "overzicht": _overzicht(totalen, tot, bron=["odoo"],
                                  bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                                  prognose_methode=METHODE),
        "kanalen": ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                              gemeten_tot=tot,
                              ontbrekend={"deliveroo": "geen data"}),
        "producten": ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                                  bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                                  gemeten_tot=tot),
    }
    for naam, antwoord in antwoorden.items():
        for pad, waarde in _alle_getallen(antwoord["data"]):
            if isinstance(waarde, float):
                assert pad.endswith(".y") or ".ticks" in pad, (
                    f"{naam}{pad} is een float ({waarde}) maar geen plotgeometrie"
                )


def test_kerncijfers_zijn_strings_met_punt_decimaal():
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)
    for c in a["data"]["kerncijfers"]:
        assert isinstance(c["waarde"], str)
        assert "," not in c["waarde"]
        Decimal(c["waarde"])  # moet ontleedbaar zijn
        assert c["soort"] in ("euro", "aantal")
        assert c["richting"] in ("op", "neer", None)


def test_aantallen_ronden_half_naar_boven_af():
    """Geen bankiersafronding op stuks.

    `round(1234.5)` geeft 1234 en `round(1235.5)` geeft 1236: hetzelfde aantal kan
    dan op twee schermen één stuk verschillen. Aantallen kunnen fractioneel zijn
    (gewichtsproducten), dus dit is geen theoretisch geval.
    """
    assert ct._aantal(1234.5) == "1235"
    assert ct._aantal(1235.5) == "1236"
    assert ct._aantal(0.5) == "1"
    assert round(1234.5) == 1234, "vangt af of Python nog steeds bankiers afrondt"


# --- onbeschikbaar is een antwoord ------------------------------------------

def test_ontbrekende_jaarvergelijking_staat_in_onbeschikbaar():
    """Een kengetal zonder pijl moet uitleggen waarom er geen pijl is."""
    dagen = pd.date_range("2026-01-01", periods=60, freq="D")  # één jaar
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 100.0) for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)

    assert a["onbeschikbaar"], "geen enkele reden gegeven"
    velden = [o["veld"] for o in a["onbeschikbaar"]]
    assert any(v.startswith("kerncijfer.") for v in velden)
    assert all(o["reden"] for o in a["onbeschikbaar"])


def test_kanaal_zonder_data_blijft_in_de_rij_staan_met_reden():
    _, totalen, tot = _twee_jaar()
    a = ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot,
                   ontbrekend={"deliveroo": "Historiek nog niet aangeleverd"})
    kanalen = {k["kanaal"]: k for k in a["data"]["kanalen"]}
    assert set(kanalen) == {"winkel", "deliveroo"}
    assert kanalen["deliveroo"]["omzet_30d"] is None
    assert kanalen["deliveroo"]["verloop"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"] if "deliveroo" in o["veld"])
    assert "aangeleverd" in reden


def test_margescherm_is_leeg_met_twee_redenen():
    a = ct.marge(bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                 gemeten_tot=pd.Timestamp("2026-07-31"))
    assert a["data"] == {}
    assert len(a["onbeschikbaar"]) == 2
    for o in a["onbeschikbaar"]:
        assert "kostprijs" in o["reden"].lower()


# --- de as komt uit de berekening -------------------------------------------

def test_de_y_as_wordt_kant_en_klaar_meegegeven():
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)
    as_ = a["data"]["omzetverloop"]["y_as"]["ticks"]
    assert len(as_) >= 3
    assert as_[0]["y"] == 0
    for tick in as_:
        assert tick["label"].startswith("€")
        assert isinstance(tick["y"], (int, float))


def test_percentage_in_lopende_tekst_gebruikt_komma_en_spatie():
    """De notatie van platform/lib/format.ts (procent): komma als
    decimaalteken en een gewone spatie vóór het procentteken. De visuele
    steekproef van 17 augustus 2026 vond "7,8%" naast "8,1 %" op één scherm."""
    assert ct._pct_tekst(0.084) == "8,4 %"
    assert ct._pct_tekst(0.2019) == "20,2 %"


# --- overzicht: verloopcontext en weekdagprofiel ----------------------------

def test_overzicht_draagt_verloopcontext_en_weekdagprofiel():
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)

    labels = [c["label"] for c in a["data"]["omzetverloop_context"]]
    assert any(l.startswith("Totaal") for l in labels)
    assert any(l.startswith("Beste dag") for l in labels)
    for c in a["data"]["omzetverloop_context"]:
        assert isinstance(c["waarde"], str)
        assert c["soort"] in ("euro", "aantal", "verschil")
        assert c["richting"] in ("op", "neer", None)

    profiel = a["data"]["weekdagprofiel"]
    assert profiel["toelichting"]
    # het patroon van de fixture heeft zeven weekdagen, elk met een gemiddelde
    assert len(profiel["grafiek"]["reeksen"][0]["punten"]) == 7
    assert profiel["grafiek"]["y_as"]["ticks"]


def test_weekdagprofiel_draagt_meetdagen_per_staaf():
    """Een gemiddelde over twee zaterdagen is iets anders dan over acht."""
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)
    punten = a["data"]["weekdagprofiel"]["grafiek"]["reeksen"][0]["punten"]
    for p in punten:
        assert isinstance(p["meetdagen"], int)
        assert p["meetdagen"] >= 1
    # acht volle kalenderweken in de fixture: acht metingen per weekdag —
    # letterlijk, want het profielvenster is een belofte aan de lezer en geen
    # moduleconstante om mee te bewegen (audit 15 aug, punt d)
    assert {p["meetdagen"] for p in punten} == {8}


def test_weekdagprofiel_noemt_de_weekdag_die_ontbreekt():
    """Een vaste sluitingsdag komt niet als nulstaaf en niet stilzwijgend."""
    dagen = pd.date_range("2026-01-01", "2026-06-30", freq="D")
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 1000.0)
        for d in dagen if d.dayofweek != 6           # nooit op zondag open
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    tot = bk.peildatum(open_v)
    a = _overzicht(bk.dagtotalen(open_v), tot, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                     prognose_methode=METHODE)

    punten = a["data"]["weekdagprofiel"]["grafiek"]["reeksen"][0]["punten"]
    assert len(punten) == 6
    assert "zo" not in [p["x"] for p in punten]
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "weekdagprofiel.zondag")
    assert "zondag" in reden
    assert "nulstaaf" in reden


def test_weekdagprofiel_zonder_enige_meting_is_geen_kale_kaart():
    """Geen staven, dus geen grafiek: een reden in plaats van een lege kaart."""
    dagen = pd.date_range("2026-01-01", periods=40, freq="D")
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 1000.0) for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    # Peildatum ruim ná de meting: het venster van acht weken is dan leeg.
    a = _overzicht(totalen, pd.Timestamp("2026-06-30"), bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=pd.Timestamp("2026-02-09"),
                     prognose_methode=METHODE)
    assert a["data"]["weekdagprofiel"]["grafiek"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "weekdagprofiel")
    assert "geen enkele open winkeldag" in reden


def test_weekdagprofiel_toelichting_belooft_geen_gelijk_getal():
    """De oude tekst zei dat de prognose op ditzelfde patroon bouwt.

    Het profiel gemiddelt over acht kalenderweken, de baseline over de laatste
    vier gelijke weekdagen. Wie de twee naast elkaar legt, vindt verschillende
    getallen; de tekst hoort dat te zeggen in plaats van gelijkheid te beloven.
    """
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                     gemeten_tot=tot, prognose_methode=METHODE)
    tekst = a["data"]["weekdagprofiel"]["toelichting"]
    assert "ditzelfde patroon" not in tekst
    assert METHODE in tekst
    assert "niet gelijk" in tekst
    assert "8" in tekst  # het venster van acht weken, uitgeschreven


# --- kanalen en producten ---------------------------------------------------

def test_kanaalblok_draagt_stuks_meetdagen_en_gemiddelde():
    _, totalen, tot = _twee_jaar()
    a = ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, ontbrekend={})
    winkel = next(b for b in a["data"]["kanalen"] if b["kanaal"] == "winkel")
    assert isinstance(winkel["stuks_30d"], str)
    assert isinstance(winkel["gem_dagomzet"], str)
    assert isinstance(winkel["meetdagen"], str)
    Decimal(winkel["gem_dagomzet"])
    # een kanaal zonder data draagt dezelfde sleutels, met None
    deliveroo = next(b for b in a["data"]["kanalen"] if b["kanaal"] == "deliveroo")
    assert deliveroo["stuks_30d"] is None
    assert deliveroo["gem_dagomzet"] is None


def test_productverschuiving_in_contract_scheidt_stijgers_en_dalers():
    open_v, _totalen, tot = _twee_jaar()
    a = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    schuif = a["data"]["verschuiving"]
    assert schuif["toelichting"]
    for rij in schuif["stijgers"] + schuif["dalers"]:
        assert isinstance(rij["verschil"], str)
        Decimal(rij["verschil"])
        assert rij["verschil_pct"] is None or isinstance(rij["verschil_pct"], str)
        assert isinstance(rij["nieuw"], bool)
    for rij in schuif["stijgers"]:
        assert not rij["verschil"].startswith("-")
    for rij in schuif["dalers"]:
        assert rij["verschil"].startswith("-")


def test_geweigerde_verschuiving_wordt_een_reden_en_geen_stille_lijst():
    """Weigert de berekeningslaag de vergelijking, dan staat dát op het scherm.

    `bk.productverschuiving` levert een `Verschuiving` die zelf zegt of ze
    vergelijkbaar is: tellen de twee vensters niet evenveel gemeten open dagen,
    dan zijn de rijen leeg. Een lege tabel zonder uitleg is wat harde regel 8
    verbiedt, dus hier hoort een reden met beide aantallen.

    De fixture: twintig open dagen, en een vraag om vensters van dertig. Dan telt
    het huidige venster twintig dagen en het vorige nul.
    """
    dagen = pd.date_range("2026-06-01", periods=20, freq="D")
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 1000.0) for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    tot = bk.peildatum(open_v)

    schuif = bk.productverschuiving(open_v, tot, dagen=30)
    assert not schuif.vergelijkbaar, "fixture bewijst zijn eigen premisse niet"

    a = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"]["verschuiving"]["stijgers"] == []
    assert a["data"]["verschuiving"]["dalers"] == []
    assert a["data"]["verschuiving"]["toelichting"] == ""
    reden = next(o["reden"] for o in a["onbeschikbaar"] if o["veld"] == "verschuiving")
    assert "20 dagen" in reden and "0 dagen" in reden
    assert "vraaguitval" in reden


# --- de CFO-metrieken --------------------------------------------------------
#
# Zeven metrieken uit de berekeningslaag krijgen in het contract hun vorm. Wat
# hier bewaakt wordt is niet dat de cijfers kloppen — dat doen de tests van de
# berekeningslaag — maar dat de vorm klopt: geen float, geen technische sleutel
# zonder label, en een reden op elke plek waar een cijfer ontbreekt.


def _geen_floats(x) -> None:
    """Geen enkel bedrag verlaat het contract als float.

    Doorlopend, niet steekproefsgewijs: elk nieuw veld dat iemand toevoegt komt
    hier langs zonder dat er een test bij hoeft.
    """
    if isinstance(x, dict):
        for sleutel, waarde in x.items():
            # `y` en `ticks` zijn plotgeometrie en mogen float zijn, zoals in
            # elke grafiek van dit contract.
            if sleutel in ("y", "ticks"):
                continue
            _geen_floats(waarde)
    elif isinstance(x, list):
        for waarde in x:
            _geen_floats(waarde)
    else:
        assert not isinstance(x, float), f"float in het contract: {x!r}"


def _ontbinding_telt_op(ontbinding: dict) -> None:
    """De belofte van elke ontbinding: de termen tellen op de cent op."""
    som = sum((Decimal(t["waarde"]) for t in ontbinding["termen"]), Decimal(0))
    assert som == Decimal(ontbinding["verschil"]["waarde"])


def test_bonritme_ontbindt_de_omzet_en_telt_op_de_cent_op():
    """Dertig dagen 100 bonnen van € 10, daarna dertig 120 bonnen van € 11.

    Twee vensters van dertig dagen, want dat is het venster waarop het contract
    het bonritme opvraagt: een kortere fixture zou de twee helften in één
    venster middelen en dan meet de test niets.
    """
    dagen = pd.date_range("2026-05-02", periods=60, freq="D")
    bonnen_per_dag = [100] * 30 + [120] * 30
    bedrag = [10.0] * 30 + [11.0] * 30
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, b * n)
        for d, n, b in zip(dagen, bonnen_per_dag, bedrag, strict=True)
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)
    bonnen = _bonnen([
        (d.date().isoformat(), n)
        for d, n in zip(dagen, bonnen_per_dag, strict=True)
    ])

    a = ct.overzicht(totalen, tot, kalender=kal, bonnen=bonnen, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                     prognose_methode=METHODE)
    rit = a["data"]["bonritme"]
    assert [k["label"] for k in rit["kengetallen"]] == [
        "Klanten per dag", "Gemiddeld bonbedrag"]
    assert rit["kengetallen"][0]["waarde"] == "120.0"
    assert rit["kengetallen"][1]["waarde"] == "11.00"

    ont = rit["ontbinding"]
    # 120·11 − 100·10 = 320 per dag, waarvan 200 uit klanten en 100 uit mandje.
    assert ont["verschil"]["waarde"] == "320.00"
    assert ont["verschil"]["richting"] == "op"
    assert [t["waarde"] for t in ont["termen"]] == ["200.00", "100.00", "20.00"]
    _ontbinding_telt_op(ont)
    # Elke term draagt zijn eigen woorden: het scherm verzint er geen.
    assert all(t["label"] and t["uitleg"] for t in ont["termen"])
    _geen_floats(rit)


def test_bonritme_zonder_bonnentelling_is_een_reden_en_geen_leeg_vak():
    _open_v, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    assert a["data"]["bonritme"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"] if o["veld"] == "bonritme")
    assert "niet ingeladen" in reden


def test_weken_geven_de_omzet_per_open_dag_en_zwijgen_niet_over_een_dichte_week():
    """Twee volle weken met een gesloten week ertussen.

    De dichte week houdt haar rij en krijgt None met een reden. Nul zou een
    week zonder omzet tonen in plaats van een week zonder meting.
    """
    dagen = list(pd.date_range("2026-06-01", "2026-06-07")) + list(
        pd.date_range("2026-06-15", "2026-06-21"))
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 1000.0)
        for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)

    a = ct.overzicht(totalen, tot, kalender=kal, bonnen=None, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                     prognose_methode=METHODE)
    rijen = a["data"]["weken"]["rijen"]
    assert [r["open_dagen"] for r in rijen[-3:]] == [7, 0, 7]
    assert rijen[-2]["omzet"] is None
    assert rijen[-1]["omzet"] == "7000.00"
    assert rijen[-1]["omzet_per_dag"] == "1000.00"
    # Het label is kant-en-klaar: het scherm bouwt geen periodeteksten.
    assert rijen[-1]["label"] == "15 jun – 21 jun"
    reden = next(o["reden"] for o in a["onbeschikbaar"] if o["veld"] == "weken.gesloten")
    assert "8 jun – 14 jun" in reden
    _geen_floats(a["data"]["weken"])


def test_maandritme_tekent_geen_staaf_voor_een_maand_zonder_meting():
    _open_v, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    punten = a["data"]["maandritme"]["grafiek"]["reeksen"][0]["punten"]
    assert len(punten) == 12
    assert punten[-1]["x"] == "jun 26"
    # `meetdagen` is de sleutel waarop de staafgrafiek een ontbrekende staaf
    # herkent; zonder dat veld wordt een maand zonder meting een nulstaaf.
    assert all("meetdagen" in p for p in punten)


def test_weekdagmix_toont_alleen_het_aandeel_en_noemt_zijn_eigen_venster():
    _open_v, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    mix = a["data"]["weekdagmix"]
    assert [r["weekdag"] for r in mix["rijen"]] == bk.WEEKDAGEN_KORT
    assert all(isinstance(r["aandeel"], str) for r in mix["rijen"])
    # De toelichting moet het verschil met de grafiek erboven benoemen, anders
    # staan er twee onverenigbare zaterdagen op één scherm.
    assert "kalenderweken" in mix["toelichting"]
    _geen_floats(mix)


def test_afwijkende_dagen_zonder_uitschieter_zeggen_waarom_ze_leeg_zijn():
    """Een volmaakt regelmatig jaar heeft geen uitschieters.

    "Geen uitschieters" en "te weinig waarnemingen om het te kunnen zeggen"
    zien er in een lege tabel hetzelfde uit; de reden houdt ze uit elkaar.
    """
    _open_v, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    assert a["data"]["afwijkende_dagen"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "afwijkende_dagen")
    assert "niet als normaal verklaard" in reden


def test_afwijkende_dag_draagt_een_leesbaar_label_en_een_richting():
    """Eén maandag ver boven de gebruikelijke maandag.

    De fixture draagt bewust wat spreiding per weekdag: een reeks waarin elke
    maandag exact gelijk is, heeft een MAD van nul, en dan doet die weekdag
    volgens de berekeningslaag niet mee — daar is elke afwijking oneindig veel
    en dus niets gezegd.
    """
    dagen = pd.date_range("2026-04-01", "2026-06-30", freq="D")
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0,
         1000.0 + 50.0 * ((i // 7) % 3))
        for i, d in enumerate(dagen)
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)

    uitschieter = max(d for d in dagen if d.dayofweek == 0)
    assert uitschieter.dayofweek == 0, "de fixture moet een maandag raken"
    totalen = totalen.copy()
    totalen.loc[totalen["datum"] == uitschieter, "omzet"] = 5000.0

    a = ct.overzicht(totalen, tot, kalender=kal, bonnen=None, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                     prognose_methode=METHODE)
    rijen = a["data"]["afwijkende_dagen"]["rijen"]
    rij = next(r for r in rijen if r["datum"] == uitschieter.date().isoformat())
    assert rij["label"] == f"maandag {uitschieter.day} jun"
    assert rij["richting"] == "op"
    assert Decimal(rij["verschil"]) > 0
    assert Decimal(rij["omzet"]) - Decimal(rij["gebruikelijk"]) == Decimal(
        rij["verschil"])
    _geen_floats(a["data"]["afwijkende_dagen"])


def test_concentratie_telt_de_kop_en_noemt_de_staart_in_euro():
    open_v, _totalen, tot = _twee_jaar()
    a = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    con = a["data"]["concentratie"]
    # Eén product in de fixture: het draagt alles, en de staart is leeg.
    assert [r["producten"] for r in con["rijen"]] == ["1", "1", "1"]
    assert con["totaal_producten"] == "1"
    assert con["staart_producten"] == "0"
    assert con["staart_omzet"] == "0.00"
    # De drempels zijn woorden, geen technische sleutels.
    assert con["rijen"][1]["drempel"] == "80 % van de omzet"
    _geen_floats(con)


def test_prijs_volume_ontbinding_telt_op_de_cent_op():
    """Brood halveert in stuks en wordt duurder; de vijf termen sluiten aan."""
    rijen = []
    for d in pd.date_range("2026-06-01", periods=30, freq="D"):
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 10.0, 40.0))
    for d in pd.date_range("2026-07-01", periods=30, freq="D"):
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 5.0, 25.0))
        rijen.append((d.date().isoformat(), "20", "Koek", "winkel", 1.0, 3.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    tot = bk.peildatum(open_v)

    a = ct.producten(open_v, pd.Series({"10": "Brood", "20": "Koek"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    ont = a["data"]["prijs_volume"]
    assert len(ont["termen"]) == 5
    _ontbinding_telt_op(ont)
    # "Uit het assortiment" gaat als negatieve term het contract in, want de
    # invariant van de berekeningslaag trekt die post af. Wie hem positief zou
    # tonen, presenteert een optelling die niet uitkomt.
    uit_assortiment = next(t for t in ont["termen"]
                           if t["label"] == "Uit het assortiment")
    assert not Decimal(uit_assortiment["waarde"]) > 0
    _geen_floats(ont)


def test_prijs_volume_weigert_ongelijke_vensters_met_een_reden():
    dagen = pd.date_range("2026-06-01", periods=20, freq="D")
    verkopen = _verkopen([
        (d.date().isoformat(), "10", "Brood", "winkel", 1.0, 1000.0) for d in dagen
    ])
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    tot = bk.peildatum(open_v)

    a = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"]["prijs_volume"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"] if o["veld"] == "prijs_volume")
    assert "20 dagen" in reden and "0 dagen" in reden


def test_een_ontbinding_die_niet_optelt_komt_het_contract_niet_uit():
    """De vangrail achter beide ontbindingen.

    De invariant staat in de berekeningslaag, maar de contractlaag rekent hem
    na in plaats van hem aan te nemen: als iemand later een term toevoegt of
    een afronding verschuift, breekt het hier en niet op het scherm.
    """
    with pytest.raises(ValueError, match="telt niet op"):
        ct._ontbinding(
            verschil=Decimal("100.00"),
            verschil_label="Verandering",
            termen=[("A", Decimal("60.00"), "uitleg"),
                    ("B", Decimal("30.00"), "uitleg")],
            toelichting="",
        )


# --- prognose ---------------------------------------------------------------

def test_prognose_noemt_zijn_eigen_nauwkeurigheid_en_startpunt():
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam="weekdaggemiddelde", wape=0.084, venster=venster)
    velden = {o["veld"]: o["reden"] for o in a["onbeschikbaar"]}
    assert "prognose.nauwkeurigheid" in velden
    assert "8,4 %" in velden["prognose.nauwkeurigheid"], "komma en spatie"
    assert "30 juni 2026" in velden["prognose.startpunt"]
    assert "prognose.sluitingsdagen" in velden

    assert len(a["data"]["dagen"]) == 3
    assert a["data"]["dagen"][0]["datum"] == "2026-07-01"
    assert a["data"]["dagen"][0]["verwacht"] == "1000.00"
    assert len(a["data"]["grafiek"]["band"]) == 3


def test_prognose_weektotaal_is_som_over_de_dagen_in_het_venster():
    venster = _venster(7)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam="test", wape=0.084, venster=venster)
    assert a["data"]["weektotaal"] == "7000.00"
    assert a["data"]["weektotaal_dagen"] == 7
    velden = [o["veld"] for o in a["onbeschikbaar"]]
    assert "prognose.weektotaal" in velden


def test_prognose_over_een_zomersluiting_toont_geen_verwachte_week():
    """Bevinding 1, aan de contractkant.

    De situatie van 12 augustus 2026: laatste open dag 31 juli, daarna zeven
    dagen gemeten zomersluiting, en pas daarna dagen waarover iets te zeggen valt.
    Het weektotaal mag geen week beslaan waarin de bakkerij dicht was, en het
    meetgat ertussen hoort op het scherm.
    """
    kal = pd.DataFrame(
        [{"datum": datetime.date(2026, 7, 31), "winkel_gemeten": True,
          "winkel_open": True}]
        + [{"datum": datetime.date(2026, 8, d), "winkel_gemeten": True,
            "winkel_open": False} for d in range(1, 8)]
        + [{"datum": datetime.date(2026, 8, d), "winkel_gemeten": False,
            "winkel_open": False} for d in range(8, 26)]
    )
    venster = canoniek.prognosevenster(kal, gemeten_tot="2026-07-31",
                                       vandaag="2026-08-12", horizon=7)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster)

    # Geen enkele dag uit de sluitingsweek staat in het antwoord.
    datums = [d["datum"] for d in a["data"]["dagen"]]
    assert datums == [f"2026-08-{d}" for d in range(12, 19)]
    assert a["data"]["weektotaal_dagen"] == 7
    assert a["gemeten_tot"] == "2026-07-31"

    velden = {o["veld"]: o["reden"] for o in a["onbeschikbaar"]}
    assert "1 augustus 2026" in velden["prognose.meetgat"]
    assert "11 augustus 2026" in velden["prognose.meetgat"]
    assert "7 dagen zijn gemeten" in velden["prognose.meetgat"]
    assert "4 dagen zijn nog niet" in velden["prognose.meetgat"]
    assert "12 augustus 2026" in velden["prognose.startpunt"]


def test_het_meetgat_noemt_de_aangekondigde_sluitingsdagen_apart():
    """Dezelfde zomersluiting, nu mét sluitingslijst.

    Tot 18 augustus 2026 stonden de ongemeten dagen van een aangekondigde
    sluiting hier als "nog niet uit de bronsystemen ingeladen". Dat is de fout die
    de briefing op het openingsscherm liet zeggen dat de synchronisatie hapert;
    dit veld vertelde hetzelfde verhaal. De drie oorzaken staan nu apart.
    """
    dicht = {datetime.date(2026, 8, d) for d in range(1, 24)}
    kal = pd.DataFrame([
        {"datum": d.date(),
         "winkel_gemeten": d.date() <= datetime.date(2026, 8, 7),
         "winkel_open": (d.date() <= datetime.date(2026, 8, 7)
                         and d.date() not in dicht),
         "gepland_dicht": d.date() in dicht,
         "gepland_dicht_reden": "Jaarlijkse sluiting" if d.date() in dicht else ""}
        for d in pd.date_range("2026-07-25", "2026-09-05", freq="D")
    ])
    venster = canoniek.prognosevenster(kal, gemeten_tot="2026-07-31",
                                       vandaag="2026-08-18", horizon=7)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster)

    reden = {o["veld"]: o["reden"] for o in a["onbeschikbaar"]}["prognose.meetgat"]
    assert "1 augustus 2026 t/m 17 augustus 2026" in reden
    assert "7 dagen zijn gemeten en waren gesloten" in reden
    assert "10 dagen waren vooraf als gesloten aangekondigd" in reden
    # En geen enkele dag wordt als niet-ingeladen gepresenteerd.
    assert "ingeladen" not in reden


def test_prognose_meldt_de_gesloten_dagen_die_ze_oversloeg():
    """Een gesloten dag binnen het venster verdwijnt niet stilzwijgend."""
    kal = pd.DataFrame(
        [{"datum": datetime.date(2026, 5, 24), "winkel_gemeten": True,
          "winkel_open": True}]
        + [{"datum": datetime.date(2026, 5, d), "winkel_gemeten": True,
            "winkel_open": False} for d in (25, 26)]
        + [{"datum": datetime.date(2026, 5, d), "winkel_gemeten": False,
            "winkel_open": False} for d in range(27, 31)]
    )
    venster = canoniek.prognosevenster(kal, gemeten_tot="2026-05-24",
                                       vandaag="2026-05-24", horizon=2)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster)
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "prognose.gesloten_dagen")
    assert "25 mei 2026" in reden and "26 mei 2026" in reden
    assert [d["datum"] for d in a["data"]["dagen"]] == ["2026-05-27", "2026-05-28"]


def test_prognose_zonder_dagen_geeft_geen_nul_maar_een_reden():
    venster = _venster(0)
    a = ct.prognose(_blik([]), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster)
    assert a["data"]["weektotaal"] is None
    assert a["data"]["weektotaal_dagen"] == 0
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "prognose.weektotaal")
    assert "Geen weektotaal" in reden


# --- prognose: trackrecord, stapband en banddekking --------------------------

def _stappen() -> pd.DataFrame:
    return pd.DataFrame({
        "stap": [1, 2, 3],
        "n": [40, 40, 40],
        "wape": [0.065, 0.084, 0.102],
        "mae": [50.0, 60.0, 70.0],
        "bias": [1.0, 2.0, 3.0],
        "q_onder": [-0.05, -0.08, -0.12],
        "q_boven": [0.05, 0.09, 0.14],
    })


def _track() -> pd.DataFrame:
    datums = pd.date_range("2026-06-01", periods=4, freq="D")
    return pd.DataFrame({
        "datum": datums,
        "verwacht": [900.0, 1000.0, 1100.0, 960.0],
        "werkelijk": [1000.0, 1000.0, 1000.0, 1000.0],
        "stap": [1, 2, 3, 4],
    })


def _banddekking() -> pd.DataFrame:
    return pd.DataFrame({
        "stap": [1, 2, 3],
        "n": [30, 30, 0],
        "binnen_band": [0.56, 0.74, float("nan")],
        "beloofd": [0.8, 0.8, 0.8],
    })


def test_trackrecord_staat_als_twee_reeksen_in_het_antwoord():
    """Werkelijk naast voorspeld, out-of-sample: de vraag die een CFO over een
    model stelt is niet hoe het werkt maar of het de vorige keer klopte."""
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster,
                    track=_track())
    tr = a["data"]["trackrecord"]
    assert tr["dagen"] == 4
    assert tr["van"] == "2026-06-01" and tr["tot"] == "2026-06-04"
    # WAPE over het trackrecord: (100+0+100+40)/4000 = 6,0% — berekend hier,
    # nooit in de UI.
    assert tr["wape"] == "6.0"
    namen = {r["naam"]: r["kleur"] for r in tr["grafiek"]["reeksen"]}
    assert namen["Werkelijke omzet"] == "warmgrijs"
    assert namen["Wat het model voorspelde"] == "bordeaux"
    assert len(tr["grafiek"]["y_as"]["ticks"]) > 1


def test_zonder_trackrecord_staat_de_reden_in_onbeschikbaar():
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster)
    assert a["data"]["trackrecord"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "prognose.trackrecord")
    assert "te kort" in reden


def test_nauwkeurigheid_noemt_de_fout_per_stap_en_de_gemeten_dekking():
    """Het doel is 80% en de band dekt gemeten minder; dat staat hardop in de
    tekst, want een band die breder oogt dan hij dekt is een stille leugen."""
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster,
                    stappen=_stappen(), banddekking=_banddekking(),
                    band_doel=0.80)
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "prognose.nauwkeurigheid")
    assert "6,5 %" in reden and "10,2 %" in reden, "eerste en verste stap"
    # De stap met n=0 telt niet mee in de gemeten dekking.
    assert "56,0 %" in reden and "74,0 %" in reden and "80,0 %" in reden
    assert "te smal" in reden, "de band haalt haar doel niet en zegt dat"


def test_zonder_opgegeven_doel_wordt_er_geen_doel_verzonnen():
    """De dekking wordt dan wél gemeld, maar zonder uitspraak over een doel.

    Tot 15 augustus 2026 viel deze tak terug op de kolom `beloofd`, en dat is
    de nominale breedte van het kwantielpaar en niet het dekkingsdoel. Bij de
    productie-instelling (0,05-0,95 met doel 80%) had het scherm dan gezegd
    "waar 90,0% bedoeld is" en de band te smal genoemd terwijl ze haar doel
    haalt.
    """
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam=METHODE, wape=0.084, venster=venster,
                    stappen=_stappen(), banddekking=_banddekking())
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "prognose.nauwkeurigheid")
    assert "56,0 %" in reden and "74,0 %" in reden
    assert "bedoeld" not in reden
    assert "te smal" not in reden and "te ruim" not in reden


def test_stand_draagt_de_kwaliteitslaag_in_de_gewone_envelope():
    kwaliteit = {
        "bronnen": [{"bron": "odoo-kassa", "laatste_meetdag": "2026-07-31",
                     "rijen": 90000, "status": "vers", "toelichting": "ok"}],
        "wachters": [{"naam": "dubbele_sleutels", "uitkomst": "goed",
                      "toelichting": "geen dubbels"}],
        "ergste": "goed",
    }
    a = ct.stand(kwaliteit, bron=["odoo", "deliveroo"], bijgewerkt_op=BIJGEWERKT,
                 gemeten_tot=datetime.date(2026, 7, 31))
    assert a["gemeten_tot"] == "2026-07-31"
    assert a["data"]["ergste"] == "goed"
    assert a["data"]["bronnen"][0]["status"] == "vers"
    assert a["onbeschikbaar"] == []


# --- marge met ingevulde invoer ----------------------------------------------

def _marge_fixture():
    """Twintig dagen winkel, twee groepen; Brood draagt 2/3 van de omzet."""
    dagen = pd.date_range("2026-06-11", periods=20, freq="D")
    rijen = []
    for d in dagen:
        rijen.append((d.date().isoformat(), "10", "Brood wit", "winkel", 1.0, 100.0))
        rijen.append((d.date().isoformat(), "20", "Eclair", "winkel", 1.0, 50.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    groepen = pd.Series({"10": "Brood", "20": "Patisserie"})
    return open_v, groepen, bk.peildatum(open_v)


def _model(waarden, criteria=None):
    """Een echt kostenmodel, zoals lees_kostenmodel het aanlevert."""
    namen = criteria or sorted({c for w in waarden.values() for c in w})
    return km.Kostenmodel(
        criteria=tuple(km.Criterium(n) for n in namen),
        waarden=waarden)


def test_marge_vult_zich_zodra_er_invoer_is():
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen,
                 _model({"Brood": {"Kosten": Decimal(45)},
                         "Patisserie": {"Kosten": Decimal("37.5")}}),
                 tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    kern = a["data"]["kern"]
    assert kern is not None
    assert isinstance(kern["gewogen_pct"], str) and "," not in kern["gewogen_pct"]
    assert kern["dekking_pct"] == "100.0"
    groepen_uit = {r["groep"]: r for r in a["data"]["per_groep"]}
    assert set(groepen_uit) == {"Brood", "Patisserie"}
    assert groepen_uit["Brood"]["marge_pct"] == "55"
    assert groepen_uit["Brood"]["kosten"] == [
        {"criterium": "Kosten", "pct": "45", "kost_30d": "900.00"}]
    assert a["data"]["staaf"]["reeksen"][0]["punten"]
    assert a["data"]["criteria_bron"] == "ingevuld"
    # geen ontbrekende groepen: geen regel daarover
    velden = [o["veld"] for o in a["onbeschikbaar"]]
    assert "marge.ontbrekende_groepen" not in velden
    # maar Deliveroo staat er wél eerlijk bij
    assert "marge.deliveroo" in velden


def test_marge_draagt_de_kostenopbouw_met_sluitende_identiteit():
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen,
                 _model({"Brood": {"Grondstoffen": Decimal(30),
                                   "Verlies": Decimal(5)},
                         "Patisserie": {"Grondstoffen": Decimal(40)}},
                        criteria=["Grondstoffen", "Verlies"]),
                 tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    opbouw = a["data"]["kostenopbouw"]
    assert opbouw is not None
    per = {r["criterium"]: r for r in opbouw["per_criterium"]}
    assert per["Verlies"]["groepen_n"] == 1
    # identiteit als strings op de cent: omzet - kosten = marge
    assert (Decimal(opbouw["omzet_30d"]) - Decimal(opbouw["kosten_30d"])
            == Decimal(opbouw["marge_30d"]))


def test_marge_waarschuwt_bij_kosten_boven_100_procent():
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen,
                 _model({"Brood": {"Grondstoffen": Decimal(80),
                                   "Verlies": Decimal(30)}}),
                 tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    regel = next(o for o in a["onbeschikbaar"] if o["veld"] == "marge.negatief")
    assert "Brood" in regel["reden"]


def test_marge_zonder_invoer_draagt_suggestiecriteria():
    """Zonder invoer krijgt het formulier het standaardmenu aangereikt,
    herkenbaar als suggestie — er hangt geen enkel cijfer aan."""
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen, None, tot, bron=["odoo"],
                 bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"]["criteria_bron"] == "suggestie"
    assert a["data"]["kostenopbouw"] is None
    namen = [c["naam"] for c in a["data"]["criteria"]]
    assert "Grondstoffen" in namen


def test_marge_zonder_invoer_draagt_wel_de_groepenlijst():
    """Het formulier op Instellingen leest de groepen uit dit antwoord; ook
    zonder invoer moet de lijst er dus staan, met omzet en aandeel."""
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen, None, tot, bron=["odoo"],
                 bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"]["kern"] is None
    assert a["data"]["staaf"] is None
    rijen = a["data"]["per_groep"]
    assert [r["groep"] for r in rijen] == ["Brood", "Patisserie"]
    assert all(r["marge_pct"] is None for r in rijen)
    assert all(isinstance(r["omzet_30d"], str) for r in rijen)
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "marge_per_groep")
    assert "Instellingen" in reden


def test_marge_meldt_groepen_zonder_invoer_met_hun_aandeel():
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen,
                 _model({"Brood": {"Kosten": Decimal(45)}}), tot,
                 bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    assert a["data"]["kern"] is not None
    regel = next(o for o in a["onbeschikbaar"]
                 if o["veld"] == "marge.ontbrekende_groepen")
    assert "Patisserie" in regel["reden"]
    assert "33,3 %" in regel["reden"]


def test_marge_toont_een_genegeerd_bestand_met_reden():
    open_v, groepen, tot = _marge_fixture()
    a = ct.marge(open_v, groepen, None, tot, bron=["odoo"],
                 bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot,
                 invoer_fout="De marge van \"Brood\" is 101%, buiten het bereik 0-100.")
    regel = next(o for o in a["onbeschikbaar"] if o["veld"] == "marge.invoer")
    assert "genegeerd" in regel["reden"]
    assert "101%" in regel["reden"]


# --- de periodekubus -----------------------------------------------------------

def test_periodes_dragen_vijf_voorgebakken_vensters():
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    vensters = {v["sleutel"]: v for v in a["data"]["periodes"]}
    assert set(vensters) == {"d7", "d30", "w13", "m12", "jaar"}
    for v in vensters.values():
        assert v["label"]
        assert v["soort"] in ("lijn", "staaf")
        assert v["toelichting"]
        # context: kant-en-klare labels, machinewaarden als string
        for item in v["context"]:
            assert isinstance(item["waarde"], str)
            assert "," not in item["waarde"]
    # de kiezer rekent niet: elke grafiek draagt zijn eigen as
    for v in vensters.values():
        if v["grafiek"] is not None:
            assert v["grafiek"]["y_as"]["ticks"]


def test_het_korte_venster_telt_open_dagen_en_niet_kalenderdagen():
    """Zeven open dagen zijn geen zeven kalenderdagen.

    De fixture draait zes dagen per week; het venster moet dus zeven gemeten
    open dagen beslaan en niet de zeven kalenderdagen vóór de peildatum. Zonder
    dit onderscheid zakt het totaal mee met elke sluitingsdag in het venster,
    en dan meet de week de kalender in plaats van de zaak.
    """
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    d7 = next(v for v in a["data"]["periodes"] if v["sleutel"] == "d7")
    assert d7["grafiek"]["reeksen"][0]["punten"] is not None
    assert len(d7["grafiek"]["reeksen"][0]["punten"]) == 7
    # Het knoplabel draagt het gevraagde aantal, de toelichting het gevondene.
    assert "7" in d7["label"]
    assert "7 gemeten open winkeldagen" in d7["toelichting"]


def test_precies_een_venster_opent_de_kiezer():
    """De kiezer mag niet raden welk venster opent, en niet twee kandidaten
    krijgen. Dertig dagen blijft het openingsbeeld: een week is te kort om een
    dashboard mee te openen, ook nu ze zelf kunnen wisselen."""
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    standaard = [v for v in a["data"]["periodes"] if v.get("standaard")]
    assert [v["sleutel"] for v in standaard] == ["d30"]


def test_periodes_lopen_van_kort_naar_lang():
    """De knoprij is een schaal; een venster dat ertussen springt leest als een
    fout in het scherm."""
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    sleutels = [v["sleutel"] for v in a["data"]["periodes"]]
    assert sleutels == ["d7", "d30", "w13", "m12", "jaar"]


def test_periodes_vergelijken_op_gemiddelde_per_open_dag():
    """Twee jaar fixture: het jaarvenster moet tegen vorig jaar vergelijken,
    en het verschil-item draagt beide aantallen open dagen in zijn label."""
    _, totalen, tot = _twee_jaar()
    a = _overzicht(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, prognose_methode=METHODE)
    jaar = next(v for v in a["data"]["periodes"] if v["sleutel"] == "jaar")
    verschil = [c for c in jaar["context"] if c["soort"] == "verschil"]
    assert verschil, "geen vergelijking met vorig jaar in het jaarvenster"
    assert "open dagen" in verschil[0]["label"]


# --- de financiële wig op het kanalenscherm ---------------------------------------

def test_kanalen_dragen_bruto_commissie_netto():
    rijen = []
    for d in pd.date_range("2026-06-11", periods=20, freq="D"):
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, 100.0))
        rijen.append((d.date().isoformat(), "99", "Bestelling", "deliveroo", 2.0, 8.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)
    kost = pd.DataFrame({
        "kanaal": ["deliveroo"], "maand": ["2026-06"], "stuks": [40.0],
        "bruto_per_stuk": [5.69], "commissie_per_stuk": [1.69],
        "inhouding_pct": [0.297],
    })
    a = ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, ontbrekend={}, kanaalkost=kost)
    blokken = {k["kanaal"]: k for k in a["data"]["kanalen"]}
    assert blokken["winkel"]["commissie_30d"] == "0.00"
    assert blokken["winkel"]["bruto_30d"] == blokken["winkel"]["netto_30d"]
    assert blokken["deliveroo"]["commissie_30d"] is not None
    assert Decimal(blokken["deliveroo"]["bruto_30d"]) == (
        Decimal(blokken["deliveroo"]["netto_30d"])
        + Decimal(blokken["deliveroo"]["commissie_30d"])
    )
    assert blokken["deliveroo"]["inhouding_pct"] is not None


def test_kanalen_zonder_kosttabel_zetten_de_reden_erbij():
    rijen = [("2026-06-11", "99", "Bestelling", "deliveroo", 2.0, 8.0),
             ("2026-06-11", "10", "Brood", "winkel", 1.0, 100.0)]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    a = ct.kanalen(totalen, bk.peildatum(open_v), bron=["odoo"],
                   bijgewerkt_op=BIJGEWERKT, gemeten_tot=None,
                   ontbrekend={}, kanaalkost=None)
    blokken = {k["kanaal"]: k for k in a["data"]["kanalen"]}
    assert blokken["deliveroo"]["bruto_30d"] is None
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "kanaal.deliveroo.kost")
    assert "commissie" in reden.lower()


def test_bevroren_kanaal_toont_tot_wanneer_de_data_loopt():
    # Een kanaal met historiek maar niets in het 30-dagenvenster: de reden
    # zegt tot wanneer de data loopt, en niet "geen data ingeladen".
    rijen = [("2026-03-05", "99", "Bestelling", "deliveroo", 2.0, 8.0)]
    for d in pd.date_range("2026-06-01", periods=20, freq="D"):
        rijen.append((d.date().isoformat(), "10", "Brood", "winkel", 1.0, 100.0))
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    totalen = bk.dagtotalen(open_v)
    tot = bk.peildatum(open_v)
    a = ct.kanalen(totalen, tot, bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                   gemeten_tot=tot, ontbrekend={}, kanaalkost=None)
    reden = next(o["reden"] for o in a["onbeschikbaar"]
                 if o["veld"] == "kanaal.deliveroo")
    assert "5 maart 2026" in reden
    assert "ingeladen" not in reden


def test_producten_dragen_de_drilldown_met_restregel():
    open_v, _, tot = _marge_fixture()
    groepen = pd.Series({"10": "Brood", "20": "Brood"})
    a = ct.producten(open_v, groepen, tot, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    detail = a["data"]["groepen_detail"]
    assert detail, "geen drill-down in het antwoord"
    brood = detail[0]
    assert brood["groep"] == "Brood"
    assert len(brood["producten"]) == 2
    assert brood["rest"] is None
    # de zichtbare rijen sommeren tot de groepsomzet, op de cent
    som = sum(Decimal(p["omzet"]) for p in brood["producten"])
    assert som == Decimal(brood["omzet_30d"])


# --- aangekondigde sluitingen op het scherm (14 augustus 2026) --------------


def _venster_met_aankondiging(horizon=4):
    """Kalender met een aangekondigde sluitingsweek na de laatste meting."""
    rijen = (
        [{"datum": datetime.date(2026, 8, d), "winkel_gemeten": True,
          "winkel_open": True, "gepland_dicht": False, "gepland_dicht_reden": ""}
         for d in range(10, 15)]
        + [{"datum": datetime.date(2026, 8, d), "winkel_gemeten": False,
            "winkel_open": False, "gepland_dicht": True,
            "gepland_dicht_reden": "Jaarlijkse sluiting"}
           for d in range(17, 24)]
        + [{"datum": datetime.date(2026, 8, d), "winkel_gemeten": False,
            "winkel_open": False, "gepland_dicht": False,
            "gepland_dicht_reden": ""}
           for d in range(24, 30)]
    )
    return canoniek.prognosevenster(
        pd.DataFrame(rijen), gemeten_tot="2026-08-14", vandaag="2026-08-17",
        horizon=horizon,
    )


def test_prognose_meldt_de_aangekondigde_sluiting_met_de_reden():
    """De gebruiker die zich afvraagt waarom er volgende week niets staat,
    hoort "Jaarlijkse sluiting" te lezen en niet "overgeslagen"."""
    venster = _venster_met_aankondiging()
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam="test", wape=0.076, venster=venster,
                    sluitingsdekking=datetime.date(2026, 8, 23))
    velden = {o["veld"]: o["reden"] for o in a["onbeschikbaar"]}

    reden = velden["prognose.geplande_sluiting"]
    assert "Jaarlijkse sluiting" in reden
    assert "17 augustus 2026" in reden and "23 augustus 2026" in reden

    # Geen enkele gesloten dag in de uitvoer.
    datums = {d["datum"] for d in a["data"]["dagen"]}
    assert not any(f"2026-08-{d:02d}" in datums for d in range(17, 24))
    assert a["data"]["weektotaal_dagen"] == 4


def test_de_aannametekst_volgt_wat_er_werkelijk_bekend_is():
    """Het voorbehoud werkt sinds de sluitingskalender (19 augustus 2026) per
    dag, niet per venster: het wordt preciezer naarmate er meer bevestigd is,
    en het blijft eerlijk zolang er iets ontbreekt."""
    venster = _venster_met_aankondiging()

    zonder = ct.prognose(_blik(venster.dagen), bron=["odoo"],
                         bijgewerkt_op=BIJGEWERKT, baseline_naam="test",
                         wape=0.076, venster=venster)
    tekst = {o["veld"]: o["reden"] for o in zonder["onbeschikbaar"]}
    # Gedrag, niet gelijkheid met de constante (die vergelijking was de tekst
    # met zichzelf vergelijken — audit 15 aug, punt d): zonder enige bron zegt
    # de reden dat de prognose voorbij het gemeten bereik "open" aanneemt, en
    # de handeling is een scherm — niet langer een JSON-bestand in git.
    reden_zonder = tekst["prognose.sluitingsdagen"]
    assert "neemt de prognose aan dat de winkel open is" in reden_zonder
    assert "scherm Sluitingsdagen" in reden_zonder

    # De lijst reikt tot 23 augustus; de vier vensterdagen (24 t/m 27) liggen
    # erbuiten en niemand heeft ze bevestigd. Meer dan drie: aantal en bereik.
    deels = ct.prognose(_blik(venster.dagen), bron=["odoo"],
                        bijgewerkt_op=BIJGEWERKT, baseline_naam="test",
                        wape=0.076, venster=venster,
                        sluitingsdekking=datetime.date(2026, 8, 23))
    tekst = {o["veld"]: o["reden"] for o in deels["onbeschikbaar"]}
    reden_deels = tekst["prognose.sluitingsdagen"]
    assert "4 dagen in dit venster" in reden_deels
    assert "24 augustus 2026 t/m 27 augustus 2026" in reden_deels
    assert "neemt de prognose aan dat de winkel open is" in reden_deels

    # Een bevestigde dag verdwijnt uit het voorbehoud: drie dagen over, en
    # drie of minder staan bij naam.
    bevestigd = ct.prognose(_blik(venster.dagen), bron=["odoo"],
                            bijgewerkt_op=BIJGEWERKT, baseline_naam="test",
                            wape=0.076, venster=venster,
                            sluitingsdekking=datetime.date(2026, 8, 23),
                            bevestigde_dagen=frozenset(
                                {datetime.date(2026, 8, 24)}))
    tekst = {o["veld"]: o["reden"] for o in bevestigd["onbeschikbaar"]}
    reden_bevestigd = tekst["prognose.sluitingsdagen"]
    assert "24 augustus 2026" not in reden_bevestigd
    assert ("25 augustus 2026, 26 augustus 2026, 27 augustus 2026"
            in reden_bevestigd)
    assert "scherm Sluitingsdagen" in reden_bevestigd

    volledig = ct.prognose(_blik(venster.dagen), bron=["odoo"],
                           bijgewerkt_op=BIJGEWERKT, baseline_naam="test",
                           wape=0.076, venster=venster,
                           sluitingsdekking=datetime.date(2026, 12, 31))
    tekst = {o["veld"]: o["reden"] for o in volledig["onbeschikbaar"]}
    reden_volledig = tekst["prognose.sluitingsdagen"]
    assert "Voor elke overige dag in dit venster is er een antwoord" in (
        reden_volledig)
    # En géén dekkingsclaim: een lijst van periodes verklaart de periodes die
    # erin staan en heeft geen begin van dekking. Dat "de stand aangeleverd is"
    # was op 15 augustus 2026 aantoonbaar onwaar over 15 en 16 augustus, dagen
    # waarover niemand ooit iets gezegd had.
    assert "aangeleverd en niet aangenomen" not in reden_volledig
    assert "de lijst zwijgt" in reden_volledig

    # En nergens de doodlopende gang: "vul de sluitingslijst aan" vroeg een
    # CFO om een bestand in een git-repository te bewerken.
    for reden in (reden_zonder, reden_deels, reden_bevestigd, reden_volledig):
        assert "vul ze aan in de sluitingslijst" not in reden
        assert "vul de sluitingslijst aan" not in reden


def test_kalenderreden_zonder_enige_bron_geeft_de_algemene_tekst():
    """onbekend=None betekent "er is geen enkele sluitingsbron": dan geldt het
    voorbehoud over het hele venster, en eindigt de tekst op de handeling."""
    reden = ct._kalenderreden(None, None)
    assert "neemt de prognose aan dat de winkel open is" in reden
    assert reden.endswith("op het scherm Sluitingsdagen.")


def test_kalenderreden_noemt_weinig_dagen_bij_naam_en_veel_als_bereik():
    dagen = tuple(datetime.date(2026, 8, 24) + datetime.timedelta(days=i)
                  for i in range(4))
    dekking = datetime.date(2026, 8, 23)

    weinig = ct._kalenderreden(dekking, dagen[:2])
    assert "24 augustus 2026, 25 augustus 2026" in weinig
    assert "scherm Sluitingsdagen" in weinig

    veel = ct._kalenderreden(dekking, dagen)
    assert "4 dagen in dit venster" in veel
    assert "24 augustus 2026 t/m 27 augustus 2026" in veel


def test_kalenderreden_met_alles_beantwoord_zegt_dat_ook():
    """onbekend=() is een andere uitspraak dan onbekend=None (harde regel 8:
    onbekend is niet hetzelfde als open): het voorbehoud is weg, en dat mag
    gezegd worden — zonder dekkingsclaim die de bron niet kan waarmaken."""
    met_lijst = ct._kalenderreden(datetime.date(2026, 12, 31), ())
    assert "Voor elke overige dag in dit venster is er een antwoord" in met_lijst
    assert "tot 31 december 2026" in met_lijst
    assert "de lijst zwijgt" in met_lijst
    assert "aangeleverd en niet aangenomen" not in met_lijst

    # Zonder bestandslijst maar met alles per dag bevestigd: geen woord over
    # een lijst die er niet is.
    zonder_lijst = ct._kalenderreden(None, ())
    assert "Voor elke overige dag in dit venster is er een antwoord" in (
        zonder_lijst)
    assert "bereik van de sluitingslijst" not in zonder_lijst


# --- de tabelwoorden komen uit het contract, in beide talen (17 aug 2026) ----
#
# De visuele steekproef vond op het Franse productmixscherm "KOMT VAN",
# "VAN HET ASSORTIMENT", "29 producten" en "overige 8 producten": woorden die
# de UI zelf achter de machinewaarden plakte. Harde regel 4 geldt ook voor
# woorden — de UI verzint geen tekst. Sindsdien draagt het contract ze
# kant-en-klaar, en deze tests pinnen dat in beide talen vast.


def test_concentratie_draagt_zijn_kolomkoppen_en_telwoorden_zelf():
    open_v, _totalen, tot = _twee_jaar()
    a = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                     bron=["odoo"], bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    con = a["data"]["concentratie"]
    assert con["kolommen"] == [
        "Dit deel van de omzet", "komt van", "van het assortiment"]
    # Eén product in de fixture: enkelvoud, met het woord erbij.
    assert [r["label"] for r in con["rijen"]] == ["1 product"] * 3

    with tl.in_taal("fr"):
        a_fr = ct.producten(open_v, pd.Series({"10": "Brood"}), tot,
                            bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                            gemeten_tot=tot)
    con_fr = a_fr["data"]["concentratie"]
    assert con_fr["kolommen"] == [
        "Cette part du chiffre d'affaires", "provient de", "de l'assortiment"]
    assert [r["label"] for r in con_fr["rijen"]] == ["1 produit"] * 3
    # De machinewaarden zijn identiek: zelfde cijfers, andere woorden.
    assert [r["producten"] for r in con_fr["rijen"]] == [
        r["producten"] for r in con["rijen"]]


def test_meervoud_van_producten_in_beide_talen():
    assert ct._producten_nl(29) == "29 producten"
    assert ct._producten_nl(1) == "1 product"
    with tl.in_taal("fr"):
        assert ct._producten_nl(29) == "29 produits"
        assert ct._producten_nl(1) == "1 produit"


def test_restregel_draagt_zijn_eigen_label_in_beide_talen():
    """Het Frans zet het telwoord vóór 'autres'; dat kan alleen als de hele
    tekst uit de berekeningslaag komt en de UI er niets aan plakt."""
    assert ct._rest_label(23) == "overige 23 producten"
    assert ct._rest_label(1) == "1 overig product"
    with tl.in_taal("fr"):
        assert ct._rest_label(23) == "23 autres produits"
        assert ct._rest_label(1) == "1 autre produit"


def test_drilldown_restregel_in_het_contract_draagt_het_label():
    """Meer producten in één groep dan de kop toont: de rest-regel komt met
    label én machinewaarde uit het contract."""
    dagen = pd.date_range("2026-05-01", "2026-06-30", freq="D")
    rijen = []
    for i in range(12):
        pid = str(100 + i)
        rijen += [(d.date().isoformat(), pid, f"Product {pid}", "winkel",
                   1.0, 10.0 + i) for d in dagen]
    verkopen = _verkopen(rijen)
    kal = canoniek.bouw_kalender(verkopen)
    open_v = bk.open_verkopen(verkopen, kal)
    tot = bk.peildatum(open_v)
    groepen = pd.Series({str(100 + i): "Brood" for i in range(12)})
    a = ct.producten(open_v, groepen, tot, bron=["odoo"],
                     bijgewerkt_op=BIJGEWERKT, gemeten_tot=tot)
    rest = a["data"]["groepen_detail"][0]["rest"]
    assert rest is not None
    assert rest["producten"] == "4"
    assert rest["label"] == "overige 4 producten"
