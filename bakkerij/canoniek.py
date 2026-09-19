"""Het canonieke datamodel: alle kanalen naar één verkooptabel, plus de kalender.

Dit is laag 1 uit CLAUDE.md. Elke bron wordt hier genormaliseerd naar:

    datum | filiaal_id | product_id | product_naam | kanaal | aantal | omzet_excl_btw

Drie beslissingen die niet uit de code zelf blijken:

KASSA'S — alle drie tellen mee. De meting van 12 augustus (scripts/kassa_analyse.py,
data-audit addendum 3) weerlegde dat twee van de drie kassa's andere concepten
zijn: alle drie verkopen hetzelfde bakkerijassortiment in vrijwel dezelfde
verhoudingen. Filteren op één kassa zou ~2/3 van de bakkerijomzet weggooien.
`filiaal_id` blijft staan zodat uitsplitsen een rapportagekwestie is zodra de
opdrachtgever bevestigt wat de drie zijn (vraag 18, aanname A11).

SLUITINGSDAGEN — geen meting, geen nul. Een dag zonder kassaverkoop van betekenis
binnen het gemeten bereik betekent: de zaak was dicht. Die dag krijgt in de
kalender `winkel_open = False`. Wie hem als nulverkoop meetelt, leert het model
dat er in augustus geen vraag naar brood is. Buiten het gemeten bereik weten we
niets: `winkel_gemeten = False`.

"Van betekenis" is nodig omdat een sluitingsdag niet altijd volledig leeg is;
zie DREMPEL_OPEN hieronder. De losse bonregels op zo'n dag blijven wél in de
verkooptabel staan — het zijn echte transacties, en de feitentabel liegt niet.
De interpretatie zit in de kalender, en `alleen_open_dagen` en
`prognosevenster` zijn de enige twee plekken waar erop gefilterd wordt: de
eerste kijkt naar het verleden, de tweede naar de dagen die nog moeten komen.
"""

from __future__ import annotations

import datetime as dt
import gzip
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pandas as pd

from bakkerij.features.calendar import kalender as bouw_basiskalender

KANALEN = ("winkel", "deliveroo", "overig")

# De kanalen waar een platform een commissie inhoudt, en waar netto dus niet
# gelijk is aan bruto. Deze lijst bestaat om één stille fout te voorkomen:
# zodra de Deliveroo-historiek binnenkomt (S1) zou dat kanaal zonder deze
# lijst een commissie van € 0 en bruto = netto tonen — bij een platform dat
# 25 à 35% inhoudt. Geen fout, geen lege kolom, gewoon een verkeerd cijfer.
#
# Wie hier een kanaal bij zet zonder dat de kanaalkosttabel het kent, krijgt
# vanaf nu een onbeschikbaar-melding in plaats van een nul. Dat is de bedoeling.
KANALEN_MET_COMMISSIE = ("deliveroo",)

KOLOMMEN = ["datum", "filiaal_id", "product_id", "product_naam",
            "kanaal", "aantal", "omzet_excl_btw"]

# De dtypes waarmee elke lezer van canoniek_verkopen.csv de sleutelkolommen
# moet inlezen. Niet optioneel, en niet per script opnieuw te bedenken.
#
# `product_id` is een IDENTIFICATIE en geen getal. Vandaag komt hij als int64
# uit de CSV, en dan werkt alles. Eén rij met een lege waarde -- een
# Deliveroo-regel zonder koppeling -- maakt er float64 van, en dan levert
# `.astype(str)` verderop
# "123.0" op waar de productgroepenindex "123" verwacht. Gevolg: geen fout,
# geen lege tabel, maar een assortiment dat stilzwijgend volledig onder
# "Overige" belandt, inclusief het margebeeld. De totalen blijven kloppen, dus
# niemand ziet het.
#
# Dat is precies het soort stille fout waarvoor deze laag bestaat. Wie een
# nieuwe lezer van de canonieke CSV schrijft, gebruikt deze mapping.
CANONIEK_DTYPES = {
    "filiaal_id": str,
    "product_id": str,
    "product_naam": str,
    "kanaal": str,
}

# Waarom Deliveroo leeg is, in één zin die de UI letterlijk mag tonen.
# De constante blijft Nederlands (module-constanten bevriezen bij import en
# kennen geen taal); wie hem in het contract zet, kiest via taal.t() tussen
# deze en de Franse variant eronder.
DELIVEROO_REDEN = ("Nog geen Deliveroo Orders-export opgeladen. Te doen: uit "
                   "Partner Hub -> Reports halen en opladen via het scherm "
                   "Deliveroo-import (venster van 12 maanden, schuift "
                   "dagelijks op)")
DELIVEROO_REDEN_FR = ("Aucun export Orders Deliveroo chargé. À faire : le "
                      "récupérer dans Partner Hub -> Reports et le charger via "
                      "l'écran Import Deliveroo (fenêtre de 12 mois, avance "
                      "chaque jour)")

# Een sluitingsdag met één losse bon is nog steeds een sluitingsdag.
#
# Gemeten op 12 augustus 2026 over de 534 dagen met kassaverkoop: vijf dagen
# hadden 1 tot 6 bonregels en € 0,03 tot € 54,18 omzet. Alle vijf liggen
# middenin een sluitingsperiode (paassluiting 2025, Nieuwjaar 2026,
# zomersluiting 2026). Uitgedrukt als aandeel van de mediaan van hun eigen
# weekdag zitten ze op 0,00 tot 0,004. De laagste échte openingsdag zit op 0,67.
# Tussen 0,004 en 0,67 ligt geen enkele dag, dus de drempel is niet kritisch:
# 0,10 heeft een factor 25 marge naar onder en 6,7 naar boven.
#
# Zonder deze zeef belanden die vijf dagen als echte openingsdagen in de
# baselines en in de backtest, waar ze elk een fout ter grootte van een volle
# dagomzet opleveren — en dat is een gemeten artefact, geen voorspelfout.
DREMPEL_OPEN = 0.10

# Onder dit aantal dagen per weekdag is een mediaan geen mediaan. Dan laten we
# de drempel vallen en houden we het bij 'er was verkoop', zichtbaar in de
# aanname in plaats van stilzwijgend.
MIN_DAGEN_PER_WEEKDAG = 8

# Hoe ver de kalender doorloopt voorbij de laatste dag met verkoop.
#
# De kalender leidt zijn bereik af uit de verkopen en stopt dus op de laatste
# gemeten dag. Een prognose begint bij vandaag of later, en dat is per definitie
# ná die dag: zonder overloop bestaat er voor geen enkele voorspelde dag een
# kalenderrij, en dan valt niet na te gaan of de winkel dan open is. Zestig
# dagen is ruim genoeg voor een horizon van een week plus een extract dat bijna
# twee maanden achterloopt.
#
# Voor die dagen staat `winkel_gemeten` op False — we weten niets. Weekdag,
# feestdag en brugdag zijn wél gevuld, want die volgen uit de datum zelf.
VOORUIT_DAGEN = 60


def laad_winkel(pad) -> pd.DataFrame:
    """Lees het Odoo-werkextract. Dat staat al in de canonieke vorm."""
    df = pd.read_csv(pad, dtype={"filiaal_id": str, "product_id": str,
                                 "product_naam": str, "kanaal": str})
    ontbreekt = set(KOLOMMEN) - set(df.columns)
    if ontbreekt:
        raise ValueError(f"Odoo-extract mist kolommen: {sorted(ontbreekt)}")
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    return df[KOLOMMEN]


BONNEN_KOLOMMEN = ["datum", "filiaal_id", "bonnen"]
UREN_KOLOMMEN = ["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"]


def laad_bonnen(pad) -> pd.DataFrame:
    """Lees de bonnen-per-dag-extractie (scripts/odoo_bonnen.py).

    Dit is een distinct-count aan de bron; het aantal bonnen per dag is NIET
    de som van de bonnen per product-dag uit de urenextractie — een bon met
    drie producten telt daar drie keer.
    """
    df = pd.read_csv(pad, dtype={"filiaal_id": str})
    ontbreekt = set(BONNEN_KOLOMMEN) - set(df.columns)
    if ontbreekt:
        raise ValueError(f"Bonnen-extract mist kolommen: {sorted(ontbreekt)}")
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    return df[BONNEN_KOLOMMEN]


def laad_uren(pad) -> pd.DataFrame:
    """Lees de eerste/laatste-verkoopuur-extractie (scripts/odoo_laatste_uur.py)."""
    df = pd.read_csv(pad)
    ontbreekt = set(UREN_KOLOMMEN) - set(df.columns)
    if ontbreekt:
        raise ValueError(f"Uren-extract mist kolommen: {sorted(ontbreekt)}")
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    return df[UREN_KOLOMMEN]


def tarief_voor(maand: str, tabel: pd.Series) -> float:
    """De commissie van de maand zelf, anders de meest recente eerdere.

    Vóór de eerste bekende maand nemen we de eerste die er is: beter een
    tarief van één maand later dan stilzwijgend bruto rekenen.

    Publiek sinds 19 augustus 2026, en daarom `tarief_voor` en niet meer
    `_commissie_voor`. `berekening._tarief_voor` was een byte-identieke kopie,
    verantwoord met "geen import van een private functie uit de inlaadlaag" —
    maar `berekening` importeert hier al uit (`alleen_open_dagen`), dus er was
    geen cykel om te vermijden. Twee kopieën die uiteenlopen, laten de
    commissiewig op het kanalenscherm afwijken van de netto-omzet in het
    canonieke model, en dat is precies het cijfer dat niemand naast elkaar
    legt tot het te laat is.
    """
    if maand in tabel.index:
        return float(tabel[maand])
    eerder = tabel[tabel.index < maand]
    return float(eerder.iloc[-1]) if not eerder.empty else float(tabel.iloc[0])


# --- Deliveroo ---------------------------------------------------------------
#
# Het kanaal komt binnen als Orders-exports uit Partner Hub (zie
# bakkerij/sources/deliveroo_parse.py). Wat hier staat, zet die bestellingen
# om naar de canonieke vorm en naar de kanaalkosttabel. De keuzes staan in
# docs/beslissingen.md, 19 september 2026; de kern:
#
#   * DAGNIVEAU, GEEN ARTIKELNIVEAU. Het Items Sold-rapport draagt geen datum
#     en geen bestelnummer (het telt op over de hele downloadperiode), dus een
#     omzet per artikel per dag bestaat niet in wat Deliveroo levert. De
#     beslissing van 25 aug (een `dl-`-product per artikel) ging van iets
#     anders uit en is daarmee vervallen. Per dag per vestiging staat er één
#     rij, met één synthetisch product; `aantal` is het aantal bestellingen.
#   * NETTO IN `omzet_excl_btw`, zoals bij TGTG (beslissing 28 aug): het
#     subtotaal min de commissie. De btw op de commissie is aftrekbaar en dus
#     geen kost. Het btw-regime van het subtotaal zelf blijft onbevestigd; dat
#     voorbehoud staat als onbeschikbaar-item op het kanalenscherm.
#   * DE COMMISSIE PER MAAND IS EEN GEMETEN GEMIDDELDE, geen tarief. Bij TGTG
#     was `commissie_per_stuk` een vast tarief van de maandfactuur; hier is het
#     de som van de commissies gedeeld door het aantal bestellingen. Wie er
#     later een voorspelling op bouwt, moet dat weten (beslissing 25 aug).

#: Het ene product waaronder Deliveroo per dag per vestiging staat. Een `dl-`
#: prefix, om dezelfde reden als in CANONIEK_DTYPES: id's uit twee bronnen in
#: één naamruimte botsen stil, en een botsing met een Odoo-productnummer zou
#: bestellingen onder een brood laten vallen.
DELIVEROO_PRODUCT_ID = "dl-bestellingen"
DELIVEROO_PRODUCT_NAAM = "Deliveroo-bestellingen"

KANAALKOST_KOLOMMEN = ["kanaal", "maand", "stuks", "bruto_per_stuk",
                       "commissie_per_stuk", "inhouding_pct"]


def laad_deliveroo_orders(paden) -> list:
    """Leest elke Orders-export en ontdubbelt over de bestanden heen.

    Downloads overlappen (de historiek kwam in blokken van ~16 dagen, waarvan
    twee elkaar overlappen), dus dezelfde bestelling kan in twee bestanden
    staan. De sleutel is (datum, vestiging, bestelnummer) en niet het
    bestelnummer alleen: dat is kort en per vestiging, en botst dus tussen
    winkels. Ontdubbelen gebeurt hier en niet in de parser, want de parser
    kent één bestand en dit is een eigenschap van de verzameling.
    """
    from bakkerij.sources.deliveroo_parse import parse_orders

    uniek: dict = {}
    for pad in paden:
        for r in parse_orders(_lees_tekst(pad)):
            uniek[(r.datum, r.store_id, r.order_id)] = r
    return list(uniek.values())


def _lees_tekst(pad) -> str:
    """Een export als tekst, ook als hij gecomprimeerd in de postbus ligt.

    De postbus bewaart bytes en vraagt niet wat ze zijn. Een Partner Hub-CSV
    van een halve megabyte wordt met gzip zes keer kleiner, en voor de
    historiek van twaalf maanden (23 downloads) is dat het verschil tussen
    een oplading die past en een die niet past. De extensie beslist; de
    inhoud is daarna dezelfde tekst als bij een kale CSV.
    """
    pad = Path(pad)
    if pad.suffix == ".gz":
        with gzip.open(pad, "rt", encoding="utf-8") as fh:
            return fh.read()
    return pad.read_text(encoding="utf-8")


def orders_naar_canoniek(regels) -> pd.DataFrame:
    """Van Orders-regels naar canonieke verkooprijen: per dag per vestiging
    één rij op het product DELIVEROO_PRODUCT_ID, `aantal` = bestellingen,
    `omzet_excl_btw` = subtotaal min commissie (netto, op de cent)."""
    if not regels:
        return pd.DataFrame(columns=KOLOMMEN)
    per: dict = {}
    for r in regels:
        s = per.setdefault((r.datum, r.store_id),
                           {"aantal": 0, "netto": Decimal(0)})
        s["aantal"] += 1
        s["netto"] += r.subtotaal - r.commissie
    rijen = [{
        "datum": datum,
        "filiaal_id": str(store),
        "product_id": DELIVEROO_PRODUCT_ID,
        "product_naam": DELIVEROO_PRODUCT_NAAM,
        "kanaal": "deliveroo",
        "aantal": float(s["aantal"]),
        "omzet_excl_btw": float(s["netto"].quantize(Decimal("0.01"))),
    } for (datum, store), s in sorted(per.items())]
    return pd.DataFrame(rijen, columns=KOLOMMEN)


def kanaalkost_deliveroo(regels) -> pd.DataFrame:
    """De kanaalkost van Deliveroo per maand, in de vorm van fact_kanaalkost.
    `stuks` is het aantal bestellingen; de twee bedragen per stuk zijn
    gemeten gemiddelden over die maand, geen tarief."""
    if not regels:
        return pd.DataFrame(columns=KANAALKOST_KOLOMMEN)
    per: dict = {}
    for r in regels:
        m = f"{r.datum.year:04d}-{r.datum.month:02d}"
        s = per.setdefault(m, {"n": 0, "bruto": Decimal(0),
                               "commissie": Decimal(0)})
        s["n"] += 1
        s["bruto"] += r.subtotaal
        s["commissie"] += r.commissie
    rijen = []
    for maand, s in sorted(per.items()):
        inhouding = (s["commissie"] / s["bruto"]) if s["bruto"] else Decimal(0)
        rijen.append({
            "kanaal": "deliveroo",
            "maand": maand,
            "stuks": float(s["n"]),
            "bruto_per_stuk": round(float(s["bruto"] / s["n"]), 4),
            "commissie_per_stuk": round(float(s["commissie"] / s["n"]), 4),
            "inhouding_pct": round(min(max(float(inhouding), 0.0), 1.0), 4),
        })
    return pd.DataFrame(rijen, columns=KANAALKOST_KOLOMMEN)


def bouw_verkopen(*delen: pd.DataFrame) -> pd.DataFrame:
    """Voeg de kanalen samen tot één tabel en bewaak de vorm."""
    df = pd.concat([d[KOLOMMEN] for d in delen], ignore_index=True)
    vreemd = set(df["kanaal"].unique()) - set(KANALEN)
    if vreemd:
        raise ValueError(f"Onbekend kanaal: {sorted(vreemd)}")
    return df.sort_values(["datum", "kanaal", "filiaal_id", "product_id"],
                          kind="stable").reset_index(drop=True)


def kanaalstatus(verkopen: pd.DataFrame) -> list[dict]:
    """Per canoniek kanaal: is er data, en zo ja over welk bereik.

    Dit voedt het 'onbeschikbaar'-blok van het contract (harde regel 8):
    een kanaal zonder data wordt getoond als onbeschikbaar met reden,
    nooit stilzwijgend weggelaten.
    """
    status = []
    for kanaal in ("winkel", "deliveroo"):
        deel = verkopen[verkopen["kanaal"] == kanaal]
        if deel.empty:
            reden = DELIVEROO_REDEN if kanaal == "deliveroo" else "Geen data ingeladen"
            status.append({"kanaal": kanaal, "beschikbaar": False,
                           "van": None, "tot": None, "reden": reden})
        else:
            status.append({"kanaal": kanaal, "beschikbaar": True,
                           "van": deel["datum"].min(), "tot": deel["datum"].max(),
                           "reden": ""})
    return status


def _open_dagen(dagomzet: pd.Series, weekdag: pd.Series) -> set:
    """Welke dagen de winkel echt open was, op basis van de dagomzet.

    Twee zeven. De eerste: er was omzet. De tweede: die omzet is niet
    verwaarloosbaar tegenover wat die weekdag normaal doet — zie DREMPEL_OPEN
    voor de meting waarop dat rust.

    De mediaan wordt berekend over de dagen die de eerste zeef halen, dus over
    een verzameling waarin de sluitingsdagen nog zitten. Dat mag: een mediaan
    verdraagt een handvol uitschieters, en in deze data is het 5 op 534. Bij
    een weekdag met te weinig dagen valt de drempel weg (MIN_DAGEN_PER_WEEKDAG).

    `dagomzet` en `weekdag` zijn geïndexeerd op datum.
    """
    if dagomzet.empty:
        return set()
    wd = weekdag.reindex(dagomzet.index)
    mediaan = dagomzet.groupby(wd).median()
    aantal = dagomzet.groupby(wd).size()
    drempel = (mediaan * DREMPEL_OPEN).where(aantal >= MIN_DAGEN_PER_WEEKDAG, 0.0)
    return set(dagomzet.index[dagomzet >= wd.map(drempel)])


def bouw_kalender(verkopen: pd.DataFrame, *,
                  vooruit: int = VOORUIT_DAGEN) -> pd.DataFrame:
    """De kalender over het volledige bereik van alle kanalen, plus overloop.

    Naast de vaste kenmerken (weekdag, feestdag, brugdag) twee kolommen die
    het verschil dragen tussen 'dicht' en 'niet gemeten':

      winkel_gemeten  de datum valt binnen het bereik van het Odoo-extract
      winkel_open     er was die dag kassaverkoop van betekenis (_open_dagen)

    `winkel_open` is alleen betekenisvol waar `winkel_gemeten` waar is.

    De tabel loopt `vooruit` dagen door voorbij de laatste dag met verkoop, want
    de prognose heeft kalenderrijen nodig voor dagen die nog moeten komen; zie
    VOORUIT_DAGEN. Met `vooruit=0` stopt de kalender op de laatste dag met
    verkoop — bruikbaar wanneer alleen het gemeten verleden telt.
    """
    if verkopen.empty:
        raise ValueError("Geen verkoopdata om een kalender op te bouwen")
    if vooruit < 0:
        raise ValueError("vooruit kan niet negatief zijn")
    eind = pd.Timestamp(verkopen["datum"].max()) + dt.timedelta(days=vooruit)
    df = bouw_basiskalender(verkopen["datum"].min(), eind)
    df["datum"] = df["datum"].dt.date

    winkel = verkopen[verkopen["kanaal"] == "winkel"]
    if winkel.empty:
        df["winkel_gemeten"] = False
        df["winkel_open"] = False
        return df

    van, tot = winkel["datum"].min(), winkel["datum"].max()
    df["winkel_gemeten"] = df["datum"].map(lambda d: van <= d <= tot)

    dagomzet = winkel.groupby("datum")["omzet_excl_btw"].sum()
    weekdag = df.set_index("datum")["weekdag"]
    open_dagen = _open_dagen(dagomzet, weekdag)
    df["winkel_open"] = df["datum"].map(open_dagen.__contains__)
    return df


def alleen_open_dagen(verkopen: pd.DataFrame, kalender: pd.DataFrame) -> pd.DataFrame:
    """Houd van het kanaal winkel alleen de dagen over die echt open waren.

    De kanonieke filter op `winkel_open`: elke afgeleide tabel en elke
    baseline gaat hierdoor, zodat de losse bonregels van een sluitingsdag
    nergens als openingsdag meetellen. Niet de énige plek die op de kolom
    filtert — dat beweerde deze docstring tot 18 augustus 2026 ten onrechte —
    maar wie er zelf op filtert (berekening, kwaliteit, de scripts), moet
    `winkel_gemeten` erbij nemen: zie de valkuil hieronder. Hier volstaat
    `winkel_open` alleen, omdat verkoopregels per definitie binnen het
    gemeten bereik vallen — een kalenderdag erbuiten heeft geen bonregels om
    weg te filteren. Andere kanalen blijven ongemoeid: Deliveroo kent geen
    winkelsluiting.
    """
    # Via `als_bool` en niet als kale mask: dit is de openingsfilter waar de
    # hele berekeningslaag onder hangt. Wordt `winkel_open` ooit een
    # object-kolom (één NaN uit de CSV volstaat), dan is elke waarde een
    # niet-lege string en telt élke dag als open — of, bij "False"-strings,
    # juist geen enkele. Zie de docstring van `als_bool`.
    open_dagen = set(kalender.loc[als_bool(kalender["winkel_open"]), "datum"])
    is_winkel = verkopen["kanaal"] == "winkel"

    # De datumtypes moeten aan beide kanten gelijk zijn, en dat is hier geen
    # muggenzifterij. `pd.Timestamp` erft van `datetime.date`, maar hasht
    # anders -- een set van `date` vindt daarom nooit een `Timestamp`. Loopt de
    # ene kant als `date` binnen en de andere als `Timestamp`, dan matcht er
    # níéts, valt het volledige kanaal winkel weg, en gebeurt dat zonder één
    # foutmelding: de tabellen blijven kloppen, ze zijn alleen leeg. De vier
    # aanroepers zijn vandaag toevallig consistent, en toevallig is geen wacht.
    if is_winkel.any() and open_dagen:
        kalendertype = type(next(iter(open_dagen)))
        verkooptype = type(verkopen.loc[is_winkel, "datum"].iloc[0])
        if kalendertype is not verkooptype:
            raise TypeError(
                f"Datumtypes lopen uiteen: de kalender draagt {kalendertype.__name__} "
                f"en de verkopen {verkooptype.__name__}. Zo matcht geen enkele dag "
                "en verdwijnt het kanaal winkel stilzwijgend. Zet beide op "
                "hetzelfde type vóór deze aanroep."
            )

    houden = ~is_winkel | verkopen["datum"].map(open_dagen.__contains__)
    return verkopen[houden].reset_index(drop=True)


# --- welke dagen een prognose krijgen --------------------------------------
#
# De baseline zegt in zijn eigen moduledocstring dat de beller de sluitingsdagen
# eruit moet laten: op een dag dat de zaak dicht is valt er niets te voorspellen.
# Dit is die beller, op één plek en met een test.
#
# De valkuil zit in de makkelijke versie. Filteren op alleen `winkel_open` werkt
# voor het verleden en sloopt de toekomst: buiten het gemeten bereik staat
# winkel_open óók op False, dus zo'n filter houdt geen enkele toekomstige dag
# over. `winkel_open` is alleen betekenisvol waar `winkel_gemeten` waar is, en
# alleen die combinatie mag een dag wegsnijden.


def _als_datum(waarde) -> dt.date:
    """Elke datumvorm (date, Timestamp, string) naar één `date`."""
    return pd.Timestamp(waarde).date()


def _status_per_dag(kalender: pd.DataFrame) -> dict[dt.date, tuple[bool, bool]]:
    """datum -> (winkel_gemeten, winkel_open). Eén keer opbouwen, vaak bevragen.

    Via `als_bool` en niet via een kale `bool(...)`: zie de docstring daar.
    `bool("False")` is True, en deze twee kolommen komen uit een CSV zonder
    dtype-opgave. Vandaag leest pandas ze goed omdat er alleen True en False
    in staan; één NaN of één handmatige regel maakt er een object-kolom van,
    en dan kantelt de hele kalender zonder foutmelding. Deze dict voedt de
    bronwachters, de censureringsdrempel, de sluitingsstand en het
    prognosevenster — de plek waar dat het duurst zou zijn.
    """
    gemeten = als_bool(kalender["winkel_gemeten"])
    open_ = als_bool(kalender["winkel_open"])
    return {
        _als_datum(datum): (bool(g), bool(o))
        for datum, g, o in zip(kalender["datum"], gemeten, open_, strict=True)
    }


def als_bool(reeks: pd.Series) -> pd.Series:
    """Een waarheidskolom naar echte booleans, ook als ze uit een CSV komt.

    `astype(bool)` is hier de verkeerde functie en de fout is stil: de string
    "False" is een niet-lege string en wordt dus True. De kalender gaat via
    `canoniek_kalender.csv` en pandas leest een kolom van louter True/False
    correct als bool — maar één NaN of één handmatige aanpassing maakt er een
    object-kolom van, en dan zou elke dag als gesloten gelden. Een prognose die
    door een dtype in het niets verdwijnt, is erger dan een verkeerde prognose.
    """
    if reeks.dtype == bool:
        return reeks
    def waar(w) -> bool:
        if isinstance(w, str):
            return w.strip().lower() in ("true", "1", "ja", "waar")
        if pd.isna(w):
            return False
        return bool(w)

    return reeks.map(waar).astype(bool)


def _gepland_dicht_per_dag(kalender: pd.DataFrame) -> dict[dt.date, str]:
    """datum -> reden, voor de dagen die vooraf als gesloten zijn aangekondigd.

    De kolom komt uit `sources/agenda.py` (iCal-feed) of uit
    `sluitingsdagen.py` (configlijst), of uit beide. Ontbreekt ze, dan is er
    geen sluitingskennis en is dit leeg -- niet "alles open".
    """
    if "gepland_dicht" not in kalender.columns:
        return {}
    dicht = kalender[als_bool(kalender["gepland_dicht"])]
    redenen = (
        dicht["gepland_dicht_reden"].fillna("")
        if "gepland_dicht_reden" in dicht.columns
        else pd.Series("", index=dicht.index)
    )
    return {
        _als_datum(datum): str(reden)
        for datum, reden in zip(dicht["datum"], redenen, strict=True)
    }


@dataclass(frozen=True)
class Meetgat:
    """De dagen tussen de laatste meting en vandaag: geen cijfer, geen prognose.

    Het gat is geen detail. Stond het extract op 31 juli en is het 12 augustus,
    dan bestaan er elf dagen waarover het platform niets zegt, en de gebruiker
    hoort te weten waaróm. Er zijn drie redenen, en ze vertellen drie heel
    verschillende verhalen:

      gemeten_gesloten  de kassa heeft die dag gemeten en de zaak bleek dicht.
                        Er is niets te tonen omdat er niets verkocht is.
      gepland_dicht     niet gemeten, maar vooraf als gesloten aangekondigd
                        (`gepland_dicht`, uit de agenda of de sluitingslijst).
                        Ook hier valt er niets te laden: de deur was dicht.
      niet_ingeladen    niet gemeten, en door geen enkele bron verklaard. DIT
                        is de achterstand, en de enige van de drie waar het
                        platformbeheer iets aan moet doen.

    HET DERDE BAKJE IS ER PAS SINDS 18 AUGUSTUS 2026, en het ontbreken ervan
    was een echte fout. `niet_gemeten` heette wat nu `niet_ingeladen` heet, en
    het telde élke ongemeten dag — ook de dagen waarvan de kalender wist dat de
    bakkerij dicht was. Gevolg tijdens de zomersluiting (1 t/m 23 augustus): de
    briefing meldde "10 dagen die niet uit de bronsystemen zijn ingeladen" en
    vroeg het platformbeheer de nachtelijke synchronisatie na te kijken, terwijl
    er simpelweg niets te verkopen was. Een externe lezer concludeerde eruit dat
    het platform verouderde cijfers toonde. De kolom `gepland_dicht` bestond al
    en `prognosevenster` keek er al naar bij het kiezen van de dagen; alleen deze
    telling deed het niet. Precies dezelfde vorm als de fout van 14 augustus:
    de kennis lag er, niemand las hem.
    """

    van: dt.date
    tot: dt.date
    dagen: int
    gemeten_gesloten: int
    gepland_dicht: int
    niet_ingeladen: int


@dataclass(frozen=True)
class Sluitingsstand:
    """De bakkerij is vandaag dicht, en dit is wat het platform daarover weet.

    Bestaat om één misverstand uit te sluiten dat op het openingsscherm stond:
    cijfers die niet doorlopen tot vandaag zijn tijdens een sluiting geen
    achterstand maar de normale toestand. Het platform hoort dat te zeggen in
    plaats van te zwijgen (harde regel 8) én in plaats van alarm te slaan.

    `dicht_sinds` is de eerste dag van de aaneengesloten gesloten reeks waarin
    vandaag valt; `dagen` telt die reeks tot en met vandaag. Gesloten betekent
    hier: gemeten en dicht, of vooraf als gesloten aangekondigd — dezelfde
    tweedeling als in `prognosevenster`, en om dezelfde reden.

    `eerste_open_dag` is de eerste dag na vandaag die door geen van beide bronnen
    als gesloten bekend staat. None wanneer de kalender niet ver genoeg reikt om
    die dag aan te wijzen: dan weet het platform niet wanneer de zaak opengaat,
    en dat is iets anders dan "morgen".

    `reden` komt uit `gepland_dicht_reden` en is aangeleverde tekst; ze blijft
    staan zoals ze is ingevuld en wordt niet vertaald. Leeg wanneer de reeks
    alleen uit metingen blijkt en niemand haar heeft aangekondigd.
    """

    dicht_sinds: dt.date
    dagen: int
    reden: str
    eerste_open_dag: dt.date | None


@dataclass(frozen=True)
class Prognosevenster:
    """Het resultaat van de horizonregel: welke dagen erin zitten, en waarom niet."""

    gemeten_tot: dt.date
    vandaag: dt.date
    start: dt.date
    dagen: pd.DatetimeIndex
    overgeslagen: tuple[dt.date, ...]      # gemeten én gesloten: niets te voorspellen
    buiten_kalender: tuple[dt.date, ...]   # geen kalenderrij: als onbekend meegenomen
    meetgat: Meetgat | None
    #: Vooraf aangekondigde sluitingen in dit venster, als (datum, reden).
    #: Los van `overgeslagen` gehouden omdat het een ander verhaal op het
    #: scherm is: die dagen zijn gemeten en bleken dicht, deze zijn nog niet
    #: gemeten en gaan dicht zijn omdat de bakkerij dat zegt.
    gepland_gesloten: tuple[tuple[dt.date, str], ...] = ()
    #: De sluiting waarin vandaag valt, of None als de zaak vandaag open hoort
    #: te zijn. Zie `Sluitingsstand`.
    sluiting: Sluitingsstand | None = None


def _meetgat(status: dict[dt.date, tuple[bool, bool]],
             gepland: dict[dt.date, str],
             gemeten_tot: dt.date, vandaag: dt.date) -> Meetgat | None:
    """De dagen ná de laatste meting en vóór vandaag, geteld naar oorzaak.

    Drie bakjes, en de volgorde waarin een dag erin valt is niet vrij: de meting
    gaat voor. Een dag die gemeten is en dicht bleek, is gemeten — ook als er een
    sluiting voor aangekondigd stond. Dat is dezelfde voorrangsregel als in
    `prognosevenster` ("de meting is de waarheid"), zodat het scherm en deze
    telling dezelfde dag niet elk anders verklaren.

    Wat niet in een bakje valt: een dag die gemeten is en open bleek. Die kan er
    per definitie niet zijn — `gemeten_tot` is de jóngste gemeten open dag — en
    zou hij er zijn, dan is dat geen gat maar een fout in de kalender.
    """
    van = gemeten_tot + dt.timedelta(days=1)
    tot = vandaag - dt.timedelta(days=1)
    if tot < van:
        return None

    gesloten = aangekondigd = ongeladen = 0
    dag = van
    while dag <= tot:
        gemeten, open_ = status.get(dag, (False, False))
        if gemeten and not open_:
            gesloten += 1
        elif gemeten:
            pass
        elif dag in gepland:
            aangekondigd += 1
        else:
            ongeladen += 1
        dag += dt.timedelta(days=1)

    return Meetgat(van=van, tot=tot, dagen=(tot - van).days + 1,
                   gemeten_gesloten=gesloten, gepland_dicht=aangekondigd,
                   niet_ingeladen=ongeladen)


def _dicht_op(dag: dt.date, status: dict[dt.date, tuple[bool, bool]],
              gepland: dict[dt.date, str]) -> bool:
    """Weet het platform van deze dag dat de zaak dicht was of dicht gaat zijn?

    Precies de tweedeling van `prognosevenster`: gemeten én dicht, of vooraf
    aangekondigd. Niets weten is géén sluiting — een dag buiten het gemeten
    bereik en buiten de sluitingslijst geeft hier False.
    """
    gemeten, open_ = status.get(dag, (False, False))
    if gemeten:
        return not open_
    return dag in gepland


def _sluitingsstand(status: dict[dt.date, tuple[bool, bool]],
                    gepland: dict[dt.date, str], vandaag: dt.date,
                    kalender_tot: dt.date | None) -> Sluitingsstand | None:
    """De sluiting waarin vandaag valt, of None.

    Loopt de gesloten reeks voorbij het einde van de kalender, dan blijft
    `eerste_open_dag` None: verder dan de kalender reikt de kennis niet, en een
    datum verzinnen is hier hetzelfde als een cijfer verzinnen.
    """
    if not _dicht_op(vandaag, status, gepland):
        return None

    dicht_sinds = vandaag
    while _dicht_op(dicht_sinds - dt.timedelta(days=1), status, gepland):
        dicht_sinds -= dt.timedelta(days=1)

    # De reden van de eerste dag die er een draagt, vooraan beginnend: dat is de
    # reden van deze sluiting en niet die van de dag waarop iemand kijkt.
    reden = ""
    dag = dicht_sinds
    while dag <= vandaag and not reden:
        reden = gepland.get(dag, "")
        dag += dt.timedelta(days=1)

    eerste_open = vandaag + dt.timedelta(days=1)
    while _dicht_op(eerste_open, status, gepland):
        eerste_open += dt.timedelta(days=1)
    if kalender_tot is None or eerste_open > kalender_tot:
        eerste_open = None

    return Sluitingsstand(
        dicht_sinds=dicht_sinds,
        dagen=(vandaag - dicht_sinds).days + 1,
        reden=reden,
        eerste_open_dag=eerste_open,
    )


def sluitingsstand(kalender: pd.DataFrame, *, vandaag) -> Sluitingsstand | None:
    """Is de bakkerij vandaag dicht, en tot wanneer? Zie `Sluitingsstand`."""
    vandaag_d = _als_datum(vandaag)
    if kalender.empty:
        return None
    return _sluitingsstand(
        _status_per_dag(kalender), _gepland_dicht_per_dag(kalender), vandaag_d,
        max(kalender["datum"].map(_als_datum)),
    )


def prognosevenster(kalender: pd.DataFrame, *, gemeten_tot, vandaag,
                    horizon: int) -> Prognosevenster:
    """De dagen waarover een prognose iets mag zeggen.

    De horizonregel, op één plek en met een test:

        start = max(gemeten_tot + 1 dag, vandaag)
        loop vooruit en sla elke dag over die
            gemeten is en dicht bleek   (winkel_gemeten EN NIET winkel_open)
            of vooraf als dicht is aangekondigd  (gepland_dicht)
        neem zo `horizon` dagen

    Waarom `vandaag` meedoet: begint de prognose op de dag na de laatste meting
    terwijl die meting twaalf dagen oud is, dan voorspelt het scherm een week die
    al voorbij is. Dat is geen prognose.

    DE TWEEDE ZEEF IS ER PAS SINDS 14 AUGUSTUS 2026, en het ontbreken ervan was
    een echte fout. De regel hierboven luidde alleen "gemeten én dicht", en een
    toekomstige dag is per definitie niet gemeten. Gevolg: het scherm zette een
    omzetverwachting op een week waarin de zaak aangekondigd dicht is. De kolom
    `gepland_dicht` bestond al — `sources/agenda.py` vult hem uit de iCal-feed —
    maar niets keek ernaar bij het kiezen van de dagen.

    Wat NIET veranderd is: buiten het gemeten bereik én buiten de sluitingslijst
    weten we niets, en niets-weten is nog steeds geen sluiting. Die dagen gaan
    mee als gewone dagen. De aanname `prognose.sluitingsdagen` verschuift dus
    van "we kennen geen enkele toekomstige sluiting" naar "we kennen de
    sluitingen die aangeleverd zijn, en tot waar die lijst reikt staat op het
    scherm". Verzinnen doet het platform nog steeds niet.
    """
    if horizon < 0:
        raise ValueError("horizon kan niet negatief zijn")

    status = _status_per_dag(kalender)
    gepland = _gepland_dicht_per_dag(kalender)
    gemeten_tot_d, vandaag_d = _als_datum(gemeten_tot), _als_datum(vandaag)
    start = max(gemeten_tot_d + dt.timedelta(days=1), vandaag_d)

    gekozen: list[dt.date] = []
    overgeslagen: list[dt.date] = []
    gepland_over: list[tuple[dt.date, str]] = []
    buiten: list[dt.date] = []

    # Bovengrens tegen een eindeloze lus. Gesloten dagen komen nu uit twee
    # bronnen: gemeten sluitingen liggen binnen het gemeten bereik, geplande
    # binnen de sluitingslijst. Beide zijn eindig, dus de lus loopt af.
    dag, stappen = start, 0
    maximum = horizon + len(status) + len(gepland) + 1
    while len(gekozen) < horizon and stappen < maximum:
        stappen += 1
        gemeten, open_ = status.get(dag, (False, False))

        # Eerst de meting, want de meting is de waarheid: een dag die gemeten is
        # en open bleek, is open — ook als er een sluiting voor aangekondigd
        # stond. Die tegenspraak is een afwijking om te melden
        # (sluitingsdagen.afwijkingen, agenda.afwijkingen) en niet iets om hier
        # stil op te lossen.
        if gemeten and not open_:
            overgeslagen.append(dag)
            dag += dt.timedelta(days=1)
            continue

        if not gemeten and dag in gepland:
            gepland_over.append((dag, gepland[dag]))
            dag += dt.timedelta(days=1)
            continue

        if dag not in status:
            buiten.append(dag)
        gekozen.append(dag)
        dag += dt.timedelta(days=1)

    return Prognosevenster(
        gemeten_tot=gemeten_tot_d,
        vandaag=vandaag_d,
        start=start,
        dagen=pd.DatetimeIndex(gekozen, name="datum"),
        overgeslagen=tuple(overgeslagen),
        buiten_kalender=tuple(buiten),
        meetgat=_meetgat(status, gepland, gemeten_tot_d, vandaag_d),
        gepland_gesloten=tuple(gepland_over),
        sluiting=_sluitingsstand(
            status, gepland, vandaag_d,
            max(kalender["datum"].map(_als_datum)) if not kalender.empty else None,
        ),
    )
