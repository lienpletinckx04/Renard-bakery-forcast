"""Bouwt het volledige contract uit de canonieke data.

Dit is de nachtelijke berekening in zijn lokale vorm: dezelfde functies, maar de
uitvoer gaat naar bestanden in plaats van naar Postgres. Zodra de database er is
(G7), schrijft dezelfde berekening naar tabellen en serveert een API-route dit
antwoord; de vorm verandert niet, en dat is het hele punt van de contractlaag.

    data/interim/canoniek_*.csv  ->  platform/contract/*.json

WAAROM DE UITVOER NIET IN GIT GAAT

`platform/contract/` is gitignored. Wat hier uit komt zijn geaggregeerde
omzetcijfers van de eindklant, en harde regel 2 zegt dat klantdata de repo niet
in gaat. De generator is versiebeheerd, de uitvoer niet. Wie het platform wil
draaien, draait eerst dit script.

Draaien:  make contract
"""
import json
import os
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import berekening as bk
from bakkerij import briefing as bf
from bakkerij import canoniek, sluitingsdagen
from bakkerij import contract as ct
from bakkerij import kostenmodel as km
from bakkerij import kwaliteit as kw
from bakkerij import taal as tl
from bakkerij import winkels as wk
from bakkerij.backtest.rolling import (
    HORIZON,
    MIN_TRAIN,
    STAP,
    band_per_stap,
    evalueer,
    kalibreer_kwantielen,
    per_horizon,
    trackrecord,
)
from bakkerij.canoniek import DELIVEROO_REDEN, DELIVEROO_REDEN_FR
from bakkerij.db import BRONNEN, contract_bron, droge_modus
from bakkerij.db import kostenmodel_db as kmdb
from bakkerij.features import vakanties
from bakkerij.features.calendar import (
    SCHOOLVAKANTIES_FR,
)
from bakkerij.model.categorie import categorie_prognoses, categorie_reeksen
from bakkerij.model.productie import (
    BASIS,
    KENMERKEN,
    VOORSPELLER_NAAM,
    VOORSPELLER_NAAM_FR,
    bouw_voorspeller,
    prognosekalender,
    wikkel,
)
from bakkerij.model.scenario import scenario_prognoses
from bakkerij.model.verfijning import opbouw
from bakkerij.omgeving import laad_env

INTERIM = REPO / "data" / "interim"
RAW = REPO / "data" / "raw"
UIT = REPO / "platform" / "contract"
REPORTS = REPO / "reports"

# De door de beheerder beheerde invoer. In data/ en dus buiten git; het
# formulier op Instellingen schrijft het kostenmodel, migratie 005 is de
# databasevorm die het bij S2 overneemt. marges.json is de v1-vorm (één
# brutomarge per groep) en blijft leesbaar zolang er geen v2-bestand ligt.
KOSTEN_PAD = REPO / "data" / "config" / "kostenmodel.json"
MARGES_PAD = REPO / "data" / "config" / "marges.json"

# De winkelindeling (optioneel): welke filialen samen één verkooppunt vormen.
# Zonder bestand is er één geheel, zoals vandaag; mét bestand komt er naast het
# totaal een contractmap per winkel, elk met een eigen gebackteste prognose.
# Sinds 18 sep 2026 in `config/` en dus in git, om dezelfde reden als
# SLUITINGEN_PAD hieronder: winkel- en kassanamen zijn geen klantdata, en de
# nachtelijke sync draait op een GitHub-runner die `data/` nooit ziet.
WINKELS_PAD = REPO / "config" / "winkels.json"

#: De vooraf bekende sluitingsdagen. Zonder bestand kent de prognose geen
#: toekomstige sluitingen en zegt ze dat, in plaats van open aan te nemen.
#: Sinds 19 aug 2026 in `config/` en dus in git — zie de toelichting bij
#: dezelfde constante in scripts/canoniek_bouw.py.
SLUITINGEN_PAD = REPO / "config" / "sluitingsdagen.json"

# Onder MIN_TRAIN gemeten dagen (harnas: bakkerij/backtest/rolling.py) is er
# geen out-of-sample meting mogelijk, en dus ook geen prognose (harde regel 7).

# WAT "IN PRODUCTIE" IS, STAAT NIET MEER HIER MAAR IN bakkerij/model/productie.py.
#
# Tot 19 augustus 2026 stond de constructie hier, en bouwden de diagnose en het
# backtest-rapport hem elk op hun eigen manier na. Die drie constructies liepen
# uiteen — genoeg om twee tegengestelde verdicten te geven over hetzelfde
# kenmerk (heropening: +0,12 punt volgens de diagnose, -0,002 volgens E4), en
# op 14 augustus genoeg om een modelkaart te laten claimen wat het model niet
# deed. Het volledige verhaal staat in de kop van productie.py en in
# docs/beslissingen.md.
#
# Wat er hier overblijft is de tweetalige naam voor de modelkaart: die hoort bij
# de presentatie en niet bij het model.

def voorspeller_naam() -> str:
    """De naam in de taal van het moment. Een moduleconstante zou bij import
    bevriezen op het Nederlands en dan als Nederlandse zin midden in de
    Franse modelkaart staan — precies zo is hij op 17 aug gevonden."""
    return tl.t(VOORSPELLER_NAAM, VOORSPELLER_NAAM_FR)


def kosten_waarden(model) -> dict:
    """De ingevulde kosten van een kostenmodel: groep -> criterium -> percentage.

    Eén regel, en toch een eigen functie met een test, want hier zat een fout die
    de hele contractbouw omvergooide zodra er écht kosten waren ingevuld.

    `berekening.marge_per_groep` verwacht die dict en niet het model -- zo geeft
    `contract.marge_antwoord` hem ook door. In `_briefings` stond `kosten_model
    or {}`, en dat gaf `AttributeError: 'Kostenmodel' object has no attribute
    'get'`. Gemeten op 18 augustus 2026, bij de eerste bouw met ingevulde kosten:
    de bouw viel om in beide talen.

    Waarom geen enkele test dat kon zien: `data/config/marges.json` draagt nul
    groepen en `kostenmodel.json` bestond niet, dus `kosten_model` was altijd
    None -- en `None or {}` is een dict. Het margescherm is met andere woorden
    nog nooit met echte kosten gebouwd, en dus was dit pad nog nooit gedraaid.
    """
    return dict(getattr(model, "waarden", {}) or {})


def _briefings(*, open_verkopen, dagtotalen, groepen, kalender, verkopen,
               kosten_model, kosten_fout, kanaalkost, bonnen, uren, tot, vandaag,
               venster, resultaat, dek, kalenderdekking,
               sluitingsdekking, bevestigde_dagen=frozenset()) -> dict[str, dict]:
    """De briefing per scherm, als dict klaar voor de envelope.

    Alle invoer komt uit dezelfde berekeningen die de schermen zelf vullen, en
    dat is de bedoeling: de briefing mag niets weten wat er niet ook onder
    staat. Ze rekent hier niets zelf uit -- `bakkerij/briefing.py` leest de
    uitkomsten en zet er drempels naast.
    """
    versheid = bf.Versheid(vandaag, tot, meetgat=venster.meetgat,
                           sluiting=venster.sluiting)

    bronstanden = kw.bronstanden(
        verkopen.assign(datum=verkopen["datum"].dt.date),
        kalender.assign(datum=kalender["datum"].dt.date),
        vandaag=vandaag,
    )
    wachters = kw.wachters(
        verkopen.assign(datum=verkopen["datum"].dt.date),
        kalender.assign(datum=kalender["datum"].dt.date),
        vandaag=vandaag, bonnen_df=bonnen, uren_df=uren,
    )

    # Zonder opgegeven volgorde ordent `marge_per_groep` de criteria zelf. Dat
    # raakt alleen de presentatie, en de briefing leest van dit beeld alleen de
    # dekking en de groepen -- niet de kolomvolgorde.
    #
    # `.waarden` en niet het model zelf. Hier stond `kosten_model or {}`, en dat
    # gaf `AttributeError: 'Kostenmodel' object has no attribute 'get'` zodra er
    # écht een kostenmodel was -- de functie verwacht groep -> criterium -> pct,
    # net zoals contract.marge_antwoord het doorgeeft. Gemeten 18 aug 2026, bij
    # de eerste bouw met ingevulde kosten: de hele contractbouw viel om, in beide
    # talen. Niemand had het kunnen zien, want `data/config/marges.json` draagt
    # nul groepen en `kostenmodel.json` bestond niet, dus `kosten_model` was
    # altijd None en `None or {}` is een dict. De marge is met andere woorden nog
    # nooit gebouwd; dit is de eerste keer.
    beeld = bk.marge_per_groep(open_verkopen, groepen,
                               kosten_waarden(kosten_model), tot, dagen=30)

    bias = None
    if resultaat is not None and resultaat.som_werkelijk:
        bias = resultaat.som_fout / resultaat.som_werkelijk

    return {
        "overzicht": bf.overzicht(
            versheid=versheid,
            periode=bk.periodecontext(dagtotalen, tot, dagen=30),
            afwijkende=bk.afwijkende_dagen(dagtotalen, tot),
            bonritme=(bk.bonritme(bonnen, dagtotalen, tot)
                      if bonnen is not None else None),
        ).als_dict(),
        "kanalen": bf.kanalen(
            versheid=versheid, bronstanden=bronstanden,
        ).als_dict(),
        "producten": bf.producten(
            versheid=versheid,
            verschuiving=bk.productverschuiving(open_verkopen, tot, dagen=30),
        ).als_dict(),
        "marge": bf.marge(versheid=versheid, beeld=beeld,
                          invoer_fout=kosten_fout).als_dict(),
        "prognose": bf.prognose(
            versheid=versheid, venster=venster, bias=bias, banddekking=dek,
            band_doel=BAND_DOEL, kalenderdekking=kalenderdekking,
            sluitingsdekking=sluitingsdekking, categorieen_overgeslagen=(),
            bevestigde_dagen=bevestigde_dagen,
        ).als_dict(),
        "stand": bf.instellingen(
            versheid=versheid, bronstanden=bronstanden, wachters=wachters,
            kostenmodel_ingevuld=bool(kosten_model),
        ).als_dict(),
    }


# De band belooft geen nominale kwantielnaam maar een dekkingsdoel; de
# kalibratie kiest de smalste kwantielen die dit doel out-of-sample halen.
BAND_DOEL = 0.80


def laad_groepen() -> pd.Series:
    """product_id -> categorie, uit de productendimensie van Odoo."""
    treffers = sorted(RAW.glob("*_odoo_producten.csv"))
    if not treffers:
        return pd.Series(dtype=str)
    producten = pd.read_csv(treffers[-1], dtype={"product_id": str})
    return producten.set_index("product_id")["categorie"]


def kostenrijen_uit_db() -> tuple[tuple[list, list] | None, str | None]:
    """De ruwe kostenmodelrijen uit Postgres, of een reden waarom het niet lukte.

    WAAROM DIT BESTAAT. Het kostenmodel is invoer van de beheerder, en die
    invoer verhuisde op 18 augustus 2026 mee naar de database: met
    `CONTRACT_BRON=db` leest het platform het contract daar, en dus schrijft het
    formulier op Instellingen de kosten daar ook (migratie 009). Zou deze bouw
    dan nog het bestand lezen, dan bestaan er twee kostenmodellen die kunnen
    uiteenlopen -- en dat is precies wat "één bron van waarheid" uitsluit. Op de
    nachtelijke runner is het verschil nog scherper: daar staat `data/config/`
    helemaal niet, dus het bestand is er leeg en de database niet.

    RUWE RIJEN EN GEEN MODEL. De rijen zijn taalloos; het model is dat niet -- de
    foutmeldingen van de parser en de naam van het v1-criterium volgen `t()`.
    Daarom halen we hier één keer op en bouwt de taallus er per taal een model
    van.

    EEN ONBEREIKBARE DATABASE STOPT DE BOUW NIET. Het kostenmodel voedt één van
    de zeven schermen. Zes schermen niet bouwen omdat de pooler even weg is, is
    slechter dan het margescherm eerlijk op onbeschikbaar zetten met de reden
    erbij (harde regel 8). De volledige fout gaat naar de bouwuitvoer, waar een
    beheerder hem kan lezen; op het scherm komt een vaste zin. Dat onderscheid
    is bewust: `SUPABASE_DB_URL` bevat het databasewachtwoord, en de reden
    achter een verbindingsfout hoort niet op een scherm dat ook een lezer opent.
    """
    from bakkerij.db import kostenmodel_db as kmdb
    from bakkerij.db.verbinding import verbind

    try:
        with verbind() as verbinding:
            return kmdb.haal_rijen(verbinding), None
    except Exception as fout:  # noqa: BLE001 -- zie de docstring: nooit fataal
        print(f"kostenmodel uit de database: mislukt ({type(fout).__name__}: "
              f"{fout})")
        return None, type(fout).__name__


def kostenmodel_voor_taal(bron: str, rijen, dbfout: str | None):
    """Het kostenmodel voor één taal, uit de gekozen bron.

    Geeft (model, fout) terug: hoogstens één van de twee is gezet. `None, None`
    betekent "nog niets ingevuld" -- de normale beginstand, geen fout.

    Deze functie moet BINNEN de taalcontext aangeroepen worden: elke tekst die
    hij teruggeeft, gaat het contract in en volgt dus `t()`.
    """
    # Vóór de try, zodat een onbekende bron níét als "invoerfout" op het scherm
    # eindigt maar de bouw stopt. Een bron die we niet kennen, is een
    # configuratiefout van ons, geen fout in de invoer van de beheerder --
    # en stil de bestanden kiezen zou op een runner zonder data/config/ een
    # verarmd contract opleveren.
    if bron not in BRONNEN:
        raise ValueError(
            f"kostenmodel_voor_taal: onbekende bron {bron!r}; "
            f"keuze uit {', '.join(BRONNEN)}."
        )
    try:
        if bron == "db":
            if dbfout is not None:
                return None, tl.t(
                    "Het kostenmodel kon niet uit de database gelezen worden. "
                    "De reden staat in het logboek van de berekening; zolang ze "
                    "niet verholpen is, blijft de marge onbeschikbaar.",
                    "Le modèle de coûts n'a pas pu être lu depuis la base de "
                    "données. La raison figure dans le journal du calcul ; tant "
                    "qu'elle n'est pas résolue, la marge reste indisponible.",
                )
            return (kmdb.model_uit_rijen(*rijen) if rijen else None), None
        return km.lees_kostenmodel(KOSTEN_PAD, MARGES_PAD), None
    except (ValueError, TypeError) as fout:
        return None, str(fout)


def _schrijf(pad: Path, inhoud: dict) -> None:
    """Atomair wegschrijven: eerst een tijdelijk bestand, dan os.replace.

    De dev-server en de PDF-route lezen deze bestanden terwijl wij schrijven;
    een half JSON-bestand zou een scherm laten omvallen op precies het moment
    dat iemand op Instellingen opslaat.

    Onder DROOG wordt er niets geschreven. Tot 18 aug 2026 negeerde dit
    script de vlag, terwijl `make sync-droog` "zonder schrijven" beloofde:
    een droge proef overschreef dan stil het laatste goede contract. De hele
    bouw — beide talen, alle winkels, alle wachten — draait wél.
    """
    if droge_modus():
        print(f"DROOG: {pad.relative_to(REPO)} niet geschreven")
        return
    tmp = pad.with_name(pad.name + ".tmp")
    tmp.write_text(json.dumps(inhoud, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, pad)


def bouw_antwoorden(verkopen: pd.DataFrame, kalender: pd.DataFrame,
                    groepen: pd.Series, *, voorspeller, bijgewerkt, vandaag,
                    kosten_model, kosten_fout, kanaalkost, bonnen, uren,
                    kalenderdekking=None, sluitingsdekking=None,
                    bevestigde_dagen=frozenset()):
    """De zeven contractantwoorden voor één gegevensset: het geheel, of — met
    de winkelindeling uit winkels.json — de filialen van één winkel.

    Geeft (antwoorden, kerngegevens-voor-de-afdruk) terug. De prognose blijft
    per gegevensset gebacktest: een winkel met minder dan MIN_TRAIN gemeten
    dagen krijgt geen prognose maar een reden (harde regels 7 en 8).
    """
    open_verkopen = bk.open_verkopen(verkopen, kalender)
    dagtotalen = bk.dagtotalen(open_verkopen)
    tot = bk.peildatum(open_verkopen, "winkel")
    bronnen = sorted(open_verkopen["kanaal"].unique())

    # De prognose draait op dezelfde reeks als de backtest, zodat de band die
    # getoond wordt uit de fouten van precies deze methode op precies deze data komt.
    reeks = (
        dagtotalen[dagtotalen["kanaal"] == "winkel"]
        .set_index("datum")["omzet"]
        .sort_index()
    )

    # De doeldagen komen uit de kalender en niet uit pd.date_range. De oude versie
    # nam HORIZON kalenderdagen na de laatste meting, en dat leverde op 12 augustus
    # 2026 een verwacht weektotaal op voor 1 t/m 7 augustus: een week waarin de
    # bakkerij geen dag open was, en die op het moment van tonen al voorbij was.
    # De horizonregel staat in canoniek.prognosevenster, met een test.
    venster = canoniek.prognosevenster(kalender, gemeten_tot=tot, vandaag=vandaag,
                                       horizon=HORIZON)

    # De zeef hierboven slaat aangekondigde sluitingen over, maar alleen die in
    # de lijst staan. Op 15 augustus 2026 stond de zomersluiting er als 17 t/m
    # 23 augustus in terwijl ze op 1 augustus begonnen was, en het scherm zette
    # een omzetverwachting op 15 en 16 augustus. Deze wacht kijkt naar de
    # aansluiting tussen de meting en de lijst: eindigt de meting in een
    # gesloten reeks die de lijst niet verklaart, dan meldt hij dat. Hij
    # corrigeert niets -- het platform verzint geen sluitingskalender.
    lopende = sluitingsdagen.lopende_sluiting(kalender, venster.dagen)

    resultaat = track = dek = None
    if len(reeks) >= MIN_TRAIN + HORIZON:
        resultaat = evalueer(reeks, voorspeller, naam=voorspeller_naam(),
                             min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)

        # De band per dag komt uit de kwantielen van de eigen horizonstap, niet uit
        # één gepoolde band: die is te breed voor morgen en te smal voor over een
        # week. De kwantielen zelf zijn sinds 13 augustus gekalibreerd: de meting
        # liet zien dat een nominale 10-90-band out-of-sample maar 56 à 74% dekt,
        # dus kiest kalibreer_kwantielen het smalste paar dat het dekkingsdoel wél
        # haalt, out-of-sample gemeten. Daarnaast het trackrecord (voorspeld naast
        # werkelijk, elke dag out-of-sample) als eerlijkheidsmeting.
        kal = kalibreer_kwantielen(reeks, voorspeller, doel=BAND_DOEL,
                                   min_train=MIN_TRAIN, stap=7, horizon=HORIZON)
        stappen = per_horizon(reeks, voorspeller, onder=kal.onder, boven=kal.boven,
                              min_train=MIN_TRAIN, stap=7, horizon=HORIZON)
        blik = band_per_stap(voorspeller(reeks, venster.dagen), stappen)
        # Eén doorloop voor 180 dagen; de grafiek toont er de jongste 28 van
        # en de modelkaart meet ook op 90 en 180 (de audit-vraag: is 28 dagen
        # trackrecord genoeg voor vertrouwen? nee).
        track_vol = trackrecord(reeks, voorspeller, dagen=180,
                                min_train=MIN_TRAIN, horizon=HORIZON)
        track = track_vol.tail(28).reset_index(drop=True)
        dek = kal.dekking

        # De opbouw per doeldag (basis x niveau x kalenderfactoren), met exact
        # dezelfde rekenkern én dezelfde vlaggen als de voorspeller — de test
        # in test_verfijning pint de rekenkern vast, prognosekalender() de
        # vlaggen.
        opb = (opbouw(reeks, venster.dagen, prognosekalender(kalender),
                      kenmerken=KENMERKEN)
               if len(venster.dagen) > 0 else None)

        def _venster_meting(dagen_terug: int):
            """WAPE en bias over de jongste `dagen_terug` gemeten open dagen,
            uit dezelfde out-of-sample voorspellingen als het trackrecord.
            None wanneer het venster er niet vol is: een cijfer over 90 dagen
            dat er maar 60 bevat, zou liegen over zijn eigen naam."""
            if len(track_vol) < dagen_terug:
                return None, None
            t = track_vol.tail(dagen_terug)
            som_w = float(t["werkelijk"].sum())
            if som_w <= 0:
                return None, None
            fout = t["verwacht"] - t["werkelijk"]
            return (float(fout.abs().sum()) / som_w,
                    float(fout.sum()) / som_w)

        wape_90, bias_90 = _venster_meting(90)
        wape_180, bias_180 = _venster_meting(180)
        meting = {
            "n_dagen": resultaat.n_dagen,
            "van": reeks.index[MIN_TRAIN].date(),
            "tot": reeks.index[-1].date(),
            "bias": (resultaat.som_fout / resultaat.som_werkelijk
                     if resultaat.som_werkelijk else 0.0),
            "wape_90": wape_90, "bias_90": bias_90,
            "wape_180": wape_180, "bias_180": bias_180,
        }

        # Blok 15b: per categorie een eigen prognose met een eigen gemeten fout.
        # De som van de categorieën is als dagmodel getoetst en won niet materieel
        # (0,42 punt WAPE op een lat van 0,5); de dagprognose blijft dus direct.
        cat_reeksen = categorie_reeksen(open_verkopen, groepen, top_n=6)
        categorieen, cat_overgeslagen = categorie_prognoses(
            cat_reeksen, voorspeller, venster.dagen,
            onder=kal.onder, boven=kal.boven, horizon=HORIZON,
        )
        prognose_antwoord = ct.prognose(
            blik, bron=bronnen, bijgewerkt_op=bijgewerkt,
            baseline_naam=voorspeller_naam(),
            wape=resultaat.wape, venster=venster,
            stappen=stappen, track=track, banddekking=dek,
            band_kwantielen=(kal.onder, kal.boven),
            band_doel=BAND_DOEL,
            categorieen=categorieen,
            categorieen_overgeslagen=cat_overgeslagen,
            kalenderdekking=kalenderdekking,
            sluitingsdekking=sluitingsdekking,
            bevestigde_dagen=bevestigde_dagen,
            lopende_sluiting=lopende,
            opbouw=opb, meting=meting)

        # Blok 22, achter een vlag in afwachting van vraag 55: dezelfde
        # gebackteste motor met een andere kalenderinvoer, nooit een vrije
        # schuif. Zonder PROGNOSE_SCENARIOS=1 bestaat het veld niet, en de
        # UI toont het hoe dan ook niet — voorbereiden mag, tonen niet.
        if os.environ.get("PROGNOSE_SCENARIOS") == "1":
            omschrijving = {
                "als_vakantieweek": tl.t(
                    "Alsof elke dag in dit venster een schoolvakantiedag is "
                    "(Franstalig regime).",
                    "Comme si chaque jour de cette fenêtre était un jour de "
                    "vacances scolaires (régime francophone).",
                ),
                "zonder_vakantie": tl.t(
                    "Alsof geen enkele dag in dit venster vakantie is.",
                    "Comme si aucun jour de cette fenêtre n'était en vacances.",
                ),
                "zonder_correctie": tl.t(
                    "De kale weekdagmediaan, zonder vakantiecorrectie.",
                    "La médiane par jour de la semaine, sans correction des "
                    "vacances.",
                ),
            }
            prognose_antwoord["data"]["scenarios"] = [
                {
                    "sleutel": s.sleutel,
                    "omschrijving": omschrijving[s.sleutel],
                    # Via ct._s zoals elk bedrag in het contract: half-up op
                    # de cent, nooit een float-formatter (inspectie 18 aug).
                    "weektotaal": ct._s(s.weektotaal),
                    "dagen": [
                        {"datum": d.date().isoformat(), "verwacht": ct._s(v)}
                        for d, v in s.dagen.items()
                    ],
                }
                for s in scenario_prognoses(
                    reeks, venster.dagen, prognosekalender(kalender),
                    # Dezelfde wikkel als de productievoorspeller, uit
                    # dezelfde module: een scenario varieert de kalenderINVOER
                    # binnen het gebackteste mechanisme, niet het mechanisme.
                    basis=BASIS, maak_voorspeller=wikkel,
                )
            ]
    else:
        # Geen backtest mogelijk, dus geen prognose: een voorspelling zonder
        # gemeten fout is een mening (harde regel 7).
        prognose_antwoord = ct.antwoord({}, bron=bronnen,
                                        bijgewerkt_op=bijgewerkt,
                                        gemeten_tot=tot, onbeschikbaar=[{
            "veld": "prognose",
            "reden": (f"Te weinig historiek voor een gebackteste prognose: "
                      f"{len(reeks)} gemeten dagen, minstens "
                      f"{MIN_TRAIN + HORIZON} nodig. Deze verkopen tellen wel "
                      "gewoon mee in het totaal; de prognose verschijnt "
                      "vanzelf zodra er genoeg historiek ligt."),
        }])

    # De kwaliteitslaag kijkt naar álle kanalen en alle rijen, dus naar de
    # canonieke verkopen vóór de open-dagen-filter. De datums gaan als `date`
    # mee, zoals de kwaliteitslaag ze verwacht.
    kwaliteit = kw.stand(
        verkopen.assign(datum=verkopen["datum"].dt.date),
        kalender.assign(datum=kalender["datum"].dt.date),
        vandaag=vandaag,
        bonnen_df=bonnen,
        uren_df=uren,
    )

    antwoorden = {
        "overzicht": ct.overzicht(dagtotalen, tot, kalender=kalender,
                                  bonnen=bonnen, bron=bronnen,
                                  bijgewerkt_op=bijgewerkt, gemeten_tot=tot,
                                  prognose_methode=voorspeller_naam()),
        "kanalen": ct.kanalen(dagtotalen, tot, bron=bronnen, bijgewerkt_op=bijgewerkt,
                              gemeten_tot=tot,
                              # Binnen de taallus, dus t() kiest hier de taal;
                              # de constante zelf blijft Nederlands (import).
                              ontbrekend={"deliveroo": tl.t(DELIVEROO_REDEN,
                                                            DELIVEROO_REDEN_FR)},
                              kanaalkost=kanaalkost),
        "producten": ct.producten(open_verkopen, groepen, tot, bron=bronnen,
                                  bijgewerkt_op=bijgewerkt, gemeten_tot=tot),
        "marge": ct.marge(open_verkopen, groepen, kosten_model, tot,
                          bron=bronnen, bijgewerkt_op=bijgewerkt,
                          gemeten_tot=tot, invoer_fout=kosten_fout),
        "prognose": prognose_antwoord,
        "stand": ct.stand(kwaliteit, bron=bronnen, bijgewerkt_op=bijgewerkt,
                          gemeten_tot=tot),
        # De kandidatenlijst voor het scherm Sluitingsdagen. De uitspraken
        # zelf leest het scherm rechtstreeks uit de database; dit antwoord
        # draagt alleen wat de berekeningslaag weet (de feestdagen en de
        # dekking van de oude bestandslijst).
        "sluitingsdagen": ct.sluitingsdagen(
            vandaag=vandaag, sluitingsdekking=sluitingsdekking,
            bron=bronnen, bijgewerkt_op=bijgewerkt, gemeten_tot=tot),
    }

    # De briefing bovenaan elk scherm (blok 21). Signalering en geen advies: de
    # motor rekent, de UI toont. Ze hangt in de envelope naast `onbeschikbaar`
    # en niet in `data`, want het is hetzelfde soort metagegeven over het
    # scherm — en dan hoeft geen enkele schermfunctie een parameter erbij.
    for scherm, brief in _briefings(
            open_verkopen=open_verkopen, dagtotalen=dagtotalen,
            groepen=groepen, kalender=kalender, verkopen=verkopen,
            kosten_model=kosten_model, kosten_fout=kosten_fout,
            kanaalkost=kanaalkost, bonnen=bonnen, uren=uren, tot=tot,
            vandaag=vandaag,
            venster=venster, resultaat=resultaat, dek=dek,
            kalenderdekking=kalenderdekking,
            sluitingsdekking=sluitingsdekking,
            bevestigde_dagen=bevestigde_dagen).items():
        antwoorden[scherm] = ct.met_briefing(antwoorden[scherm], brief)
    info = {"tot": tot, "bronnen": bronnen, "venster": venster,
            "resultaat": resultaat, "track": track, "dek": dek,
            "kwaliteit": kwaliteit, "reeks_dagen": len(reeks)}
    return antwoorden, info


def bouw_en_schrijf(uitmap: Path, *, verkopen, kalender, groepen, voorspeller,
                    bijgewerkt, vandaag, kosten_model, kosten_fout, kanaalkost,
                    bonnen, uren, kalenderdekking, sluitingsdekking,
                    bevestigde_dagen, winkels, winkels_fout, stil=False):
    """Alle antwoorden voor de ingestelde taal, naar `uitmap`.

    De taal staat op dat moment in `bakkerij/taal.py` en bepaalt elk label en
    elke reden die hieruit komt. De cijfers zijn identiek: dezelfde
    berekeningslaag, dezelfde invoer, alleen andere tekst. Dat is de hele
    belofte van het contract — één waarheid, meerdere consumenten (harde
    regel 4) — nu ook over talen heen.
    """
    antwoorden, info = bouw_antwoorden(
        verkopen, kalender, groepen, voorspeller=voorspeller,
        bijgewerkt=bijgewerkt, vandaag=vandaag, kosten_model=kosten_model,
        kosten_fout=kosten_fout, kanaalkost=kanaalkost, bonnen=bonnen,
        uren=uren, kalenderdekking=kalenderdekking,
        sluitingsdekking=sluitingsdekking,
        bevestigde_dagen=bevestigde_dagen)

    for naam, inhoud in antwoorden.items():
        _schrijf(uitmap / f"{naam}.json", inhoud)

    # --- de winkelcontracten, naast het totaal --------------------------------
    # De map wordt eerst geleegd: een winkel die uit de indeling verdwijnt,
    # mag niet als spookmap blijven staan. Behalve onder DROOG: wissen is
    # ook schrijven.
    winkels_dir = uitmap / "winkels"
    if winkels_dir.exists() and not droge_modus():
        shutil.rmtree(winkels_dir)
    index: dict = {"winkels": [], "niet_toegewezen": [], "melding": winkels_fout,
                   "overgeslagen": []}
    if winkels:
        filiaal_ids = set(verkopen["filiaal_id"].astype(str))
        index["niet_toegewezen"] = list(wk.niet_toegewezen(filiaal_ids, winkels))
        for w in winkels:
            deel = verkopen[verkopen["filiaal_id"].isin(w.filialen)]
            bonnen_deel = (bonnen[bonnen["filiaal_id"].astype(str)
                                  .isin(w.filialen)]
                           if bonnen is not None else None)
            try:
                # uren=None: de urenextractie draagt geen filiaal_id, en het
                # urenbeeld van het geheel aan één winkel toeschrijven zou
                # een meting tonen die er voor die winkel niet is.
                w_antwoorden, w_info = bouw_antwoorden(
                    deel, kalender, groepen, voorspeller=voorspeller,
                    bijgewerkt=bijgewerkt, vandaag=vandaag,
                    kosten_model=kosten_model, kosten_fout=kosten_fout,
                    kanaalkost=None, bonnen=bonnen_deel, uren=None,
                    kalenderdekking=kalenderdekking,
                    sluitingsdekking=sluitingsdekking,
                    bevestigde_dagen=bevestigde_dagen)
            except ValueError as fout:
                # Naar de index en niet alleen naar stdout: een winkel die
                # stil uit de kiezer verdwijnt is onvindbaar voor wie het
                # scherm leest, en de terugval op het totaal ziet eruit als
                # een keuze (audit 15 aug, punt a). De reden bevat aantallen
                # en veldnamen, geen datarijen.
                index["overgeslagen"].append({"naam": w.naam, "reden": str(fout)})
                if not stil:
                    print(f"  winkel {w.naam!r} overgeslagen: {fout}")
                continue
            doel = winkels_dir / w.slug
            doel.mkdir(parents=True, exist_ok=True)
            for naam, inhoud in w_antwoorden.items():
                _schrijf(doel / f"{naam}.json", inhoud)
            index["winkels"].append({"naam": w.naam, "slug": w.slug})
            if not stil:
                print(f"  winkel {w.naam:<20} {len(deel):>9,} rijen, "
                      f"{w_info['reeks_dagen']} gemeten dagen")
    _schrijf(uitmap / "winkels.json", index)
    return antwoorden, info


#: Velden waarvan de inhoud een mens leest. De rest van het contract is
#: machinewaarde (bedragen, enums, ISO-datums) en heeft geen taal.
#:
#: Deze lijst was tot 17 augustus 2026 acht velden lang, en dat was een gat in
#: de wacht: het briefingproza (kop, waarom, nodig), kolomkoppen, drempels en
#: de tekstuele waarden van de modelkaart deden niet mee aan de telling. Een
#: onvertaalde kolomkop bestond dus niet voor de teller. Nu staat hier elk veld
#: waarvan de visuele steekproef of de veldinventaris liet zien dat er tekst
#: voor mensen in staat; `waarde` is meestal een machinegetal, maar de
#: cijferfilter hieronder laat die vanzelf door.
LEESBARE_VELDEN = (
    "label", "reden", "titel", "toelichting", "omschrijving", "naam", "x",
    "eenheid",
    # tabellen: koppen (lijstitems tellen mee via _veldnaam), drempelwoorden,
    # de uitlegkolom van een ontbinding, en tekstwaarden zoals de modelnaam
    "kolommen", "drempel", "uitleg", "waarde", "weekdag",
    # het briefingproza van blok 21, dat tot 17 augustus 2026 buiten de
    # telling viel
    "kop", "waarom", "nodig", "statuswoord", "leeg",
)

#: Velden waarvan de inhoud uit de BRON komt en dus niet vertaald hoort te
#: worden. Productnamen staan zoals de bakkerij ze in Odoo heeft ingevoerd; een
#: vertaald assortiment zou namen tonen die op geen enkele kassabon staan.
#: `x` zijn aslabels: weekdagen en maanden uit de taaltabellen (die per
#: constructie vertaald zijn, en waar "nov 25" in beide talen zo hoort) en
#: groeps- of kanaalnamen uit de bron.
BRONVELDEN = ("product_naam", "product", "categorie", "x")

#: Paden waar een `naam`-veld een productnaam uit Odoo draagt. Alleen daar is
#: een identieke naam vanzelfsprekend; elders (een reeksnaam als "Omzet 30
#: dagen") is een identiek `naam`-veld gewoon onvertaald.
BRONPADEN = (
    "data.top.*.naam",
    "data.groepen_detail.*.producten.*.naam",
    "data.verschuiving.stijgers.*.naam",
    "data.verschuiving.dalers.*.naam",
)

#: Paden waar een veld dat elders leesbaar is, tóch machinewaarde draagt: een
#: wachter heet met zijn sleutel (`dubbele_sleutels`) en het leesbare woord
#: staat in de UI-vertaling; zijn `toelichting` — het echte proza — telt
#: gewoon mee.
MACHINEPADEN = ("data.wachters.*.naam",)

#: Merknamen, afkortingen en vaktermen die in elke taal zo heten. Expliciet en
#: kort: elke naam hier is een beslissing, geen lengteheuristiek. "Backtest"
#: staat in het contract als t("Backtest", "Backtest") — het Franse proza
#: gebruikt hetzelfde woord.
MERKNAMEN = {"Deliveroo", "Too Good To Go", "Odoo", "WAPE", "Backtest"}


def _veldnaam(pad: str) -> str:
    """Het veld waar een tekst onder hangt: het laatste niet-numerieke stuk van
    het pad, zodat een lijstitem (`kolommen.1`) bij zijn lijstnaam telt."""
    for deel in reversed(pad.split(".")):
        if not deel.isdigit():
            return deel
    return ""


def _leesbare_teksten(knoop, pad="", uit=None) -> dict:
    """Alle mensleesbare teksten uit een contractantwoord, per pad.

    Het pad (bijvoorbeeld `data.concentratie.rijen.0.label`) is de sleutel,
    zodat de Nederlandse en de Franse boom paar voor paar te vergelijken zijn.
    Tot 17 augustus 2026 kreeg een scalar alleen zijn eigen veldnaam als pad;
    daardoor kon de bron-uitzondering alleen op veldnaam werken en nooit op de
    plek in de boom — en gleed een lijst van kolomkoppen er helemaal uit, want
    het laatste padstuk van een lijstitem is zijn index.
    """
    if uit is None:
        uit = {}
    if isinstance(knoop, dict):
        for k, v in knoop.items():
            _leesbare_teksten(v, f"{pad}.{k}" if pad else k, uit)
    elif isinstance(knoop, list):
        for i, v in enumerate(knoop):
            _leesbare_teksten(v, f"{pad}.{i}", uit)
    elif (isinstance(knoop, str) and _veldnaam(pad) in LEESBARE_VELDEN
          and not any(fnmatch(pad, patroon) for patroon in MACHINEPADEN)):
        uit[f"{pad}#{len(uit)}"] = knoop
    return uit


def _hoort_gelijk(pad: str, tekst: str) -> bool:
    """Of een tekst die in beide talen identiek is, dat ook hóórt te zijn."""
    kaal = pad.split("#")[0]
    if _veldnaam(kaal) in BRONVELDEN:
        return True
    if tekst in MERKNAMEN:
        return True
    return any(fnmatch(kaal, patroon) for patroon in BRONPADEN)


def vergelijk_talen(nl_antwoorden: dict,
                    fr_antwoorden: dict) -> tuple[list[str], set[str]]:
    """(werk, hoort_zo): de mensleesbare teksten die in beide talen identiek
    zijn, gescheiden in wat nog vertaald moet worden en wat zo hoort.

    De scheiding is expliciet — bronvelden, productnaam-paden, merknamen — en
    geen heuristiek. De eerdere grens "drie woorden of minder zal wel een
    productnaam zijn" legde precies de gevonden lekken opzij: "komt van",
    "29 producten" en "overige 8 producten" zijn alle drie kort, en geen van
    drieën een productnaam.
    """
    werk: set[str] = set()
    hoort_zo: set[str] = set()
    for scherm, inhoud_nl in nl_antwoorden.items():
        teksten_nl = _leesbare_teksten(inhoud_nl)
        teksten_fr = _leesbare_teksten(fr_antwoorden[scherm])
        for pad, tekst in teksten_nl.items():
            if teksten_fr.get(pad) != tekst:
                continue
            if not any(c.isalpha() for c in tekst):
                continue          # "€ 12.000", "2026"
            (hoort_zo if _hoort_gelijk(pad, tekst) else werk).add(tekst)
    return sorted(werk), hoort_zo


def vertaalrapport(per_taal: dict) -> None:
    """Wat er in de Franse contractmap nog Nederlands is, gemeten en niet geloofd.

    HOE DIT GEMETEN WORDT, EN WAAROM NIET ANDERS. De eerste versie hiervan
    telde alleen de teksten die door `taal.t()` gingen zonder Franse variant.
    Dat gaf op 14 augustus 2026 de melding "elke tekst bestaat in beide talen"
    terwijl de helft van het proza nog Nederlands was -- want die teksten gingen
    helemaal niet door `t()`. Een teller die alleen meet wat hij al kent, meldt
    schoon zodra je hem niet gebruikt, en dat is het gevaarlijkste soort groen.

    Daarom vergelijkt deze functie de twee gebouwde bomen: elke mensleesbare
    tekst die in beide talen letterlijk gelijk is, is verdacht. Een deel daarvan
    is terecht gelijk (productnamen uit Odoo, "Deliveroo", aslabels), en dat
    staat apart geteld. De rest is werk.

    TWEEDE LES, 17 AUGUSTUS 2026. Ook deze meting had mazen, en de visuele
    steekproef vond ze alle twee terug op het scherm. Eén: er werd maar een
    handvol velden gelezen, zodat kolomkoppen, drempels en het hele
    briefingproza buiten de telling vielen. Twee: alles van drie woorden of
    minder werd als "zal wel een productnaam zijn" opzijgelegd, zodat "komt
    van" en "overige 8 producten" onzichtbaar bleven. De veldenlijst is nu
    volledig en de uitzondering expliciet (zie `vergelijk_talen`).
    """
    nl = per_taal.get("nl")
    fr = per_taal.get("fr")
    if nl is None or fr is None:
        return

    proza, bron = vergelijk_talen(nl[0], fr[0])
    woorden = sum(len(s.split()) for s in proza)
    hoort_zo_zin = (
        f"Daarnaast zijn {len(bron)} teksten in beide talen gelijk op plekken "
        "waar dat hoort: productnamen uit Odoo, merknamen, aslabels."
    )

    print()
    REPORTS.mkdir(parents=True, exist_ok=True)
    if not proza:
        print("Vertaling: geen Nederlandse tekst meer in de Franse "
              f"contractmap. ({hoort_zo_zin})")
        # Het bestand wordt ook bij nul herschreven: een werklijst van
        # gisteren die blijft staan, is een werklijst die liegt.
        if not droge_modus():
            (REPORTS / "onvertaald.md").write_text(
                "# Nog niet in het Frans\n\nNiets. Elke mensleesbare tekst "
                "verschilt tussen de Nederlandse en de Franse contractmap, of "
                f"staat op een plek waar hij gelijk hoort te zijn. {hoort_zo_zin}\n",
                encoding="utf-8")
        return

    print(f"NOG NIET IN HET FRANS: {len(proza)} teksten, {woorden} woorden.")
    print(f"  (plus {len(bron)} teksten die in beide talen gelijk horen te "
          f"zijn: productnamen, merknamen, aslabels)")
    for s in proza[:4]:
        kort = s if len(s) <= 88 else s[:85] + "..."
        print(f"  - {kort}")
    if len(proza) > 4:
        print(f"  ... en {len(proza) - 4} andere")
    print("  volledige lijst: reports/onvertaald.md")

    regels = [
        "# Nog niet in het Frans",
        "",
        (
            f"Gemeten bij de contractbouw door de Nederlandse en de Franse "
            f"contractmap te vergelijken: {len(proza)} teksten, {woorden} "
            "woorden staan in beide talen identiek en zijn dus nog niet "
            "vertaald."
        ),
        "",
        (
            "Dit bestand is uitvoer en geen bron. Los een regel op door in "
            "`bakkerij/contract.py` een tweede argument aan `t(...)` te geven; "
            "hier iets invullen doet niets."
        ),
        "",
        hoort_zo_zin,
        "",
    ]
    regels += [f"- {s}" for s in proza]
    if not droge_modus():
        (REPORTS / "onvertaald.md").write_text("\n".join(regels) + "\n",
                                               encoding="utf-8")


def main() -> int:
    # Tot 18 aug 2026 las dit script géén .env, waardoor PROGNOSE_SCENARIOS
    # alleen als shell-variabele werkte — anders dan elke andere vlag hier.
    laad_env()
    verkopen_pad = INTERIM / "canoniek_verkopen.csv"
    if not verkopen_pad.exists():
        print("Geen canonieke data gevonden. Draai eerst: make canoniek")
        return 1
    verkopen = pd.read_csv(verkopen_pad, parse_dates=["datum"],
                           dtype=canoniek.CANONIEK_DTYPES)
    kalender_pad = INTERIM / "canoniek_kalender.csv"

    # De sluitingslijst wordt op twee plaatsen gelezen: de canoniekbouw bakt
    # haar in de kalender-CSV (gepland_dicht), en dit script leest haar vers
    # voor de dekkingswacht. Wie de lijst aanvult en dan alleen `make ui`
    # draait, krijgt een scherm dat de nieuwe dekking meldt terwijl de
    # prognose nog met de oude kalender rekent — twee waarheden op één scherm
    # (audit 15 aug, punt b). Daarom: een verse lijst naast een oudere
    # kalender is een harde stop, geen stille combinatie.
    if (SLUITINGEN_PAD.exists()
            and SLUITINGEN_PAD.stat().st_mtime > kalender_pad.stat().st_mtime):
        print("config/sluitingsdagen.json is jonger dan de canonieke "
              "kalender. Draai eerst: make canoniek")
        return 1

    kalender = pd.read_csv(kalender_pad, parse_dates=["datum"])

    voorspeller = bouw_voorspeller(kalender)
    groepen = laad_groepen()
    bijgewerkt = ct.nu()
    vandaag = bijgewerkt.date()

    bonnen_pad = INTERIM / "canoniek_bonnen.csv"
    uren_pad = INTERIM / "canoniek_uren.csv"
    bonnen = canoniek.laad_bonnen(bonnen_pad) if bonnen_pad.exists() else None
    uren = canoniek.laad_uren(uren_pad) if uren_pad.exists() else None

    # De kanaalkost per commissiekanaal (bruto/commissie per maand), voor de
    # financiële wig op het kanalenscherm. Optioneel: zonder tabel staat de
    # reden erbij.
    kanaalkost_pad = INTERIM / "canoniek_kanaalkost.csv"
    kanaalkost = (pd.read_csv(kanaalkost_pad, dtype={"maand": str})
                  if kanaalkost_pad.exists() else None)

    # Idem voor de winkelindeling: kapot bestand -> alleen het totaal, met de
    # reden in de index zodat de UI er niets stils van maakt.
    winkels, winkels_fout = (), None
    try:
        winkels = wk.lees_winkels(WINKELS_PAD)
    except (ValueError, TypeError) as fout:
        winkels_fout = str(fout)

    # De dekkingswacht kijkt naar het regime dat de voorspeller echt gebruikt.
    kalenderdekking = vakanties.dekking_tot(SCHOOLVAKANTIES_FR)

    # Tot waar de sluitingslijst reikt. Voorbij die datum betekent 'geen
    # sluiting bekend' niet 'open' maar 'onbekend', en het scherm zegt dat.
    sluitingsdekking = sluitingsdagen.dekking_tot(
        sluitingsdagen.lees_sluitingen(SLUITINGEN_PAD))

    # De dagen die een beheerder bevestigd open heeft verklaard, uit de
    # kalender-CSV en niet vers uit de database: de prognose rekent met deze
    # kalender, dus het voorbehoud moet dezelfde stand beschrijven. Een
    # uitspraak die ná de canoniekbouw is opgeslagen, telt vanaf de volgende
    # herrekening — en dat zegt het scherm Sluitingsdagen er ook bij.
    bevestigde_dagen = frozenset()
    if "bevestigd_open" in kalender.columns:
        open_vlag = canoniek.als_bool(kalender["bevestigd_open"])
        bevestigde_dagen = frozenset(
            pd.Timestamp(datum).date()
            for datum, v in zip(kalender["datum"], open_vlag, strict=True)
            if v
        )

    # Twee talen, twee contractmappen. Nederlands blijft op zijn plek staan
    # (platform/contract/), Frans komt eronder in fr/ — zo verhuist er geen
    # enkel bestaand pad en blijft de Nederlandse route exact zoals ze was.
    gedeeld = {
        "verkopen": verkopen, "kalender": kalender, "groepen": groepen,
        "voorspeller": voorspeller, "bijgewerkt": bijgewerkt,
        "vandaag": vandaag, "kanaalkost": kanaalkost,
        "bonnen": bonnen, "uren": uren, "kalenderdekking": kalenderdekking,
        "sluitingsdekking": sluitingsdekking,
        "bevestigde_dagen": bevestigde_dagen, "winkels": winkels,
        "winkels_fout": winkels_fout,
    }
    # De bron van de beheerinvoer: de database wanneer het platform daaruit
    # leest (dan schrijft het formulier daar ook), anders de bestanden zoals
    # altijd. Nooit beide -- zie kostenrijen_uit_db.
    kosten_bron = contract_bron()
    kosten_rijen, kosten_dbfout = None, None
    if kosten_bron == "db":
        kosten_rijen, kosten_dbfout = kostenrijen_uit_db()
        if kosten_dbfout is None:
            print(f"kostenmodel uit de database: "
                  f"{len(kosten_rijen[0])} criteria, "
                  f"{len(kosten_rijen[1])} ingevulde kosten")

    per_taal = {}
    for taal in tl.TALEN:
        doelmap = UIT if taal == tl.STANDAARDTAAL else UIT / taal
        doelmap.mkdir(parents=True, exist_ok=True)
        with tl.in_taal(taal):
            # Het kostenmodel wordt per taal opnieuw gebouwd, bínnen de
            # taalcontext: de foutmeldingen van de parser en de naam van het
            # v1-criterium ("Totale kost"/"Coût total") volgen t(), en buiten
            # de lus zouden ze op het Nederlands bevriezen. Een onleesbare
            # invoer mag de run niet stoppen, maar mag ook niet stil
            # verdwijnen: de reden gaat het antwoord in (harde regel 8).
            # De invoer is klein; twee keer toetsen kost niets.
            kosten_model, kosten_fout = kostenmodel_voor_taal(
                kosten_bron, kosten_rijen, kosten_dbfout)
            per_taal[taal] = bouw_en_schrijf(
                doelmap, stil=taal != tl.STANDAARDTAAL,
                kosten_model=kosten_model, kosten_fout=kosten_fout, **gedeeld)

    antwoorden, info = per_taal[tl.STANDAARDTAAL]
    tot, bronnen = info["tot"], info["bronnen"]
    venster, resultaat = info["venster"], info["resultaat"]
    track, dek, kwaliteit = info["track"], info["dek"], info["kwaliteit"]

    print("=" * 78)
    print("CONTRACT GEBOUWD")
    print("=" * 78)
    print(f"peildatum (laatste gemeten open winkeldag): {tot.date()}")
    print(f"vandaag                                   : {vandaag}")
    print(f"kanalen met data                          : {', '.join(bronnen)}")
    if resultaat is not None:
        print(f"prognose                                  : "
              f"{len(venster.dagen)} dagen vanaf {venster.start}, "
              f"{VOORSPELLER_NAAM}, WAPE {resultaat.wape:.1%}")
        gemeten_dekking = dek.dropna(subset=["binnen_band"])
        gemeten_dekking = gemeten_dekking[gemeten_dekking["n"] > 0]
        if not gemeten_dekking.empty:
            # Tegen het DOEL afrekenen en niet tegen `beloofd`. Dat laatste is
            # `boven - onder`, de nominale breedte van het gekozen kwantielpaar
            # (vandaag 0,05-0,95 = 90%), en dat is per ontwerp geen belofte:
            # `kalibreer_kwantielen` kiest juist een nominaal bredere band om er
            # out-of-sample BAND_DOEL van te maken. De regel las dus
            # "74%-85% (beloofd 90%)" en maakte van een gehaald doel een
            # mislukking -- in de enige uitvoer die wij bij elke bouw lezen.
            haalt = gemeten_dekking["binnen_band"].min() >= BAND_DOEL
            print(f"  banddekking out-of-sample               : "
                  f"{gemeten_dekking['binnen_band'].min():.0%}"
                  f"-{gemeten_dekking['binnen_band'].max():.0%} "
                  f"(doel {BAND_DOEL:.0%}, nominaal "
                  f"{gemeten_dekking['beloofd'].iloc[0]:.0%}"
                  f"{'' if haalt else '; niet elke stap haalt het doel'})")
        print(f"  trackrecord                             : {len(track)} dagen "
              f"out-of-sample")
    else:
        print(f"prognose                                  : onbeschikbaar, "
              f"{info['reeks_dagen']} gemeten dagen < {MIN_TRAIN + HORIZON}")
    print(f"datakwaliteit (ergste)                    : {kwaliteit['ergste']}")
    if venster.overgeslagen:
        print(f"  overgeslagen (gemeten gesloten)         : "
              f"{', '.join(str(d) for d in venster.overgeslagen)}")
    if venster.buiten_kalender:
        print(f"  zonder kalenderrij (als onbekend mee)   : "
              f"{len(venster.buiten_kalender)} dagen")
    if venster.meetgat is not None:
        gat = venster.meetgat
        print(f"  meetgat                                 : {gat.van} t/m {gat.tot} "
              f"({gat.dagen} dagen: {gat.gemeten_gesloten} gemeten gesloten, "
              f"{gat.gepland_dicht} gepland dicht, "
              f"{gat.niet_ingeladen} niet ingeladen)")
    if venster.sluiting is not None:
        s = venster.sluiting
        opnieuw = s.eerste_open_dag or "onbekend (kalender reikt niet verder)"
        print(f"  sluiting vandaag                        : dicht sinds "
              f"{s.dicht_sinds} ({s.dagen} dagen"
              f"{', ' + s.reden if s.reden else ''}), eerste open dag "
              f"{opnieuw}")
    print()
    for naam, inhoud in antwoorden.items():
        pad = UIT / f"{naam}.json"
        n_onb = len(inhoud["onbeschikbaar"])
        merk = f"{n_onb} onbeschikbaar" if n_onb else "volledig"
        print(f"  {naam:<12} {pad.stat().st_size:>7,} bytes   {merk}")
    vertaalrapport(per_taal)

    print(f"\nWeggeschreven naar {UIT.relative_to(REPO)}/ (nl) en "
          f"{(UIT / 'fr').relative_to(REPO)}/ (fr), beide gitignored.")
    print("Start het platform met:  cd platform && npm run dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
