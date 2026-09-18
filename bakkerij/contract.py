"""Contractlaag: van de afgeleide tabellen naar de JSON die de schermen lezen.

Dit is laag 4 uit CLAUDE.md, en de belangrijkste grens in het hele platform.
Boven deze laag wordt niet meer gerekend: de web-UI van vandaag en de app van
fase 2 lezen hetzelfde antwoord en tonen hetzelfde getal.

De vorm is gebonden in `platform/lib/contract.ts` en wordt hier gevolgd, niet
opnieuw uitgevonden. Twee regels uit dat bestand die hier gehandhaafd worden:

  * Bedragen, aantallen en percentages zijn STRINGS met punt-decimaal. Nooit een
    float in een antwoord, want een float in JSON is een afrondingsfout die
    onderweg ontstaat en niemand meer kan navertellen.
  * `number` komt uitsluitend voor als plotgeometrie — de y-waarde van een punt
    en de tickwaarden van een as. Elk label dat een mens leest, staat kant-en-
    klaar in de data, inclusief de aslabels.

ONBESCHIKBAAR IS EEN ANTWOORD

Harde regel 8. Een veld dat niet berekend kan worden, krijgt een regel in
`onbeschikbaar` met de reden erbij, en verschijnt niet als nul en niet als lege
plek. De marge is daar het voorbeeld van: die is niet "nog niet af", die is
geblokkeerd op data die de klant niet heeft, en dat hoort op het scherm te staan.

TWEE DATUMS IN DE ENVELOPPE, EN DAT IS GEEN VERDUBBELING

`bijgewerkt_op` is het moment waarop dit antwoord gebouwd is. `gemeten_tot` is de
jongste gemeten open winkeldag. Die twee lopen uiteen zodra een extract achterloopt
— op 12 augustus 2026 twaalf dagen — en wie alleen het eerste in de voettekst zet,
belooft verse cijfers die er niet zijn. Beide staan in elk van de vijf antwoorden.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pandas as pd

from bakkerij import berekening as bk
from bakkerij import canoniek
from bakkerij import kostenmodel as km
from bakkerij import sluitingskalender as sk
from bakkerij import taal as tl
from bakkerij.taal import t

# De projecttijdzone komt sinds 18 augustus 2026 uit bakkerij/tijd.py in
# plaats van een eigen ZoneInfo: één definitie, die niet kan gaan afwijken.
from bakkerij.tijd import BRUSSEL as TIJDZONE

VERSIE = 1

# De kanaal-, maand- en weekdagnamen staan sinds 14 augustus 2026 in
# bakkerij/taal.py, want ze bestaan in twee talen. Ze worden hier alleen nog
# via tl.* opgezocht; de eigen kopieën zijn op 18 augustus 2026 verwijderd.

# Over hoeveel kalenderweken het weekdagprofiel gemiddeld. Staat hier als
# constante omdat de toelichting op het scherm dit getal noemt: één plek, zodat
# tekst en berekening niet uit elkaar kunnen lopen.
PROFIEL_WEKEN = 8


def _s(waarde: Decimal | float) -> str:
    """Een machinewaarde als string. De enige manier waarop een getal het
    contract verlaat, tenzij het plotgeometrie is."""
    if isinstance(waarde, Decimal):
        return str(waarde)
    return str(bk.euro(waarde))


def _aantal(waarde: float) -> str:
    """Een aantal als string, half naar boven afgerond.

    Niet `round()`. Dat is bankiersafronding: round(1234.5) geeft 1234 en
    round(1235.5) geeft 1236. Aantallen kunnen hier fractioneel zijn (gewichts-
    producten), dus datzelfde aantal kan op twee schermen één stuk verschillen.
    `bk._stuks` bestaat precies hiervoor en rondt half naar boven.
    """
    return str(bk._stuks(float(waarde)))


def _iso_datum(datum: date | datetime | pd.Timestamp | None) -> str | None:
    """Een datum als ISO-string voor de enveloppe, of None als ze niet bestaat."""
    if datum is None:
        return None
    return pd.Timestamp(datum).date().isoformat()


def _datum_nl(datum: date | datetime | pd.Timestamp) -> str:
    """'31 juli 2026' / '31 juillet 2026'.

    De naam houdt het achtervoegsel `_nl` omdat hij overal in dit bestand staat
    en "voor een mens, niet voor een machine" betekent -- het tegenovergestelde
    van `_iso_datum`. Sinds 14 augustus 2026 volgt hij de ingestelde taal.
    """
    d = pd.Timestamp(datum)
    return f"{tl.dagnummer(d.day)} {tl.maand_vol(d.month)} {d.year}"


def _dagen_nl(aantal: int) -> str:
    enkel = t("dag", "jour")
    meer = t("dagen", "jours")
    return f"{aantal} {enkel}" if aantal == 1 else f"{aantal} {meer}"


def _producten_nl(aantal: int) -> str:
    """'29 producten', als kant-en-klare tekst. De UI plakt geen taal achter
    een getal: tot 17 augustus 2026 deed ze dat hier wél, en dus stond er
    "29 producten" midden in het Franse productmixscherm."""
    enkel = t("product", "produit")
    meer = t("producten", "produits")
    return f"{aantal} {enkel}" if aantal == 1 else f"{aantal} {meer}"


def _rest_label(aantal: int) -> str:
    """'overige 23 producten' onder een groepstabel. Eén functie voor beide
    talen, want het Frans zet het telwoord vóór 'autres' en is dus geen
    sjabloon met één gat."""
    if aantal == 1:
        return t("1 overig product", "1 autre produit")
    return t(f"overige {aantal} producten", f"{aantal} autres produits")


def _pct_machine(waarde: float | None) -> str | None:
    """Een percentage als machinewaarde: 8.4 -> '8.4'. Neemt een PERCENTAGE.

    De naam draagt de eenheid sinds 19 augustus 2026. Daarvoor heetten deze
    functie en haar buurvrouw `_pct` en `_pct_nl` — twee namen die één letter
    schelen terwijl hun invoer een factor 100 scheelt, en waarbij de
    verwisseling geen fout geeft maar een geloofwaardig cijfer dat honderd keer
    te groot of te klein is. Nu zegt de naam wat erin gaat.
    """
    if waarde is None:
        return None
    # ROUND_HALF_UP expliciet: tot 18 augustus 2026 stond hier de standaard
    # (bankiersafronding), terwijl de rest van het platform half-up rondt.
    return str(Decimal(str(waarde)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _pct_tekst(fractie: float) -> str:
    """Een percentage in lopende tekst: 0.084 -> '8,4 %'. Neemt een FRACTIE.

    De machinewaarden in het contract houden een punt-decimaal — daar rekent de
    frontend mee via `lib/format.ts`. Maar een reden in `onbeschikbaar` is een
    volzin die de klant leest, en "8.4%" staat daar verkeerd. De notatie zelf
    (komma, spatie) staat op één plek: `taal.procent_tekst`.

    Zie `_pct_machine` voor de reden dat de eenheid in de naam staat.
    """
    return tl.procent_tekst(fractie)


def _factor(waarde: float) -> str:
    """Een vermenigvuldigingsfactor als machinewaarde: '1.042'. Drie decimalen,
    want ×1,04 op een dagomzet is het verschil tussen twee zinvolle cijfers."""
    return f"{float(waarde):.3f}"


def _bias_nl(fractie: float) -> str:
    """'+0,4% (gemiddeld te hoog)'. Het teken volgt voorspeld − werkelijk."""
    richting = (
        t("te hoog", "trop élevé") if fractie >= 0 else t("te laag", "trop bas")
    )
    teken = "+" if fractie >= 0 else "−"
    gemiddeld = t("gemiddeld", "en moyenne")
    return f"{teken}{_pct_tekst(abs(fractie))} ({gemiddeld} {richting})"


def antwoord(
    data: Any,
    *,
    bron: list[str],
    bijgewerkt_op: datetime,
    gemeten_tot: date | datetime | pd.Timestamp | None,
    onbeschikbaar: list[dict] | None = None,
) -> dict:
    """De envelope om elk antwoord. Elk scherm draagt zijn eigen metadata.

    `gemeten_tot` is verplicht en mag None zijn, maar niet weggelaten worden: de
    versheid van de cijfers is geen bijzaak die je vergeet mee te geven. Is er
    geen gemeten dag, dan staat er null en toont het scherm dat als onbekend —
    niet als vandaag.
    """
    return {
        "versie": VERSIE,
        "bijgewerkt_op": bijgewerkt_op.isoformat(),
        "gemeten_tot": _iso_datum(gemeten_tot),
        "bron": bron,
        "onbeschikbaar": onbeschikbaar or [],
        # De briefing hoort bij de envelope en niet bij `data`: het is een
        # uitspraak óver dit scherm, net als `onbeschikbaar`, en niet een cijfer
        # dat erop staat. Standaard leeg, zodat een antwoord dat er nog geen
        # heeft gewoon een lege briefing draagt in plaats van een ontbrekend
        # veld — de UI hoeft dan nergens te raden.
        "briefing": {"punten": [], "leeg": ""},
        "data": data,
    }


def met_briefing(antw: dict, briefing: dict) -> dict:
    """Hetzelfde antwoord met zijn briefing erin, als nieuwe dict.

    Apart van `antwoord()` omdat de briefing pas te maken is als de
    schermfunctie klaar is: ze leest dezelfde uitkomsten. Zo hoeft geen enkele
    schermfunctie een parameter erbij, en blijft de plek waar de briefing
    ontstaat één regel in de contractbouw.
    """
    return {**antw, "briefing": briefing}


def _dag_label(datum: pd.Timestamp) -> str:
    return f"{tl.dagnummer(datum.day)} {tl.maand_kort(datum.month)}"


def _maand_label(jaar: int, maand: int) -> str:
    """'aug 25'. Twaalf van deze labels moeten naast elkaar op een as passen."""
    return f"{tl.maand_kort(maand)} {str(jaar)[2:]}"


def _richting(waarde: Decimal | float | None) -> str | None:
    """Op, neer, of geen van beide. Richting komt uit het teken, nooit uit kleur."""
    if waarde is None or waarde == 0:
        return None
    return "op" if waarde > 0 else "neer"


def _ontbinding(
    *, verschil: Decimal, verschil_label: str,
    termen: list[tuple[str, Decimal, str]], toelichting: str,
) -> dict:
    """De vaste vorm van een ontbinding: één gemeten verschil, en de termen
    waarin het uiteenvalt.

    De belofte van deze vorm is dat de termen exact optellen tot `verschil`, op
    de cent. De berekeningslaag levert dat zo aan (de kruisterm is daar de
    sluitpost); hier wordt het nagerekend en niet aangenomen, want een
    ontbinding die niet optelt is geen ontbinding maar een lijstje getallen.

    Een term draagt zijn eigen label en een korte uitleg in gewone taal: het
    scherm mag geen woorden verzinnen bij een cijfer, net zomin als het cijfers
    mag verzinnen bij een woord.
    """
    som = sum((t[1] for t in termen), Decimal(0))
    if som != verschil:
        raise ValueError(
            f"Ontbinding telt niet op: {som} tegenover {verschil}"
        )
    return {
        "verschil": {
            "label": verschil_label,
            "waarde": _s(verschil),
            "richting": _richting(verschil),
        },
        "termen": [
            {"label": label, "waarde": _s(bedrag), "uitleg": uitleg,
             "richting": _richting(bedrag)}
            for label, bedrag, uitleg in termen
        ],
        "toelichting": toelichting,
    }


def _euro_as(maximum: float) -> dict:
    """Een y-as met kant-en-klare eurolabels. De frontend kiest geen schaal."""
    ticks = bk.as_ticks(maximum)
    return {
        "ticks": [
            {"y": t, "label": "€ " + f"{int(t):,}".replace(",", ".")} for t in ticks
        ]
    }


def _lijn(
    punten: list[tuple[str, float]], naam: str, kleur: str, maximum: float
) -> dict:
    return {
        "reeksen": [
            {
                "naam": naam,
                "kleur": kleur,
                "punten": [{"x": x, "y": round(y, 2)} for x, y in punten],
            }
        ],
        "y_as": _euro_as(maximum),
    }


# --- de CFO-metrieken -------------------------------------------------------
#
# Zeven metrieken uit de berekeningslaag krijgen hier hun vorm. Ze delen drie
# eigenschappen, en die zijn belangrijker dan de velden zelf:
#
#   * elk blok kan `None` zijn, en dan staat er een regel in `onbeschikbaar` met
#     de reden. Nooit een nul, nooit een leeg vak (harde regel 8);
#   * elk label dat een mens leest, staat kant-en-klaar in de data. Het scherm
#     zet geen weekdagnamen, geen periodeteksten en geen woorden bij een cijfer;
#   * elke vergelijking loopt over gemeten open dagen, en waar twee vensters niet
#     even lang zijn, is het antwoord "geen vergelijking, en dit is waarom".

# Over hoeveel gemeten open dagen de weekdagmix middelt: acht volle weken, zodat
# elke weekdag ongeveer acht waarnemingen heeft. Constante omdat de toelichting
# op het scherm dit getal noemt.
MIX_DAGEN = 56
WEKEN_TERUG = 4
MAANDEN_TERUG = 12
CONCENTRATIE_DAGEN = 90
ONTBINDING_DAGEN = 30
BONRITME_DAGEN = 30
AFWIJKING_DAGEN = 90

#: De uitschieterdrempel en het minimum per weekdag, als tekst voor de
#: toelichting. Ze komen uit `berekening` en worden hier niet opnieuw gekozen:
#: tot 19 augustus 2026 schreef deze laag "3,5" en "acht" met de hand uit
#: terwijl `_afwijkende_dagen` geen van beide argumenten meegaf, zodat een
#: wijziging in de berekening het scherm stil liet liegen. De komma is het
#: decimaalteken in beide talen, dus één tekst volstaat voor nl en fr.
AFWIJKING_DREMPEL_TEKST = str(bk.AFWIJKING_DREMPEL).replace(".", ",")


def _bonritme(
    bonnen: pd.DataFrame | None, dagtotalen: pd.DataFrame, tot: pd.Timestamp,
    onbeschikbaar: list[dict],
) -> dict | None:
    """Omzet = bonnen × gemiddeld bonbedrag, en welke van de twee bewoog.

    Minder klanten is een ander probleem dan een kleinere mand. Het bedrag dat
    ontbonden wordt is de verandering in omzet **per dag**, niet over het hele
    venster: bonnen per dag en bonbedrag zijn dagcijfers, en hun product is dat
    dus ook.
    """
    if bonnen is None or bonnen.empty:
        onbeschikbaar.append({
            "veld": "bonritme",
            "reden": t(
                "Geen bonritme: de bonnentelling per dag is niet ingeladen. Het "
                "aantal bonnen komt uit een aparte extractie (een bon met drie "
                "producten is één klant, geen drie), en zonder die telling valt "
                "niet te zeggen of een omzetverandering van de klanten of van "
                "het mandje komt.",
                "Pas de rythme de tickets : le comptage quotidien des tickets "
                "n'est pas chargé. Le nombre de tickets provient d'une "
                "extraction distincte (un ticket portant trois produits, c'est "
                "un client et non trois), et sans ce comptage il est impossible "
                "de dire si une variation du chiffre d'affaires vient des "
                "clients ou du panier.",
            ),
        })
        return None

    rit = bk.bonritme(bonnen, dagtotalen, tot, dagen=BONRITME_DAGEN)
    if rit.bonnen_per_dag is None or rit.gemiddeld_bonbedrag is None:
        onbeschikbaar.append({
            "veld": "bonritme",
            "reden": t(
                f"Geen bonritme: over de laatste {_dagen_nl(BONRITME_DAGEN)} met "
                f"gemeten verkoop t/m {_dag_label(tot)} is er geen dag waarvoor "
                "zowel de omzet als het aantal bonnen bekend is.",
                f"Pas de rythme de tickets : parmi les "
                f"{_dagen_nl(BONRITME_DAGEN)} les plus récents avec des ventes "
                f"mesurées jusqu'au {_dag_label(tot)}, aucun jour ne porte à la "
                "fois le chiffre d'affaires et le nombre de tickets.",
            ),
        })
        return None

    kengetallen = [
        {"label": t("Klanten per dag", "Clients par jour"), "waarde": str(rit.bonnen_per_dag),
         "soort": "aantal", "richting": None},
        {"label": t("Gemiddeld bonbedrag", "Ticket moyen"), "waarde": _s(rit.gemiddeld_bonbedrag),
         "soort": "euro", "richting": None},
    ]

    ontbinding = None
    if rit.verschil is None:
        onbeschikbaar.append({
            "veld": "bonritme.ontbinding",
            "reden": t(
                f"Geen ontbinding in klanten en mandje: het venster t/m "
                f"{_dag_label(tot)} telt {_dagen_nl(rit.dagen)} waarvoor omzet én "
                f"bonnen bekend zijn, de periode ervoor {_dagen_nl(rit.vorig_dagen)}. "
                "Bij ongelijke vensters zegt het verschil meer over het aantal "
                "dagen dan over de klant.",
                f"Pas de décomposition en clients et panier : la fenêtre "
                f"jusqu'au {_dag_label(tot)} compte {_dagen_nl(rit.dagen)} pour "
                f"lesquels le chiffre d'affaires et les tickets sont connus, la "
                f"période précédente {_dagen_nl(rit.vorig_dagen)}. Avec des "
                "fenêtres inégales, l'écart en dit plus sur le nombre de jours "
                "que sur le client.",
            ),
        })
    else:
        ontbinding = _ontbinding(
            verschil=rit.verschil,
            verschil_label=t("Verandering in omzet per dag",
                             "Variation du chiffre d'affaires par jour"),
            termen=[
                (t("Meer of minder klanten", "Plus ou moins de clients"),
                 rit.bonneneffect,
                 t("Het aantal bonnen veranderde, bij het oude bonbedrag.",
                   "Le nombre de tickets a changé, à ticket moyen inchangé.")),
                (t("Groter of kleiner mandje", "Panier plus grand ou plus petit"),
                 rit.bonbedrag_effect,
                 t("Het gemiddelde bonbedrag veranderde, bij het oude aantal bonnen.",
                   "Le ticket moyen a changé, à nombre de tickets inchangé.")),
                (t("Beide tegelijk", "Les deux à la fois"), rit.kruisterm,
                 t("Het deel dat pas ontstaat doordat de twee samen bewegen.",
                   "La part qui ne naît que du mouvement simultané des deux.")),
            ],
            toelichting=t(
                f"De laatste {_dagen_nl(rit.dagen)} met gemeten verkoop t/m "
                f"{_dag_label(tot)}, naast even veel dagen ervoor. De drie termen "
                "tellen op de cent op tot de verandering erboven.",
                f"Les {_dagen_nl(rit.dagen)} les plus récents avec des ventes "
                f"mesurées jusqu'au {_dag_label(tot)}, face à autant de jours "
                "précédents. Les trois termes s'additionnent au centime près "
                "pour donner la variation ci-dessus.",
            ),
        )

    if rit.dagen_zonder_bonnen:
        onbeschikbaar.append({
            "veld": "bonritme.dagen_zonder_bonnen",
            "reden": t(
                f"{_dagen_nl(rit.dagen_zonder_bonnen).capitalize()} in dit bereik "
                "hebben wel omzet maar geen bonnentelling, en doen niet mee. Een "
                "dag met nul bonnen en wel omzet zou het gemiddelde bonbedrag "
                "oneindig maken.",
                f"{_dagen_nl(rit.dagen_zonder_bonnen).capitalize()} de cette "
                "période ont bien un chiffre d'affaires mais pas de comptage de "
                "tickets, et ne sont pas repris. Un jour à zéro ticket avec du "
                "chiffre d'affaires rendrait le ticket moyen infini.",
            ),
        })

    return {
        "kengetallen": kengetallen,
        "ontbinding": ontbinding,
        "toelichting": t(
            f"Gemiddeld over de laatste {_dagen_nl(rit.dagen)} met gemeten "
            f"verkoop t/m {_dag_label(tot)}. Eén bon is één klant, ook als er "
            "drie broden op staan.",
            f"Moyenne sur les {_dagen_nl(rit.dagen)} les plus récents avec des "
            f"ventes mesurées jusqu'au {_dag_label(tot)}. Un ticket est un "
            "client, même s'il porte trois pains.",
        ),
    }


def _weekdagmix(
    dagtotalen: pd.DataFrame, tot: pd.Timestamp, onbeschikbaar: list[dict],
) -> dict | None:
    """Welk deel van de weekomzet uit welke dag komt.

    Bewust alleen het aandeel en niet het gemiddelde: het weekdagprofiel op
    hetzelfde scherm toont al een gemiddelde per weekdag, over kalenderweken.
    Twee verschillende gemiddelden voor dezelfde zaterdag naast elkaar zetten is
    de zekerste manier om beide ongeloofwaardig te maken.
    """
    mix = bk.weekdagmix(dagtotalen, tot, dagen=MIX_DAGEN)
    if mix.empty:
        onbeschikbaar.append({
            "veld": "weekdagmix",
            "reden": t(
                f"Geen verdeling over de weekdagen: in de laatste "
                f"{_dagen_nl(MIX_DAGEN)} t/m {_dag_label(tot)} is geen open "
                "winkeldag gemeten.",
                f"Pas de répartition par jour de la semaine : sur les "
                f"{_dagen_nl(MIX_DAGEN)} les plus récents jusqu'au "
                f"{_dag_label(tot)}, aucun jour d'ouverture n'a été mesuré.",
            ),
        })
        return None

    rijen = [
        {"weekdag": tl.weekdag_kort(int(r.weekdag)),
         "naam": tl.weekdag(int(r.weekdag)),
         "aandeel": _pct_machine(float(r.aandeel_pct)),
         "meetdagen": int(r.meetdagen)}
        for r in mix.itertuples()
    ]

    ontbrekend = [tl.weekdag(wd) for wd in range(7)
                  if wd not in {int(r.weekdag) for r in mix.itertuples()}]
    if ontbrekend:
        onbeschikbaar.append({
            "veld": "weekdagmix.ontbrekende_dagen",
            "reden": t(
                f"Zonder aandeel: {', '.join(ontbrekend)}. Van die weekdag is in "
                f"dit venster geen open dag gemeten, en 0 % zou betekenen dat "
                "er die dag niets verkocht werd.",
                f"Sans part : {', '.join(ontbrekend)}. Aucun jour d'ouverture de "
                "ce jour de la semaine n'a été mesuré dans cette fenêtre, et "
                "0 % laisserait croire qu'il ne s'est rien vendu ce jour-là.",
            ),
        })

    return {
        "rijen": rijen,
        "toelichting": t(
            f"Aandeel van elke weekdag in de omzet van de laatste "
            f"{_dagen_nl(int(mix['meetdagen'].sum()))} met "
            f"gemeten verkoop t/m {_dag_label(tot)}. Dit venster loopt over "
            "gemeten open dagen; de grafiek hierboven middelt over kalenderweken. "
            "De twee zijn dus niet dezelfde zaterdag.",
            f"Part de chaque jour de la semaine dans le chiffre d'affaires des "
            f"{_dagen_nl(int(mix['meetdagen'].sum()))} les plus récents avec des "
            f"ventes mesurées jusqu'au {_dag_label(tot)}. Cette fenêtre porte "
            "sur des jours d'ouverture mesurés ; le graphique ci-dessus fait la "
            "moyenne sur des semaines calendrier. Les deux ne parlent donc pas "
            "du même samedi.",
        ),
    }


def _weken(
    dagtotalen: pd.DataFrame, kalender: pd.DataFrame, tot: pd.Timestamp,
    onbeschikbaar: list[dict],
) -> dict | None:
    """De laatste volledige kalenderweken, oudste eerst.

    Alleen volledige weken: de lopende week is per definitie korter en zou als
    een instorting op het scherm komen.
    """
    tabel = bk.weekomzet(dagtotalen, kalender, tot, weken=WEKEN_TERUG)
    rijen = [
        {"label": f"{_dag_label(r.van)} – {_dag_label(r.tot)}",
         "van": _iso_datum(r.van),
         "omzet": _s(r.omzet) if r.omzet is not None else None,
         "omzet_per_dag": _s(r.omzet_per_dag) if r.omzet_per_dag is not None
         else None,
         "open_dagen": int(r.open_dagen)}
        for r in tabel.itertuples()
    ]
    if all(r["omzet"] is None for r in rijen):
        onbeschikbaar.append({
            "veld": "weken",
            "reden": t(
                f"Geen weekcijfers: in de laatste {WEKEN_TERUG} volledige "
                f"kalenderweken t/m {_dag_label(tot)} is geen open winkeldag "
                "gemeten.",
                f"Pas de chiffres hebdomadaires : sur les {WEKEN_TERUG} "
                f"dernières semaines calendrier complètes jusqu'au "
                f"{_dag_label(tot)}, aucun jour d'ouverture n'a été mesuré.",
            ),
        })
        return None

    zonder = [r["label"] for r in rijen if r["omzet"] is None]
    if zonder:
        onbeschikbaar.append({
            "veld": "weken.gesloten",
            "reden": t(
                f"Zonder cijfer: {', '.join(zonder)}. In die weken is geen enkele "
                "open winkeldag gemeten — een sluiting of een gat in de meting, "
                "en in beide gevallen geen week met nul omzet.",
                f"Sans chiffre : {', '.join(zonder)}. Aucun jour d'ouverture n'a "
                "été mesuré ces semaines-là — une fermeture ou un trou dans la "
                "mesure, et dans les deux cas ce n'est pas une semaine à zéro.",
            ),
        })

    ongelijk = {r["open_dagen"] for r in rijen if r["omzet"] is not None}
    if len(ongelijk) > 1:
        onbeschikbaar.append({
            "veld": "weken.open_dagen",
            "reden": t(
                "Niet alle weken hier tellen even veel open dagen. Vergelijk in "
                "dat geval de omzet per open dag en niet het weektotaal: een "
                "korte week is geen slechte week.",
                "Toutes les semaines reprises ici ne comptent pas le même nombre "
                "de jours d'ouverture. Comparez dans ce cas le chiffre "
                "d'affaires par jour d'ouverture et non le total hebdomadaire : "
                "une semaine courte n'est pas une mauvaise semaine.",
            ),
        })

    return {
        "rijen": rijen,
        "toelichting": t(
            f"De laatste {WEKEN_TERUG} volledige kalenderweken (maandag t/m "
            f"zondag) die geheel vóór {_dag_label(tot)} liggen. De lopende week "
            "staat er bewust niet bij: een halve week naast een volle week is "
            "geen vergelijking.",
            f"Les {WEKEN_TERUG} dernières semaines calendrier complètes (du "
            f"lundi au dimanche) entièrement antérieures au {_dag_label(tot)}. "
            "La semaine en cours est volontairement absente : une demi-semaine "
            "à côté d'une semaine entière n'est pas une comparaison.",
        ),
    }


def _maandritme(
    dagtotalen: pd.DataFrame, tot: pd.Timestamp, onbeschikbaar: list[dict],
) -> dict | None:
    """Omzet per gemeten open dag per maand, de laatste twaalf.

    Per open dag en niet per maand: een maand met zomersluiting is een korte
    maand, geen slechte maand, en alleen het dagcijfer maakt dat verschil.
    """
    tabel = bk.maandritme(dagtotalen, tot, maanden=MAANDEN_TERUG)
    punten = [
        {"x": _maand_label(int(r.jaar), int(r.maand)),
         "y": round(float(r.omzet_per_dag), 2) if r.omzet_per_dag is not None
         else 0.0,
         "meetdagen": int(r.open_dagen)}
        for r in tabel.itertuples()
    ]
    maximum = max((p["y"] for p in punten), default=0.0)
    if maximum <= 0:
        onbeschikbaar.append({
            "veld": "maandritme",
            "reden": t(
                f"Geen maandritme: in de laatste {MAANDEN_TERUG} maanden t/m "
                f"{_dag_label(tot)} is geen open winkeldag gemeten.",
                f"Pas de rythme mensuel : sur les {MAANDEN_TERUG} derniers mois "
                f"jusqu'au {_dag_label(tot)}, aucun jour d'ouverture n'a été "
                "mesuré.",
            ),
        })
        return None

    stil = [p["x"] for p in punten if p["meetdagen"] == 0]
    if stil:
        onbeschikbaar.append({
            "veld": "maandritme.lege_maanden",
            "reden": t(
                f"Zonder staaf: {', '.join(stil)}. In die maanden is geen open "
                "winkeldag gemeten. Een nulstaaf zou een maand zonder omzet "
                "tonen in plaats van een maand zonder meting.",
                f"Sans barre : {', '.join(stil)}. Aucun jour d'ouverture n'a été "
                "mesuré ces mois-là. Une barre à zéro montrerait un mois sans "
                "chiffre d'affaires au lieu d'un mois sans mesure.",
            ),
        })

    return {
        "grafiek": {
            "reeksen": [{
                "naam": t("Omzet per open dag", "Chiffre d'affaires par jour d'ouverture"),
                "kleur": "bordeaux",
                "punten": punten,
            }],
            "y_as": _euro_as(maximum),
        },
        "toelichting": t(
            f"Omzet per gemeten open dag, per kalendermaand, de laatste "
            f"{MAANDEN_TERUG} t/m {_dag_label(tot)}. Per open dag en niet per "
            "maand: anders is elke vakantiemaand een slechte maand.",
            f"Chiffre d'affaires par jour d'ouverture mesuré, par mois "
            f"calendrier, les {MAANDEN_TERUG} derniers jusqu'au "
            f"{_dag_label(tot)}. Par jour d'ouverture et non par mois : sinon, "
            "tout mois de vacances est un mauvais mois.",
        ),
    }


def _afwijkende_dagen(
    dagtotalen: pd.DataFrame, tot: pd.Timestamp, onbeschikbaar: list[dict],
) -> dict | None:
    """De dagen die hard afwijken van hun eigen weekdag."""
    tabel = bk.afwijkende_dagen(dagtotalen, tot, dagen=AFWIJKING_DAGEN)
    toelichting = t(
        f"Dagen uit de laatste {_dagen_nl(AFWIJKING_DAGEN)} t/m "
        f"{_dag_label(tot)} die sterk afwijken van wat op diezelfde weekdag "
        "gebruikelijk is. Gebruikelijk is de mediaan van die weekdag, en de "
        f"drempel ligt bij een robuuste afwijking van {AFWIJKING_DREMPEL_TEKST} "
        "— hoog genoeg dat een drukke zaterdag er niet elke week bij staat.",
        f"Jours des {_dagen_nl(AFWIJKING_DAGEN)} les plus récents jusqu'au "
        f"{_dag_label(tot)} qui s'écartent fortement de l'habituel pour ce même "
        "jour de la semaine. L'habituel est la médiane de ce jour de la "
        f"semaine, et le seuil est fixé à un écart robuste de "
        f"{AFWIJKING_DREMPEL_TEKST} — assez haut pour qu'un samedi chargé n'y "
        "figure pas chaque semaine.",
    )
    if tabel.empty:
        onbeschikbaar.append({
            "veld": "afwijkende_dagen",
            "reden": t(
                f"Geen opvallende dagen in de laatste {_dagen_nl(AFWIJKING_DAGEN)} "
                f"t/m {_dag_label(tot)}. Dat kan twee dingen betekenen: geen enkele "
                "dag week ver genoeg af, of er zijn te weinig waarnemingen per "
                f"weekdag om dat te kunnen zeggen (minder dan "
                f"{bk.AFWIJKING_MIN_PER_WEEKDAG}). Wat hier niet staat, is dus "
                "niet als normaal verklaard.",
                f"Aucun jour remarquable sur les {_dagen_nl(AFWIJKING_DAGEN)} les "
                f"plus récents jusqu'au {_dag_label(tot)}. Cela peut vouloir dire "
                "deux choses : aucun jour ne s'est suffisamment écarté, ou il y a "
                "trop peu d'observations par jour de la semaine pour l'affirmer "
                f"(moins de {bk.AFWIJKING_MIN_PER_WEEKDAG}). Ce qui ne figure pas "
                "ici n'est donc pas déclaré normal.",
            ),
        })
        return None

    rijen = []
    for r in tabel.itertuples():
        datum = pd.Timestamp(r.datum)
        verschil = float(r.omzet) - float(r.verwacht_mediaan)
        rijen.append({
            "datum": _iso_datum(datum),
            "label": f"{tl.weekdag(datum.dayofweek)} {_dag_label(datum)}",
            "omzet": _s(float(r.omzet)),
            "gebruikelijk": _s(float(r.verwacht_mediaan)),
            "verschil": _s(verschil),
            "richting": _richting(verschil),
        })
    return {"rijen": rijen, "toelichting": toelichting}


def _concentratie(
    open_verkopen: pd.DataFrame, tot: pd.Timestamp, onbeschikbaar: list[dict],
) -> dict | None:
    """Hoe zwaar de omzet op de kop van het assortiment leunt."""
    con = bk.concentratie(open_verkopen, tot, dagen=CONCENTRATIE_DAGEN)
    if con is None:
        onbeschikbaar.append({
            "veld": "concentratie",
            "reden": t(
                f"Geen verdeling over het assortiment: in de laatste "
                f"{_dagen_nl(CONCENTRATIE_DAGEN)} t/m {_dag_label(tot)} is geen "
                "omzet gemeten om te verdelen.",
                f"Pas de répartition sur l'assortiment : sur les "
                f"{_dagen_nl(CONCENTRATIE_DAGEN)} les plus récents jusqu'au "
                f"{_dag_label(tot)}, aucun chiffre d'affaires n'a été mesuré à "
                "répartir.",
            ),
        })
        return None

    def _rij(drempel: str, aantal_producten: int) -> dict:
        return {
            "drempel": drempel,
            "producten": str(aantal_producten),
            # Het kant-en-klare tabelwoord naast de machinewaarde: harde
            # regel 4 geldt ook voor woorden, de UI verzint er geen.
            "label": _producten_nl(aantal_producten),
            "aandeel_assortiment": _pct_machine(
                100.0 * aantal_producten / con.totaal_producten
            ),
        }

    return {
        # De kolomkoppen horen bij de rijen: samen lezen ze als een zin
        # ("de helft van de omzet | komt van | 29 producten | 3,7 % van het
        # assortiment"). Tot 17 augustus 2026 stonden de middelste twee
        # hard in de UI, en dus in het Frans in het Nederlands.
        "kolommen": [
            t("Dit deel van de omzet", "Cette part du chiffre d'affaires"),
            t("komt van", "provient de"),
            t("van het assortiment", "de l'assortiment"),
        ],
        "rijen": [
            _rij(t("de helft van de omzet", "la moitié du chiffre d'affaires"),
                 con.voor_50),
            _rij(t("80 % van de omzet", "80 % du chiffre d'affaires"),
                 con.voor_80),
            _rij(t("95 % van de omzet", "95 % du chiffre d'affaires"),
                 con.voor_95),
        ],
        "totaal_producten": str(con.totaal_producten),
        "staart_omzet": _s(con.staart_omzet),
        "staart_producten": str(con.totaal_producten - con.voor_95),
        "toelichting": t(
            f"Over de laatste {_dagen_nl(con.dagen)} met gemeten verkoop t/m "
            f"{_dag_label(tot)}, geteld per product. De staart is alles buiten "
            "de 95 %-kop: het bedrag waarover een assortimentsdiscussie "
            "werkelijk gaat.",
            f"Sur les {_dagen_nl(con.dagen)} les plus récents avec des ventes "
            f"mesurées jusqu'au {_dag_label(tot)}, compté par produit. La queue, "
            "c'est tout ce qui tombe hors de la tête à 95 % : le montant sur "
            "lequel porte réellement un débat sur l'assortiment.",
        ),
    }


def _prijs_volume(
    open_verkopen: pd.DataFrame, tot: pd.Timestamp, onbeschikbaar: list[dict],
) -> dict | None:
    """Δomzet ontbonden: verkochten we minder, of verkochten we goedkoper?"""
    ont = bk.ontbinding_prijs_volume(open_verkopen, tot, dagen=ONTBINDING_DAGEN)
    if not ont.vergelijkbaar or ont.verschil is None:
        onbeschikbaar.append({
            "veld": "prijs_volume",
            "reden": t(
                f"Geen ontbinding in stuks en prijs: het venster t/m "
                f"{_dag_label(tot)} telt {_dagen_nl(ont.dagen)} met gemeten "
                f"verkoop, de periode ervoor {_dagen_nl(ont.vorig_dagen)}. Bij "
                "ongelijke vensters meet de uitkomst het aantal dagen en niet "
                "het assortiment.",
                f"Pas de décomposition en unités et en prix : la fenêtre "
                f"jusqu'au {_dag_label(tot)} compte {_dagen_nl(ont.dagen)} avec "
                f"des ventes mesurées, la période précédente "
                f"{_dagen_nl(ont.vorig_dagen)}. Avec des fenêtres inégales, le "
                "résultat mesure le nombre de jours et non l'assortiment.",
            ),
        })
        return None

    return _ontbinding(
        verschil=ont.verschil,
        verschil_label=t(
            f"Verandering in omzet over {_dagen_nl(ont.dagen)}",
            f"Variation du chiffre d'affaires sur {_dagen_nl(ont.dagen)}",
        ),
        termen=[
            (t("Meer of minder stuks", "Plus ou moins d'unités"), ont.volume,
             t("Van dezelfde producten gingen er meer of minder over de "
               "toonbank, tegen de oude prijs per stuk.",
               "Des mêmes produits, il s'en est vendu plus ou moins, au prix "
               "unitaire d'avant.")),
            (t("Andere prijs of andere mix", "Autre prix ou autre mix"),
             ont.prijs,
             t("Dezelfde stuks brachten meer of minder op: een prijswijziging, "
               "of een verschuiving naar duurdere of goedkopere producten.",
               "Les mêmes unités ont rapporté plus ou moins : un changement de "
               "prix, ou un glissement vers des produits plus chers ou moins "
               "chers.")),
            (t("Beide tegelijk", "Les deux à la fois"), ont.kruisterm,
             t("Het deel dat pas ontstaat doordat stuks en prijs samen bewegen.",
               "La part qui ne naît que du mouvement simultané des unités et du "
               "prix.")),
            (t("Nieuw in het assortiment", "Nouveau dans l'assortiment"),
             ont.nieuw,
             t("Omzet van producten die in de vorige periode niet verkocht werden.",
               "Chiffre d'affaires de produits qui ne se vendaient pas lors de "
               "la période précédente.")),
            (t("Uit het assortiment", "Sorti de l'assortiment"), -ont.verdwenen,
             t("Omzet van producten die nu niet meer verkocht worden.",
               "Chiffre d'affaires de produits qui ne se vendent plus.")),
        ],
        toelichting=t(
            f"De laatste {_dagen_nl(ont.dagen)} met gemeten verkoop t/m "
            f"{_dag_label(tot)}, naast even veel dagen ervoor. De vijf termen "
            "tellen op de cent op tot de verandering erboven. Let op: dit is het "
            "verschil over de hele periode, niet per dag.",
            f"Les {_dagen_nl(ont.dagen)} les plus récents avec des ventes "
            f"mesurées jusqu'au {_dag_label(tot)}, face à autant de jours "
            "précédents. Les cinq termes s'additionnent au centime près pour "
            "donner la variation ci-dessus. Attention : il s'agit de l'écart sur "
            "toute la période, et non par jour.",
        ),
    )


# --- overzicht --------------------------------------------------------------

# --- de periodekubus ---------------------------------------------------------
#
# Vier voorgebakken vensters achter de periodekiezer op het Dagoverzicht. De
# UI kiest welk blok ze toont en rekent niets (harde regel 4): elke reeks, elke
# as en elke vergelijking staat hier al klaar. Vergelijken gebeurt op het
# gemiddelde per gemeten open dag — dat blijft eerlijk bij vensters met een
# ongelijk aantal open dagen, zolang beide aantallen in het label staan.

PERIODE_WEKEN = 13
PERIODE_MAANDEN = 12
#: Het korte venster naast de 30 dagen. Zeven, omdat de opdrachtgever zijn
#: eigen managementrapporten per week opmaakt en die twee naast elkaar moeten
#: kunnen liggen; het telt gemeten open dagen, zie `_dagenvenster`.
PERIODE_KORT_DAGEN = 7


def _vergelijk_blokken(huidig, vorig, omschrijving: str) -> dict | None:
    """Het verschil in gemiddelde per open dag, of None zonder vorige meting.

    `omschrijving` komt al vertaald binnen: de aanroeper weet welke periode
    hij bedoelt en zet er zelf `t(...)` omheen. Zo hoeft deze functie geen
    twee omschrijvingen te dragen die ze niet kan controleren.
    """
    if huidig.gemiddelde is None or vorig.gemiddelde is None:
        return None
    pct = (huidig.gemiddelde - vorig.gemiddelde) / vorig.gemiddelde * 100
    # Half-up, zoals overal in het platform (tot 18 aug 2026 bankiersafronding).
    pct = pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {
        "label": t(
            f"Gem. per open dag t.o.v. {omschrijving} "
            f"({huidig.open_dagen} om {vorig.open_dagen} open dagen)",
            f"Moy. par jour d'ouverture vs {omschrijving} "
            f"({huidig.open_dagen} contre {vorig.open_dagen} jours d'ouverture)",
        ),
        "waarde": _s(pct),
        "soort": "verschil",
        "richting": _richting(pct),
    }


def _blok_context(blok, beste: dict | None, vergelijking: dict | None) -> list[dict]:
    context = [
        # "{d} d'ouverture" en niet "{d} ouverts": `open dag` heet in dit
        # platform overal `jour d'ouverture`, ook waar de Nederlandse zin
        # korter is.
        {"label": t("Totaal, {d} open", "Total, {d} d'ouverture").format(d=_dagen_nl(blok.open_dagen)),
         "waarde": _s(blok.omzet), "soort": "euro", "richting": None},
    ]
    if blok.gemiddelde is not None:
        context.append({"label": t("Gemiddelde per open dag", "Moyenne par jour d'ouverture"),
                        "waarde": _s(blok.gemiddelde), "soort": "euro",
                        "richting": None})
    if beste is not None:
        context.append(beste)
    if vergelijking is not None:
        context.append(vergelijking)
    return context


def _dagenvenster(
    dagtotalen: pd.DataFrame, tot: pd.Timestamp, dagen: int, sleutel: str,
    *, standaard: bool = False,
) -> dict:
    """Eén venster van de vorm "de laatste N gemeten open dagen", als lijn.

    `dagen` telt gemeten open dagen en géén kalenderdagen (zie
    `berekening._aangrenzende_vensters`). Zeven open dagen zijn bij een zaak
    die zes dagen per week draait ruim een kalenderweek, en na een sluiting
    nog meer. Daarom draagt het knoplabel het gevráágde aantal en de
    toelichting het gevónden aantal: die twee lopen uiteen zodra de historiek
    korter is dan het venster, en dan is het gevonden aantal het eerlijke.

    `standaard` markeert het venster dat de kiezer opent. Dat staat hier en
    niet in de volgorde van de lijst, want de lijst loopt van kort naar lang
    (leesbaar) terwijl het openingsvenster 30 dagen blijft — een week is te
    kort om een dashboard mee te openen, en een stille wissel van dat
    openingsbeeld is precies wat niemand vraagt.
    """
    verloop = bk.omzetverloop(dagtotalen, tot, dagen=dagen)
    punten = [(_dag_label(pd.Timestamp(r.datum)), float(r.omzet))
              for r in verloop.itertuples()]
    ctx = bk.periodecontext(dagtotalen, tot, dagen=dagen)

    context = [
        {"label": t("Totaal, {n} open dagen", "Total, {n} jours d'ouverture").format(n=ctx.dagen),
         "waarde": _s(ctx.totaal), "soort": "euro", "richting": None},
        {"label": t("Gemiddelde per open dag", "Moyenne par jour d'ouverture"),
         "waarde": _s(ctx.gemiddelde), "soort": "euro", "richting": None},
        {"label": t("Beste dag, {d}", "Meilleur jour, {d}").format(d=_dag_label(ctx.beste_datum)),
         "waarde": _s(ctx.beste_omzet), "soort": "euro", "richting": None},
    ]
    # Alleen wanneer het vorige venster evenveel open dagen telt; anders is de
    # vergelijking scheef en laat `periodecontext` het percentage weg.
    if ctx.verschil_pct is not None:
        context.append({
            "label": t("T.o.v. de {n} open dagen ervoor", "Par rapport aux {n} jours d'ouverture précédents").format(n=ctx.vorig_dagen),
            "waarde": _pct_machine(float(ctx.verschil_pct)), "soort": "verschil",
            "richting": ctx.richting,
        })

    venster = {
        "sleutel": sleutel,
        "label": t("{n} dagen", "{n} jours").format(n=dagen),
        "soort": "lijn",
        "grafiek": _lijn(punten,
                         t("Dagomzet", "Chiffre d'affaires journalier"),
                         "bordeaux",
                         max((y for _, y in punten), default=0.0)),
        "context": context,
        "toelichting": t(
            f"De laatste {ctx.dagen} gemeten open winkeldagen t/m "
            f"{_dag_label(tot)}.",
            f"Les {ctx.dagen} derniers jours d'ouverture mesurés jusqu'au "
            f"{_dag_label(tot)}.",
        ),
    }
    if standaard:
        venster["standaard"] = True
    return venster


def _periodes(
    dagtotalen: pd.DataFrame, kalender: pd.DataFrame, tot: pd.Timestamp,
    onbeschikbaar: list[dict],
) -> list[dict]:
    vensters: list[dict] = []

    # Van kort naar lang. Het korte venster staat vooraan omdat de
    # opdrachtgever in weken denkt; 30 dagen blijft het venster dat opent.
    vensters.append(
        _dagenvenster(dagtotalen, tot, PERIODE_KORT_DAGEN, "d7")
    )
    # 30 dagen: dezelfde reeks als het klassieke omzetverloop.
    vensters.append(
        _dagenvenster(dagtotalen, tot, 30, "d30", standaard=True)
    )

    # 13 volledige weken: staaf per week, gat blijft zichtbaar als ontbrekende
    # staaf met de reden in onbeschikbaar.
    weekrijen = bk.weekomzet(dagtotalen, kalender, tot, weken=PERIODE_WEKEN)
    met_omzet = weekrijen[weekrijen["omzet"].notna()]
    zonder = weekrijen[weekrijen["omzet"].isna()]
    if not met_omzet.empty:
        staafpunten = [
            {"x": _dag_label(pd.Timestamp(r.van)), "y": round(float(r.omzet), 2)}
            for r in met_omzet.itertuples()
        ]
        beste_week = met_omzet.loc[met_omzet["omzet"].astype(float).idxmax()]
        huidig = bk.periodeblok(dagtotalen, weekrijen["van"].iloc[0],
                                weekrijen["tot"].iloc[-1])
        vorig = bk.periodeblok(
            dagtotalen,
            weekrijen["van"].iloc[0] - pd.Timedelta(weeks=PERIODE_WEKEN),
            weekrijen["van"].iloc[0] - pd.Timedelta(days=1),
        )
        vensters.append({
            "sleutel": "w13", "label": t("{n} weken", "{n} semaines").format(n=PERIODE_WEKEN), "soort": "staaf",
            "grafiek": {
                "reeksen": [{"naam": t("Weekomzet", "Chiffre d'affaires hebdomadaire"), "kleur": "bordeaux",
                             "punten": staafpunten}],
                "y_as": _euro_as(max(p["y"] for p in staafpunten)),
            },
            "context": _blok_context(
                huidig,
                {"label": t("Beste week, vanaf {d}", "Meilleure semaine, dès le {d}").format(d=_dag_label(pd.Timestamp(beste_week["van"]))),
                 "waarde": _s(beste_week["omzet"]), "soort": "euro",
                 "richting": None},
                _vergelijk_blokken(
                    huidig, vorig,
                    t(f"de {PERIODE_WEKEN} weken ervoor",
                      f"les {PERIODE_WEKEN} semaines précédentes"),
                ),
            ),
            "toelichting": t(
                f"De laatste {PERIODE_WEKEN} volledige kalenderweken (ma t/m zo) "
                f"t/m {_dag_label(pd.Timestamp(weekrijen['tot'].iloc[-1]))}. De "
                "lopende week doet niet mee: een halve week naast een volle is "
                "geen vergelijking.",
                f"Les {PERIODE_WEKEN} dernières semaines calendrier complètes "
                f"(du lu au di) jusqu'au "
                f"{_dag_label(pd.Timestamp(weekrijen['tot'].iloc[-1]))}. La "
                "semaine en cours ne compte pas : une demi-semaine à côté d'une "
                "semaine entière n'est pas une comparaison.",
            ),
        })
        if not zonder.empty:
            labels = ", ".join(
                _dag_label(pd.Timestamp(r.van)) for r in zonder.itertuples()
            )
            onbeschikbaar.append({
                "veld": "periodes.weken_zonder_meting",
                "reden": t(
                    f"Zonder staaf in het wekenvenster: de {len(zonder)} "
                    f"weken vanaf {labels} tellen geen enkele gemeten open dag "
                    "(sluiting of buiten het meetbereik). Een nulstaaf zou een "
                    "ingestorte week tonen die er niet is.",
                    f"Sans barre dans la fenêtre hebdomadaire : les "
                    f"{len(zonder)} semaines à partir du {labels} ne comptent "
                    "aucun jour d'ouverture mesuré (fermeture ou hors période de "
                    "mesure). Une barre à zéro montrerait un effondrement qui "
                    "n'a pas eu lieu.",
                ),
            })
    else:
        onbeschikbaar.append({
            "veld": "periodes.w13",
            "reden": t(
                f"Geen enkele van de laatste {PERIODE_WEKEN} volledige "
                "weken telt een gemeten open dag.",
                f"Aucune des {PERIODE_WEKEN} dernières semaines complètes ne "
                "compte de jour d'ouverture mesuré.",
            ),
        })

    # 12 maanden: staaf per gemeten maand.
    maanden = bk.maandomzet(dagtotalen).tail(PERIODE_MAANDEN)
    if not maanden.empty:
        staafpunten = [
            {"x": _maand_label(int(r.jaar), int(r.maand)),
             "y": round(float(r.omzet), 2)}
            for r in maanden.itertuples()
        ]
        eerste = pd.Timestamp(int(maanden["jaar"].iloc[0]),
                              int(maanden["maand"].iloc[0]), 1)
        huidig = bk.periodeblok(dagtotalen, eerste, tot)
        vorig = bk.periodeblok(dagtotalen,
                               eerste - pd.DateOffset(months=PERIODE_MAANDEN),
                               eerste - pd.Timedelta(days=1))
        beste = maanden.loc[maanden["omzet"].astype(float).idxmax()]
        vensters.append({
            "sleutel": "m12", "label": t("{n} maanden", "{n} mois").format(n=PERIODE_MAANDEN),
            "soort": "staaf",
            "grafiek": {
                "reeksen": [{"naam": t("Maandomzet", "Chiffre d'affaires mensuel"), "kleur": "bordeaux",
                             "punten": staafpunten}],
                "y_as": _euro_as(max(p["y"] for p in staafpunten)),
            },
            "context": _blok_context(
                huidig,
                {"label": t("Beste maand, {m}", "Meilleur mois, {m}").format(
                     m=_maand_label(int(beste["jaar"]), int(beste["maand"]))),
                 "waarde": _s(bk.euro(float(beste["omzet"]))), "soort": "euro",
                 "richting": None},
                _vergelijk_blokken(
                    huidig, vorig,
                    t(f"de {PERIODE_MAANDEN} maanden ervoor",
                      f"les {PERIODE_MAANDEN} mois précédents"),
                ),
            ),
            "toelichting": t(
                f"De laatste {len(maanden)} gemeten maanden t/m "
                f"{_dag_label(tot)}. De jongste maand kan onvolledig zijn; het "
                "gemiddelde per open dag hierboven vangt dat op, de staaf niet.",
                f"Les {len(maanden)} derniers mois mesurés jusqu'au "
                f"{_dag_label(tot)}. Le mois le plus récent peut être incomplet ; "
                "la moyenne par jour d'ouverture ci-dessus en tient compte, la "
                "barre non.",
            ),
        })

    # Jaar tot de peildatum, naast dezelfde periode vorig jaar.
    jaarstart = pd.Timestamp(tot.year, 1, 1)
    huidig = bk.periodeblok(dagtotalen, jaarstart, tot)
    if huidig.open_dagen:
        jaar_maanden = bk.maandomzet(dagtotalen)
        jaar_maanden = jaar_maanden[jaar_maanden["jaar"] == tot.year]
        staafpunten = [
            {"x": _maand_label(int(r.jaar), int(r.maand)),
             "y": round(float(r.omzet), 2)}
            for r in jaar_maanden.itertuples()
        ]
        vorig = bk.periodeblok(dagtotalen,
                               jaarstart - pd.DateOffset(years=1),
                               tot - pd.DateOffset(years=1))
        vensters.append({
            "sleutel": "jaar", "label": t("Dit jaar", "Cette année"), "soort": "staaf",
            "grafiek": {
                "reeksen": [{"naam": t("Maandomzet {j}", "Chiffre d'affaires mensuel {j}").format(j=tot.year),
                             "kleur": "bordeaux", "punten": staafpunten}],
                "y_as": _euro_as(max((p["y"] for p in staafpunten),
                                     default=0.0)),
            },
            "context": _blok_context(
                huidig, None,
                _vergelijk_blokken(
                    huidig, vorig,
                    t(
                        f"1 jan t/m {_dag_label(tot - pd.DateOffset(years=1))} "
                        f"{tot.year - 1}",
                        f"1er janv – "
                        f"{_dag_label(tot - pd.DateOffset(years=1))} "
                        f"{tot.year - 1}",
                    ),
                ),
            ),
            "toelichting": t(
                f"1 januari t/m {_dag_label(tot)} {tot.year}, per maand. De "
                "vergelijking hierboven loopt tegen exact dezelfde periode een "
                "jaar eerder, op het gemiddelde per open dag.",
                f"Du 1er janvier au {_dag_label(tot)} {tot.year}, par mois. La "
                "comparaison ci-dessus porte sur exactement la même période un "
                "an plus tôt, sur la moyenne par jour d'ouverture.",
            ),
        })

    return vensters


def overzicht(
    dagtotalen: pd.DataFrame,
    tot: pd.Timestamp,
    *,
    kalender: pd.DataFrame,
    bonnen: pd.DataFrame | None,
    bron: list[str],
    bijgewerkt_op: datetime,
    gemeten_tot: date | datetime | pd.Timestamp | None,
    prognose_methode: str,
) -> dict:
    """Het overzichtsscherm.

    `kalender` is nodig voor het weekritme: welke dagen in een kalenderweek
    gemeten en open waren, is niet uit de dagtotalen af te leiden — daar staan
    alleen de dagen mét verkoop in, en een week zonder rijen is dan niet te
    onderscheiden van een week die er niet is.

    `bonnen` is de aparte bonnentelling per dag en mag None zijn: die extractie
    is optioneel en het scherm zegt zelf wanneer ze ontbreekt.

    `prognose_methode` is de beschrijving van de baseline die in productie draait.
    Die staat hier omdat de toelichting onder het weekdagprofiel naar de prognose
    verwijst, en die verwijzing moet waar zijn: het profiel gemiddelt over
    kalenderweken, de baseline over de laatste N keer dezelfde weekdag. Twee
    verwante getallen die niet gelijk hoeven te zijn, en dat hoort er te staan.
    """
    kern = bk.kerncijfers(dagtotalen, tot)
    verloop = bk.omzetverloop(dagtotalen, tot, dagen=30)
    maanden = bk.maandomzet(dagtotalen)

    kerncijfers = [
        {
            "label": k.label,
            "waarde": _s(k.waarde),
            "soort": k.soort,
            "verschil": _pct_machine(float(k.verschil_pct)) if k.verschil_pct is not None
            else None,
            "richting": k.richting,
        }
        for k in kern
    ]

    # Een kengetal zonder vergelijking mag niet stilzwijgend zonder pijl staan.
    # Waarom er geen vergelijking is, hoort op het scherm (harde regel 8).
    #
    # De sleutel is `k.sleutel` en niet `k.label`. Dat was tot 19 augustus 2026
    # wél het label, en zolang de labels Nederlands waren viel dat niet op —
    # maar ze zijn tweetalig, en dan heet dezelfde toestand in het Frans anders
    # dan in het Nederlands. Een sleutel die met de taal meebeweegt, is er geen;
    # zie de docstring van `berekening.Kerncijfer`.
    #
    # `k.toelichting` is wél tekst voor een mens en komt uit de
    # berekeningslaag, in de taal van het moment.
    onbeschikbaar: list[dict] = [
        {"veld": f"kerncijfer.{k.sleutel}",
         "reden": t(f"Geen vergelijking met vorig jaar. {k.toelichting}.",
                    f"Pas de comparaison avec l'an dernier. {k.toelichting}.")}
        for k in kern if k.verschil_pct is None
    ]

    punten = [
        (_dag_label(pd.Timestamp(r.datum)), float(r.omzet))
        for r in verloop.itertuples()
    ]
    maximum = max((y for _, y in punten), default=0.0)

    # De regels onder het verloop: totaal, gemiddelde, beste dag, en de
    # vergelijking met de aangrenzende periode. Elk label kant-en-klaar.
    ctx = bk.periodecontext(dagtotalen, tot, dagen=30)
    verloop_context = [
        {"label": t("Totaal, {n} open dagen", "Total, {n} jours d'ouverture").format(n=ctx.dagen), "waarde": _s(ctx.totaal),
         "soort": "euro", "richting": None},
        {"label": t("Gemiddelde per open dag", "Moyenne par jour d'ouverture"), "waarde": _s(ctx.gemiddelde),
         "soort": "euro", "richting": None},
        {"label": t("Beste dag, {d}", "Meilleur jour, {d}").format(d=_dag_label(ctx.beste_datum)),
         "waarde": _s(ctx.beste_omzet), "soort": "euro", "richting": None},
    ]
    if ctx.verschil_pct is not None:
        verloop_context.append({
            "label": t("T.o.v. de {n} open dagen ervoor", "Par rapport aux {n} jours d'ouverture précédents").format(n=ctx.vorig_dagen),
            "waarde": _pct_machine(float(ctx.verschil_pct)), "soort": "verschil",
            "richting": ctx.richting,
        })

    # Het weekdagpatroon dat achter de prognose zit, zichtbaar op het scherm.
    # Elke staaf draagt zijn eigen aantal meetdagen: een gemiddelde over twee
    # zaterdagen is iets anders dan een gemiddelde over acht, en dat verschil
    # hoort bij de staaf te staan en niet in een voetnoot.
    profiel = bk.weekdagprofiel(dagtotalen, tot, weken=PROFIEL_WEKEN)
    profiel_max = float(profiel["gemiddelde"].max()) if not profiel.empty else 0.0
    profielpunten = [
        {"x": tl.weekdag_kort(int(r.weekdag)),
         "y": round(float(r.gemiddelde), 2),
         "meetdagen": int(r.meetdagen)}
        for r in profiel.itertuples()
    ]
    weekdagprofiel = {
        "grafiek": {
            "reeksen": [{
                "naam": t("Gemiddelde dagomzet", "Chiffre d'affaires journalier moyen"),
                "kleur": "bordeaux",
                "punten": profielpunten,
            }],
            "y_as": _euro_as(profiel_max),
        } if profielpunten else None,
        # De oude tekst zei dat de prognose op ditzelfde patroon bouwt. Dat is
        # niet waar: dit gemiddelt over kalenderweken, de baseline over de laatste
        # N keer dezelfde weekdag. Wie het zaterdaggemiddelde naast de
        # zaterdagvoorspelling legt, vindt twee verschillende getallen. De tekst
        # is waar gemaakt in plaats van de baseline te wijzigen — die is door de
        # backtest gekozen en gaat er niet op achteruit voor een bijschrift.
        "toelichting": t(
            f"Gemiddelde omzet per weekdag over de laatste {PROFIEL_WEKEN} "
            f"kalenderweken t/m {_dag_label(tot)}, met per staaf het aantal "
            f"gemeten open dagen. De prognose gebruikt hetzelfde weekdagpatroon "
            f"met een korter venster ({prognose_methode}), dus een staaf hier en "
            f"de voorspelling voor dezelfde weekdag hoeven niet gelijk te zijn.",
            f"Chiffre d'affaires moyen par jour de la semaine sur les "
            f"{PROFIEL_WEKEN} dernières semaines calendrier jusqu'au "
            f"{_dag_label(tot)}, avec pour chaque barre le nombre de jours "
            f"d'ouverture mesurés. La prévision utilise le même profil "
            f"hebdomadaire sur une fenêtre plus courte ({prognose_methode}) ; "
            "une barre ici et la prévision pour ce même jour de la semaine ne "
            "doivent donc pas nécessairement coïncider.",
        ) if profielpunten else "",
    }
    if not profielpunten:
        onbeschikbaar.append({
            "veld": "weekdagprofiel",
            "reden": t(
                f"Geen weekdagpatroon: in de laatste {PROFIEL_WEKEN} kalenderweken "
                f"t/m {_dag_label(tot)} is geen enkele open winkeldag gemeten.",
                f"Pas de profil hebdomadaire : sur les {PROFIEL_WEKEN} dernières "
                f"semaines calendrier jusqu'au {_dag_label(tot)}, aucun jour "
                "d'ouverture n'a été mesuré.",
            ),
        })
    else:
        gemeten_weekdagen = {int(r.weekdag) for r in profiel.itertuples()}
        for wd in range(7):
            if wd in gemeten_weekdagen:
                continue
            naam = tl.weekdag(wd)
            onbeschikbaar.append({
                "veld": f"weekdagprofiel.{naam}",
                "reden": t(
                    f"Geen staaf voor {naam}: in de laatste {PROFIEL_WEKEN} "
                    f"kalenderweken t/m {_dag_label(tot)} is er geen enkele "
                    f"{naam} gemeten waarop de winkel open was. Een nulstaaf zou "
                    "een dag zonder omzet suggereren in plaats van een dag "
                    "zonder meting.",
                    f"Pas de barre pour {naam} : sur les {PROFIEL_WEKEN} "
                    f"dernières semaines calendrier jusqu'au {_dag_label(tot)}, "
                    f"aucun {naam} où la boutique était ouverte n'a été mesuré. "
                    "Une barre à zéro laisserait croire à un jour sans chiffre "
                    "d'affaires plutôt qu'à un jour sans mesure.",
                ),
            })

    # Jaarvergelijking: alleen de maanden die in beide jaren gemeten zijn, want
    # een staaf van drie gemeten dagen naast een staaf van dertig is geen
    # vergelijking. Welke maanden wegvallen, staat in `onbeschikbaar`.
    jaren = sorted(maanden["jaar"].unique())
    if ctx.verschil_pct is None:
        onbeschikbaar.append({
            "veld": "omzetverloop.vergelijking",
            "reden": t(
                f"Geen vergelijking met de periode ervoor: vóór dit venster "
                f"zijn maar {ctx.vorig_dagen} open dagen gemeten, het venster "
                f"zelf telt er {ctx.dagen}.",
                f"Pas de comparaison avec la période précédente : avant cette "
                f"fenêtre, seuls {ctx.vorig_dagen} jours d'ouverture ont été "
                f"mesurés, alors que la fenêtre elle-même en compte "
                f"{ctx.dagen}.",
            ),
        })
    reeksen = []
    if len(jaren) >= 2:
        vorig, huidig = jaren[-2], jaren[-1]
        per_jaar = {
            j: maanden[maanden["jaar"] == j].set_index("maand") for j in (vorig, huidig)
        }
        gedeeld = sorted(set(per_jaar[vorig].index) & set(per_jaar[huidig].index))
        onvolledig = [
            tl.maand_kort(m)
            for m in gedeeld
            if min(per_jaar[vorig].loc[m, "open_dagen"],
                   per_jaar[huidig].loc[m, "open_dagen"]) <
            0.6 * max(per_jaar[vorig].loc[m, "open_dagen"],
                      per_jaar[huidig].loc[m, "open_dagen"])
        ]
        tonen = [m for m in gedeeld if tl.maand_kort(m) not in onvolledig]
        for jaar, kleur in ((vorig, "warmgrijs"), (huidig, "bordeaux")):
            reeksen.append({
                "naam": str(jaar),
                "kleur": kleur,
                "punten": [
                    {"x": tl.maand_kort(m),
                     "y": round(float(per_jaar[jaar].loc[m, "omzet"]), 2)}
                    for m in tonen
                ],
            })
        if onvolledig:
            onbeschikbaar.append({
                "veld": "jaarvergelijking." + ", ".join(onvolledig),
                "reden": t(
                    "Niet getoond: in deze maanden verschilt het aantal gemeten "
                    "open dagen te sterk tussen de twee jaren (sluiting of een "
                    "onvolledig meetvenster). Een staaf naast een staaf zou hier "
                    "een daling tonen die er niet is.",
                    "Non affiché : pour ces mois, le nombre de jours d'ouverture "
                    "mesurés diffère trop fortement entre les deux années "
                    "(fermeture ou période de mesure incomplète). Une barre à "
                    "côté d'une autre montrerait ici une baisse qui n'existe "
                    "pas.",
                ),
            })
    else:
        onbeschikbaar.append({
            "veld": "jaarvergelijking",
            "reden": t(
                "Er is nog maar één jaar gemeten; een jaar-op-jaarvergelijking "
                "bestaat pas vanaf twee.",
                "Une seule année a été mesurée ; une comparaison d'une année à "
                "l'autre n'existe qu'à partir de deux.",
            ),
        })

    max_maand = max(
        (p["y"] for r in reeksen for p in r["punten"]), default=0.0
    )

    return antwoord(
        {
            "kerncijfers": kerncijfers,
            "omzetverloop": _lijn(
                punten, t("Dagomzet", "Chiffre d'affaires journalier"),
                "bordeaux", maximum,
            ),
            "omzetverloop_context": verloop_context,
            # De periodekubus: vier voorgebakken vensters achter de
            # periodekiezer. Het eerste venster (30 dagen) draagt dezelfde
            # cijfers als omzetverloop hierboven; dat veld blijft bestaan voor
            # consumenten die geen kiezer tonen (de PDF, de app van fase 2).
            "periodes": _periodes(dagtotalen, kalender, tot, onbeschikbaar),
            "weekdagprofiel": weekdagprofiel,
            "jaarvergelijking": {"reeksen": reeksen, "y_as": _euro_as(max_maand)},
            # De vier CFO-metrieken die over de zaak als geheel gaan. Elk mag
            # None zijn; de reden staat dan in `onbeschikbaar`.
            "bonritme": _bonritme(bonnen, dagtotalen, tot, onbeschikbaar),
            "weekdagmix": _weekdagmix(dagtotalen, tot, onbeschikbaar),
            "weken": _weken(dagtotalen, kalender, tot, onbeschikbaar),
            "maandritme": _maandritme(dagtotalen, tot, onbeschikbaar),
            "afwijkende_dagen": _afwijkende_dagen(dagtotalen, tot, onbeschikbaar),
        },
        bron=bron,
        bijgewerkt_op=bijgewerkt_op,
        gemeten_tot=gemeten_tot,
        onbeschikbaar=onbeschikbaar,
    )


# --- kanalen ----------------------------------------------------------------

def kanalen(
    dagtotalen: pd.DataFrame,
    tot: pd.Timestamp,
    *,
    bron: list[str],
    bijgewerkt_op: datetime,
    gemeten_tot: date | datetime | pd.Timestamp | None,
    ontbrekend: dict[str, str],
    kanaalkost: pd.DataFrame | None = None,
) -> dict:
    """Alle kanalen naast elkaar. Een kanaal zonder data toont zich als
    onbeschikbaar met reden, en verdwijnt niet uit de rij.

    `kanaalkost` is de maandtabel die de financiële wig zichtbaar maakt: bruto
    (wat de klant betaalde), commissie (wat het platform inhield), netto (wat
    er overbleef). De winkel heeft geen wig; Deliveroo heeft geen data en dus
    ook geen wig — die staat als reden erbij.
    """
    verdeling = bk.kanaalverdeling(dagtotalen, tot, dagen=30).set_index("kanaal")
    financien = {
        f.kanaal: f
        for f in bk.kanaalfinancien(dagtotalen, kanaalkost, tot, dagen=30)
    }
    blokken, onbeschikbaar = [], []

    for kanaal in ("winkel", "deliveroo"):
        if kanaal not in verdeling.index:
            blokken.append({
                "kanaal": kanaal, "naam": tl.kanaalnaam(kanaal),
                "omzet_30d": None, "aandeel": None, "stuks_30d": None,
                "gem_dagomzet": None, "meetdagen": None, "verloop": None,
                "bruto_30d": None, "commissie_30d": None, "netto_30d": None,
                "inhouding_pct": None,
            })
            # Drie verschillende redenen, drie verschillende waarheden: de
            # aanroeper weet waarom een kanaal ontbreekt (Deliveroo), een
            # kanaal mét historiek buiten het venster heeft gewoon niets
            # recents aangeleverd, en pas als geen van beide geldt is er
            # echt niets ingeladen.
            historiek = dagtotalen[dagtotalen["kanaal"] == kanaal]
            if kanaal in ontbrekend:
                reden = ontbrekend[kanaal]
            elif not historiek.empty:
                laatste = pd.Timestamp(historiek["datum"].max())
                reden = t(
                    f"Geen metingen in de laatste 30 dagen. De data van dit "
                    f"kanaal loopt tot en met {_datum_nl(laatste)}; sindsdien "
                    f"is er niets meer aangeleverd.",
                    f"Aucune mesure sur les 30 derniers jours. Les données de "
                    f"ce canal s'arrêtent au {_datum_nl(laatste)} ; rien n'a "
                    f"été fourni depuis.",
                )
            else:
                reden = t("Geen data ingeladen voor dit kanaal",
                          "Aucune donnée chargée pour ce canal")
            onbeschikbaar.append({"veld": f"kanaal.{kanaal}", "reden": reden})
            continue

        fin = financien.get(kanaal)
        met_commissie = kanaal in canoniek.KANALEN_MET_COMMISSIE
        heeft_wig = fin is not None and (not met_commissie or fin.commissie > 0)
        if met_commissie and not heeft_wig:
            reden_kost = t(
                f"Geen kanaalkosttabel voor {kanaal}: de commissie is voor "
                "dit venster niet te berekenen. Dit kanaal houdt wél een "
                "commissie in, dus € 0 tonen zou de wig verzwijgen en een "
                "verkeerd nettobeeld geven.",
                f"Aucune table de coûts pour {kanaal} : la commission n'est "
                "pas calculable pour cette fenêtre. Ce canal applique bien "
                "une commission ; afficher 0 € masquerait la ponction et "
                "donnerait une image nette erronée.",
            )
            onbeschikbaar.append({
                "veld": f"kanaal.{kanaal}.kost",
                "reden": reden_kost,
            })

        rij = verdeling.loc[kanaal]
        van = tot - pd.Timedelta(days=29)
        reeks = dagtotalen[
            (dagtotalen["kanaal"] == kanaal)
            & (dagtotalen["datum"] >= van)
            & (dagtotalen["datum"] <= tot)
        ].sort_values("datum")
        punten = [
            (_dag_label(pd.Timestamp(r.datum)), float(r.omzet))
            for r in reeks.itertuples()
        ]
        blokken.append({
            "kanaal": kanaal,
            "naam": tl.kanaalnaam(kanaal),
            "omzet_30d": _s(float(rij["omzet"])),
            "aandeel": _pct_machine(float(rij["aandeel_pct"])),
            "stuks_30d": _aantal(float(rij["stuks"])),
            # Gemiddelde per gemeten dag van dít kanaal: Deliveroo meet ook op
            # dagen dat de winkel dicht is, dus elk kanaal zijn eigen noemer.
            "gem_dagomzet": _s(float(rij["omzet"]) / int(rij["dagen"])),
            "meetdagen": str(int(rij["dagen"])),
            "verloop": _lijn(
                punten, tl.kanaalnaam(kanaal), "bordeaux",
                max((y for _, y in punten), default=0.0),
            ) if punten else None,
            "bruto_30d": _s(fin.bruto) if heeft_wig else None,
            "commissie_30d": _s(fin.commissie) if heeft_wig else None,
            "netto_30d": _s(fin.netto) if heeft_wig else None,
            "inhouding_pct": _s(fin.inhouding_pct)
            if heeft_wig and fin.inhouding_pct is not None else None,
        })

    return antwoord({"kanalen": blokken}, bron=bron, bijgewerkt_op=bijgewerkt_op,
                    gemeten_tot=gemeten_tot, onbeschikbaar=onbeschikbaar)


# --- producten --------------------------------------------------------------

def producten(
    open_verkopen: pd.DataFrame,
    groepen: pd.Series,
    tot: pd.Timestamp,
    *,
    bron: list[str],
    bijgewerkt_op: datetime,
    gemeten_tot: date | datetime | pd.Timestamp | None,
) -> dict:
    top = bk.topproducten(open_verkopen, tot, dagen=30, aantal=15)
    per_groep = bk.omzet_per_groep(open_verkopen, groepen, tot, dagen=30)

    rijen = [
        {
            "naam": str(r.product_naam) if pd.notna(r.product_naam)
            else t(f"Product {r.product_id}", f"Produit {r.product_id}"),
            "groep": str(groepen.get(str(r.product_id), "Overige")),
            "stuks": _aantal(r.stuks),
            "omzet": _s(float(r.omzet)),
            "aandeel": _pct_machine(float(r.aandeel_pct)),
        }
        for r in top.itertuples()
    ]

    maximum = float(per_groep["omzet"].max()) if not per_groep.empty else 0.0
    staaf = {
        "reeksen": [{
            "naam": t("Omzet 30 dagen", "Chiffre d'affaires 30 jours"),
            "kleur": "bordeaux",
            "punten": [
                {"x": str(r.groep), "y": round(float(r.omzet), 2)}
                for r in per_groep.head(8).itertuples()
            ],
        }],
        "y_as": _euro_as(maximum),
    }

    # Wat beweegt er: de grootste verschuivingen in euro's tegenover de
    # dertig dagen ervoor. Euro's en niet procenten, want een product dat van
    # € 10 naar € 30 gaat is geen groter nieuws dan een brood dat € 400 verliest.
    schuif = bk.productverschuiving(open_verkopen, tot, dagen=30)

    def _schuifrij(r) -> dict:
        return {
            "naam": str(r.product_naam) if pd.notna(r.product_naam)
            else t(f"Product {r.product_id}", f"Produit {r.product_id}"),
            "omzet_nu": _s(float(r.omzet_nu)),
            "omzet_vorig": _s(float(r.omzet_vorig)),
            "verschil": _s(float(r.verschil)),
            "verschil_pct": _pct_machine(float(r.verschil_pct))
            if r.verschil_pct is not None else None,
            "nieuw": bool(r.nieuw),
        }

    # De berekeningslaag weigert de vergelijking als de twee vensters niet
    # evenveel gemeten open dagen tellen — dan zou een sluiting op het scherm
    # verschijnen als vraaguitval. Die weigering is hier een reden met beide
    # aantallen erin; een lege tabel zonder uitleg is precies wat harde regel 8
    # verbiedt.
    onbeschikbaar: list[dict] = []
    if not schuif.vergelijkbaar:
        stijgers, dalers = [], []
        onbeschikbaar.append({
            "veld": "verschuiving",
            "reden": t(
                f"Geen vergelijking met de periode ervoor: het venster t/m "
                f"{_dag_label(tot)} telt {_dagen_nl(schuif.dagen)} met gemeten "
                f"verkoop, de periode ervoor {_dagen_nl(schuif.vorig_dagen)}. Bij "
                "ongelijke vensters stijgt op papier bijna elk product en staan er "
                "dalers in de tabel die niet gedaald zijn; dat is een sluiting die "
                "zich voordoet als vraaguitval.",
                f"Pas de comparaison avec la période précédente : la fenêtre "
                f"jusqu'au {_dag_label(tot)} compte {_dagen_nl(schuif.dagen)} "
                f"avec des ventes mesurées, la période précédente "
                f"{_dagen_nl(schuif.vorig_dagen)}. Avec des fenêtres inégales, "
                "presque tous les produits progressent sur le papier et le "
                "tableau affiche des baisses qui n'en sont pas ; c'est une "
                "fermeture qui se fait passer pour une chute de la demande.",
            ),
        })
    else:
        rijen_schuif = schuif.rijen
        stijgers = [_schuifrij(r) for r in rijen_schuif[rijen_schuif["verschil"] > 0]
                    .head(5).itertuples()]
        dalers = [_schuifrij(r) for r in rijen_schuif[rijen_schuif["verschil"] < 0]
                  .tail(5).iloc[::-1].itertuples()]
        if not stijgers and not dalers:
            onbeschikbaar.append({
                "veld": "verschuiving",
                "reden": t(
                    f"Niets om te tonen: tussen de laatste "
                    f"{_dagen_nl(schuif.dagen)} met gemeten verkoop t/m "
                    f"{_dag_label(tot)} en de {_dagen_nl(schuif.vorig_dagen)} "
                    "ervoor is geen enkel product van omzet veranderd.",
                    f"Rien à afficher : entre les {_dagen_nl(schuif.dagen)} les "
                    f"plus récents avec des ventes mesurées jusqu'au "
                    f"{_dag_label(tot)} et les "
                    f"{_dagen_nl(schuif.vorig_dagen)} précédents, aucun produit "
                    "n'a changé de chiffre d'affaires.",
                ),
            })

    verschuiving = {
        "stijgers": stijgers,
        "dalers": dalers,
        "toelichting": t(
            f"De laatste {_dagen_nl(schuif.dagen)} met gemeten verkoop t/m "
            f"{_dag_label(tot)}, naast even veel dagen ervoor. Gerangschikt op "
            "het verschil in euro's.",
            f"Les {_dagen_nl(schuif.dagen)} les plus récents avec des ventes "
            f"mesurées jusqu'au {_dag_label(tot)}, face à autant de jours "
            "précédents. Classés sur l'écart en euros.",
        ) if schuif.vergelijkbaar else "",
    }

    # De drill-down: per groep de dragende producten, met een rest-regel in
    # plaats van een afgekapte lijst — twaalf producten stil weglaten zou de
    # groepsomzet op het scherm niet meer laten kloppen met de staaf erboven.
    TOP_PER_GROEP = 8
    detail = bk.groepen_detail(open_verkopen, groepen, tot, dagen=30)
    totaal_omzet = float(per_groep["omzet"].sum()) if not per_groep.empty else 0.0
    groepen_detail = []
    for groep, rijen_groep in detail.groupby("groep", sort=False):
        groepsomzet = float(rijen_groep["omzet"].sum())
        kop = rijen_groep.head(TOP_PER_GROEP)
        rest = rijen_groep.iloc[TOP_PER_GROEP:]
        groepen_detail.append({
            "groep": str(groep),
            "omzet_30d": _s(groepsomzet),
            "aandeel": _pct_machine(100.0 * groepsomzet / totaal_omzet)
            if totaal_omzet else None,
            "producten": [
                {
                    "naam": str(r.product_naam) if pd.notna(r.product_naam)
                    else t(f"Product {r.product_id}", f"Produit {r.product_id}"),
                    "stuks": _aantal(r.stuks),
                    "omzet": _s(float(r.omzet)),
                    "aandeel_in_groep": _pct_machine(float(r.aandeel_in_groep_pct)),
                }
                for r in kop.itertuples()
            ],
            "rest": {
                "label": _rest_label(len(rest)),
                "producten": str(len(rest)),
                "omzet_30d": _s(float(rest["omzet"].sum())),
            } if len(rest) else None,
        })

    return antwoord({"top": rijen, "groepen": staaf,
                     "groepen_detail": groepen_detail,
                     "verschuiving": verschuiving,
                     # De twee metrieken die over het assortiment gaan: waar de
                     # omzet op leunt, en of een verandering uit stuks of uit
                     # prijs komt. Ze staan hier en niet op het overzicht omdat
                     # ze allebei per product gerekend worden.
                     "concentratie": _concentratie(open_verkopen, tot,
                                                   onbeschikbaar),
                     "prijs_volume": _prijs_volume(open_verkopen, tot,
                                                   onbeschikbaar)},
                    bron=bron, bijgewerkt_op=bijgewerkt_op,
                    gemeten_tot=gemeten_tot, onbeschikbaar=onbeschikbaar)


# --- marge ------------------------------------------------------------------

MARGE_REDEN = (
    "Geblokkeerd op ontbrekende kostprijzen. Odoo berekende de kostprijs op alle "
    "1.556.770 kassabonregels en kwam 1.556.054 keer uit op nul; er is dus geen "
    "kostprijsinformatie in het bronsysteem. Zodra de bakkerij een brutomarge per "
    "productgroep aanlevert, vult dit scherm zich (vraag 19)."
)

MARGE_INVOER_REDEN = (
    "Nog geen kosten ingevuld. Een beheerder vult per productgroep de "
    "kostencriteria in op Instellingen (grondstoffen, verlies, wat de zaak "
    "zelf relevant vindt); de brutomarge is dan omzet min die kosten en dit "
    "scherm vult zich vanzelf. Het platform kan de marge niet zelf berekenen: "
    "Odoo berekende de kostprijs op alle 1.556.770 kassabonregels en kwam "
    "1.556.054 keer uit op nul (vraag 19)."
)

MARGE_REDEN_FR = (
    "Bloqué faute de prix de revient. Odoo a calculé le prix de revient sur "
    "les 1.556.770 lignes de tickets de caisse et a obtenu zéro 1.556.054 "
    "fois ; il n'y a donc aucune information de coût dans le système source. "
    "Dès que la boulangerie fournira une marge brute par groupe de produits, "
    "cet écran se remplira (question 19)."
)

MARGE_INVOER_REDEN_FR = (
    "Aucun coût n'a encore été saisi. Un administrateur renseigne par groupe "
    "de produits les critères de coûts dans Paramètres (matières premières, "
    "pertes, ce que la maison juge pertinent) ; la marge brute est alors le "
    "chiffre d'affaires moins ces coûts, et cet écran se remplit de lui-même. "
    "La plateforme ne peut pas calculer la marge elle-même : Odoo a calculé le "
    "prix de revient sur les 1.556.770 lignes de tickets de caisse et a obtenu "
    "zéro 1.556.054 fois (question 19)."
)


def marge(
    open_verkopen: pd.DataFrame | None = None,
    groepen: pd.Series | None = None,
    invoer: object | None = None,
    tot: pd.Timestamp | None = None,
    *,
    bron: list[str],
    bijgewerkt_op: datetime,
    gemeten_tot: date | datetime | pd.Timestamp | None,
    invoer_fout: str | None = None,
) -> dict:
    """Het margescherm: leeg met reden zolang niemand marges invult, gevuld
    zodra een beheerder dat doet.

    Het antwoord draagt áltijd de groepenlijst met omzet en aandeel — ook
    zonder invoer. Zo weet het invoerformulier op Instellingen welke groepen
    er werkelijk zijn (en hoeveel omzet erachter zit) zonder zelf te rekenen,
    en verschijnt er nooit een marge voor een groep die niet bestaat.

    `invoer` is een `bakkerij.kostenmodel.Kostenmodel` of None. `invoer_fout`
    is de reden waarom een aanwezig invoerbestand genegeerd wordt; die hoort op
    het scherm, want een marge die stil verdwijnt is erger dan geen marge.

    Het antwoord draagt ook altijd `criteria`: het menu van kostencriteria dat
    de beheerder zelf samenstelt. Zonder invoer zijn dat suggesties
    (`criteria_bron: "suggestie"`), zodat het formulier ergens mee kan
    beginnen zonder dat er ook maar één cijfer verzonnen is.
    """
    if open_verkopen is None or groepen is None or tot is None:
        return antwoord({}, bron=bron, bijgewerkt_op=bijgewerkt_op,
                        gemeten_tot=gemeten_tot, onbeschikbaar=[
            {"veld": "marge_per_kanaal",
             "reden": t(MARGE_REDEN, MARGE_REDEN_FR)},
            {"veld": "marge_per_groep",
             "reden": t(MARGE_REDEN, MARGE_REDEN_FR)},
        ])

    model_criteria = tuple(getattr(invoer, "criteria", ()) or ())
    kosten = dict(getattr(invoer, "waarden", {}) or {})
    if model_criteria:
        criteria = [{"naam": c.naam, "omschrijving": c.omschrijving}
                    for c in model_criteria]
        criteria_bron = "ingevuld"
    else:
        criteria = [{"naam": c.naam, "omschrijving": c.omschrijving}
                    for c in km.standaard_criteria()]
        criteria_bron = "suggestie"
    volgorde = tuple(c["naam"] for c in criteria)
    beeld = bk.marge_per_groep(open_verkopen, groepen, kosten, tot,
                               criteria_volgorde=volgorde, dagen=30)

    onbeschikbaar: list[dict] = []
    if invoer_fout:
        onbeschikbaar.append({
            "veld": "marge.invoer",
            "reden": t(f"Het margebestand wordt genegeerd: {invoer_fout}",
                       f"Le fichier des marges est ignoré : {invoer_fout}"),
        })

    if beeld is None:
        onbeschikbaar.append({
            "veld": "marge_per_groep",
            "reden": t(
                "Geen winkelomzet gemeten in de laatste 30 dagen; er is "
                "niets om een marge op te berekenen.",
                "Aucun chiffre d'affaires magasin mesuré sur les 30 derniers "
                "jours ; il n'y a rien sur quoi calculer une marge.",
            ),
        })
        return antwoord({}, bron=bron, bijgewerkt_op=bijgewerkt_op,
                        gemeten_tot=gemeten_tot, onbeschikbaar=onbeschikbaar)

    rijen = [
        {
            "groep": str(r.groep),
            "omzet_30d": _s(float(r.omzet)),
            "aandeel": _pct_machine(float(r.aandeel_pct)),
            "marge_pct": _s(r.marge_pct) if r.marge_pct is not None else None,
            "marge_30d": _s(r.marge_eur) if r.marge_eur is not None else None,
            # De opbouw achter het percentage: welk criterium hoeveel wegneemt.
            "kosten": [{"criterium": p["criterium"], "pct": _s(p["pct"]),
                        "kost_30d": _s(p["eur"])} for p in r.opbouw],
        }
        for r in beeld.rijen.itertuples()
    ]

    kern = None
    staaf = None
    if beeld.gewogen_pct is not None:
        kern = {
            "gewogen_pct": _s(beeld.gewogen_pct),
            "marge_30d": _s(beeld.marge_eur),
            "gedekte_omzet_30d": _s(beeld.gedekte_omzet),
            "dekking_pct": _s(beeld.dekking_pct),
            "meetdagen": beeld.dagen,
            "toelichting": t(
                f"Brutomarge op de winkelomzet van de laatste 30 kalenderdagen "
                f"t/m {_datum_nl(tot)} ({_dagen_nl(beeld.dagen)} met gemeten "
                f"verkoop). Gewogen over de groepen met een ingevulde marge: "
                f"{_pct_tekst(float(beeld.dekking_pct) / 100)} van de omzet.",
                f"Marge brute sur le chiffre d'affaires magasin des 30 derniers "
                f"jours calendrier jusqu'au {_datum_nl(tot)} "
                f"({_dagen_nl(beeld.dagen)} avec des ventes mesurées). Pondérée "
                f"sur les groupes dont la marge est renseignée : "
                f"{_pct_tekst(float(beeld.dekking_pct) / 100)} du chiffre "
                "d'affaires.",
            ),
        }
        gevuld = beeld.rijen[beeld.rijen["marge_eur"].notna()]
        maximum = max((float(m) for m in gevuld["marge_eur"]), default=0.0)
        staaf = {
            "reeksen": [{
                "naam": t("Brutomarge 30 dagen", "Marge brute 30 jours"),
                "kleur": "bordeaux",
                "punten": [
                    {"x": str(r.groep), "y": round(float(r.marge_eur), 2)}
                    for r in gevuld.head(10).itertuples()
                ],
            }],
            "y_as": _euro_as(maximum),
        }

        ontbrekend = beeld.rijen[beeld.rijen["marge_pct"].isna()]
        if not ontbrekend.empty:
            namen = ", ".join(str(g) for g in ontbrekend["groep"].head(8))
            aandeel = float(ontbrekend["omzet"].sum()) / float(beeld.totale_omzet)
            onbeschikbaar.append({
                "veld": "marge.ontbrekende_groepen",
                "reden": t(
                    f"Zonder ingevulde kosten, en dus buiten het gewogen cijfer: "
                    f"{namen} — samen {_pct_tekst(aandeel)} van de winkelomzet. "
                    "In te vullen op Instellingen.",
                    f"Sans coûts renseignés, et donc hors du chiffre pondéré : "
                    f"{namen} — ensemble {_pct_tekst(aandeel)} du chiffre "
                    "d'affaires magasin. À renseigner dans Paramètres.",
                ),
            })

        # Kosten boven de 100% zijn wiskundig toegestaan (een groep kán met
        # verlies verkopen) maar vrijwel zeker een tikfout; dat mag niet stil
        # in een gewogen gemiddelde verdwijnen.
        negatief = beeld.rijen[beeld.rijen["marge_pct"].map(
            lambda m: m is not None and m < 0)]
        if not negatief.empty:
            namen = ", ".join(str(g) for g in negatief["groep"].head(8))
            onbeschikbaar.append({
                "veld": "marge.negatief",
                "reden": t(
                    f"Bij {namen} tellen de ingevulde kosten op tot meer dan "
                    "100 % van de omzet; de brutomarge is daar negatief. Dat "
                    "wordt getoond zoals het is ingevuld — controleer de "
                    "invoer op Instellingen.",
                    f"Pour {namen}, les coûts renseignés dépassent 100 % du "
                    "chiffre d'affaires ; la marge brute y est négative. C'est "
                    "affiché tel que saisi — vérifiez la saisie dans "
                    "Paramètres.",
                ),
            })
    else:
        onbeschikbaar.append({
            "veld": "marge_per_groep",
            "reden": t(MARGE_INVOER_REDEN, MARGE_INVOER_REDEN_FR),
        })

    onbeschikbaar.append({
        "veld": "marge.deliveroo",
        "reden": t(
            "Geen Deliveroo-data ingeladen; zodra het kanaal er is, telt "
            "het hier mee met zijn eigen commissie.",
            "Aucune donnée Deliveroo chargée ; dès que le canal existera, il "
            "comptera ici avec sa propre commission.",
        ),
    })

    # De kostenopbouw: van gedekte omzet via elk criterium naar brutomarge.
    # De identiteit klopt op de cent (gedekte omzet - som kosten = marge),
    # omdat de berekeningslaag per kostregel afrondt en nergens twee keer.
    kostenopbouw = None
    if kern is not None and not beeld.per_criterium.empty:
        kostenopbouw = {
            "omzet_30d": _s(beeld.gedekte_omzet),
            "kosten_30d": _s(beeld.gedekte_omzet - beeld.marge_eur),
            "marge_30d": _s(beeld.marge_eur),
            "per_criterium": [
                {
                    "criterium": str(r.criterium),
                    "kost_30d": _s(r.kost_eur),
                    # Half-up, zoals overal (tot 18 aug 2026 bankiersafronding).
                    "pct_gewogen": _s((r.kost_eur / r.omzet_basis * 100)
                                      .quantize(Decimal("0.1"),
                                                rounding=ROUND_HALF_UP)),
                    "groepen_n": int(r.groepen_n),
                }
                for r in beeld.per_criterium.itertuples()
            ],
            "toelichting": t(
                "Gedekte winkelomzet min de ingevulde kostencriteria is de "
                "brutomarge. Het percentage per criterium weegt alleen over "
                "de omzet van de groepen waar dat criterium is ingevuld.",
                "Le chiffre d'affaires magasin couvert, moins les critères de "
                "coûts renseignés, donne la marge brute. Le pourcentage par "
                "critère ne se pondère que sur le chiffre d'affaires des "
                "groupes où ce critère est renseigné.",
            ),
        }

    return antwoord({"kern": kern, "per_groep": rijen, "staaf": staaf,
                     "criteria": criteria, "criteria_bron": criteria_bron,
                     "kostenopbouw": kostenopbouw},
                    bron=bron, bijgewerkt_op=bijgewerkt_op,
                    gemeten_tot=gemeten_tot, onbeschikbaar=onbeschikbaar)


# --- stand ------------------------------------------------------------------

def stand(kwaliteit: dict, *, bron: list[str], bijgewerkt_op: datetime,
          gemeten_tot: date | datetime | pd.Timestamp | None) -> dict:
    """Het zesde antwoord: leeft het platform, en mag je de cijfers geloven?

    `kwaliteit` komt uit bakkerij.kwaliteit.stand() en is daar al
    geserialiseerd (ISO-datums, dicts). Dit antwoord hoort bij geen enkel
    scherm en bij alle zes: de instellingenpagina toont het voluit, en de
    voettekst van elk scherm draagt de ergste uitkomst.
    """
    return antwoord(kwaliteit, bron=bron, bijgewerkt_op=bijgewerkt_op,
                    gemeten_tot=gemeten_tot)


# --- sluitingsdagen (het beheerscherm van de sluitingskalender) -----------


def sluitingsdagen(*, vandaag: date, sluitingsdekking: date | None,
                    bron: list[str], bijgewerkt_op: datetime,
                    gemeten_tot) -> dict:
    """De kandidatenlijst voor het scherm Sluitingsdagen.

    Het scherm is geen leeg invoerformulier maar een bevestigingslijst: het
    platform kent de Belgische feestdagen al (de `holidays`-bibliotheek,
    onbeperkt vooruit), dus het scherm toont twaalf maanden en vraagt per dag
    alleen open of dicht. Dit antwoord draagt die kandidaten, in de taal van
    het contract, met de datumtekst al opgemaakt — de UI rekent en vertaalt
    niet (harde regel 4).

    Wat dit antwoord NIET draagt: de uitspraken zelf. Die leest het scherm
    rechtstreeks uit de database (zoals de synchronisatiestand), omdat een
    beheerder die net iets bevestigd heeft zijn eigen invoer meteen terug
    moet zien — dit contract wordt nachtelijk herbouwd en zou tot de volgende
    ochtend de oude stand tonen. De kandidaten zelf verschuiven maar één keer
    per dag, en daarvoor is de nachtelijke herbouw precies goed.
    """
    kandidaten = sk.feestdagkandidaten(vandaag, maanden=12,
                                       taal=tl.huidige_taal())
    data = {
        "kandidaten": [
            {
                "datum": dag.isoformat(),
                "datum_tekst": f"{tl.weekdag_kort(dag.weekday())} "
                               f"{_datum_nl(dag)}",
                "naam": naam,
            }
            for dag, naam in kandidaten
        ],
        # Tot waar de oude bestandslijst reikt. Het scherm zegt daarmee
        # eerlijk wat er al vastligt zonder dat iemand het bevestigd heeft.
        "bestandsdekking_tot": (sluitingsdekking.isoformat()
                                if sluitingsdekking is not None else None),
        "bestandsdekking_tekst": (_datum_nl(sluitingsdekking)
                                  if sluitingsdekking is not None else ""),
    }
    return antwoord(data, bron=bron, bijgewerkt_op=bijgewerkt_op,
                    gemeten_tot=gemeten_tot)


# --- prognose ------------------------------------------------------------

KALENDER_REDEN = (
    "Van de dagen in dit venster is niet bekend of de winkel open is. Dagen die in "
    "de kalender staan als gemeten én gesloten, vallen uit de prognose — daar valt "
    "niets te voorspellen. Maar voorbij het gemeten bereik kent het platform geen "
    "geplande sluitingen, en voor die dagen neemt de prognose aan dat de winkel "
    "open is. Die aanname verdwijnt per dag zodra een beheerder de dag bevestigt "
    "op het scherm Sluitingsdagen."
)

KALENDER_REDEN_FR = (
    "Pour les jours de cette fenêtre, on ne sait pas si la boutique est "
    "ouverte. Les jours inscrits au calendrier comme mesurés et fermés sortent "
    "de la prévision — il n'y a rien à y prévoir. Mais au-delà de la période "
    "mesurée, la plateforme ne connaît aucune fermeture planifiée, et pour ces "
    "jours la prévision suppose que la boutique est ouverte. Cette hypothèse "
    "disparaît jour par jour dès qu'un administrateur confirme le jour sur "
    "l'écran Jours de fermeture."
)


def _kalenderreden(sluitingsdekking: date | None,
                   onbekend: tuple[date, ...] | None) -> str:
    """De aannametekst over sluitingen, afgestemd op wat er werkelijk bekend is.

    Sinds 14 augustus 2026 bestaat er een sluitingslijst, en sinds de
    sluitingskalender (19 augustus) bestaan er ook uitspraken per dag:
    bevestigd dicht, bevestigd open, of onbeantwoord. Het voorbehoud geldt
    daarom niet meer over het hele venster maar per dag — het wordt preciezer
    naarmate er meer bevestigd is, en het blijft eerlijk zolang er iets
    ontbreekt. Drie gevallen, drie teksten:

      geen enkele bron       -> onbekend is None: de oude tekst
      onbeantwoorde dagen    -> die dagen bij naam, met de handeling erbij
      alles beantwoord       -> het voorbehoud is weg, en dat mag gezegd worden

    De handeling is sinds 19 augustus een scherm en geen JSON-bestand meer:
    "vul de sluitingslijst aan" vroeg een CFO om een bestand in een
    git-repository te bewerken, en dat is geen handeling maar een doodlopende
    gang.
    """
    if onbekend is None:
        return t(KALENDER_REDEN, KALENDER_REDEN_FR)

    basis = (
        "Dagen die gemeten én gesloten zijn, en dagen die vooraf als gesloten "
        "zijn aangekondigd, vallen uit de prognose — daar valt niets te "
        "voorspellen."
    )
    basis_fr = (
        "Les jours mesurés et fermés, ainsi que les jours annoncés comme "
        "fermés à l'avance, sortent de la prévision — il n'y a rien à y "
        "prévoir."
    )
    if onbekend:
        if len(onbekend) <= 3:
            lijst = ", ".join(_datum_nl(d) for d in onbekend)
            deel = f"Voor {lijst}"
            deel_fr = (f"Pour le {', le '.join(_datum_nl(d) for d in onbekend)}"
                       if len(onbekend) > 1
                       else f"Pour le {_datum_nl(onbekend[0])}")
        else:
            deel = (f"Voor {_dagen_nl(len(onbekend))} in dit venster "
                    f"({_datum_nl(onbekend[0])} t/m "
                    f"{_datum_nl(onbekend[-1])})")
            deel_fr = (f"Pour {_dagen_nl(len(onbekend))} de cette fenêtre "
                       f"(du {_datum_nl(onbekend[0])} au "
                       f"{_datum_nl(onbekend[-1])})")
        return t(
            f"{basis} {deel} is geen sluiting bekend en geen bevestiging, en "
            "daar neemt de prognose aan dat de winkel open is. Dat is een "
            "aanname en geen meting: een beheerder bevestigt die dagen op het "
            "scherm Sluitingsdagen — open of dicht, allebei zijn een antwoord "
            "— en de prognose volgt.",
            f"{basis_fr} {deel_fr}, aucune fermeture n'est connue et rien "
            "n'est confirmé ; la prévision suppose alors que la boutique est "
            "ouverte. C'est une hypothèse et non une mesure : un "
            "administrateur confirme ces jours sur l'écran Jours de fermeture "
            "— ouvert ou fermé, les deux sont une réponse — et la prévision "
            "suivra.",
        )
    # Alles beantwoord. Bewust GEEN dekkingsclaim die verder gaat dan de
    # bronnen kunnen waarmaken (de les van 15 augustus 2026): een dag binnen
    # het bereik van de bestandslijst waar niets over ingevuld is, is geen
    # bevestiging maar een dag waarover de lijst zwijgt. Alleen de uitspraken
    # per dag zijn bevestigingen; het bereik van de lijst is een bereik.
    dekking = (
        t(f" of hij valt binnen het bereik van de sluitingslijst "
          f"(tot {_datum_nl(sluitingsdekking)}) — en wat daar niet als "
          "sluiting in staat, is geen bevestiging maar een dag waarover de "
          "lijst zwijgt",
          f" ou il tombe dans la portée de la liste des fermetures "
          f"(jusqu'au {_datum_nl(sluitingsdekking)}) — et ce qui n'y figure "
          "pas n'est pas une confirmation, mais un jour sur lequel la liste "
          "reste muette")
        if sluitingsdekking is not None else ""
    )
    return t(
        f"{basis} Voor elke overige dag in dit venster is er een antwoord: "
        f"hij is op het scherm Sluitingsdagen bevestigd{dekking}.",
        f"{basis_fr} Pour chaque autre jour de cette fenêtre, il existe une "
        f"réponse : il est confirmé sur l'écran Jours de fermeture{dekking}.",
    )

BANDREDEN = (
    "Om het weektotaal staat geen bandbreedte. De banden per dag komen uit "
    "dagfouten, en fouten van opeenvolgende dagen hangen samen: ze zomaar "
    "optellen zou een band tonen die de backtest nooit gemeten heeft."
)

BANDREDEN_FR = (
    "Le total hebdomadaire ne porte pas d'intervalle. Les intervalles "
    "journaliers proviennent des erreurs journalières, et les erreurs de jours "
    "qui se suivent sont liées : les additionner sans plus afficherait un "
    "intervalle que le backtest n'a jamais mesuré."
)


def _banduitspraak(laagste: float, hoogste: float, doel: float) -> str:
    """De gemeten banddekking naast het doel, met de uitspraak die daarbij past.

    Apart gezet op 15 augustus 2026, samen met een correctie. Het doel kwam bij
    ontbreken van `band_doel` uit de kolom `beloofd` van de dekkingsmeting, en
    dat is `boven - onder`: de NOMINALE breedte van het kwantielpaar (vandaag
    0,05-0,95, dus 90%). Dat is geen belofte aan de lezer maar een eigenschap
    van de gekozen kwantielen -- `kalibreer_kwantielen` zoekt juist een nominaal
    bredere band om er out-of-sample het doel (80%) van te maken. Met die
    terugval zou het scherm "waar 90,0% bedoeld is" zeggen over een band die op
    80% gekalibreerd is, en zou de tak hieronder de band te smal noemen terwijl
    ze haar doel haalt. Zonder opgegeven doel doet de beller nu helemaal geen
    uitspraak over een doel.
    """
    zin = t(
        f" Out-of-sample nagemeten dekt die band {_pct_tekst(laagste)} tot "
        f"{_pct_tekst(hoogste)} van de dagen, waar {_pct_tekst(doel)} bedoeld is",
        f" Remesuré out-of-sample, cet intervalle couvre de {_pct_tekst(laagste)} "
        f"à {_pct_tekst(hoogste)} des jours, là où {_pct_tekst(doel)} est visé",
    )
    if hoogste < doel:
        return zin + t(
            ": de band is eerder te smal dan te ruim. Reken buiten de band dus "
            "vaker op een uitschieter dan de grafiek suggereert.",
            " : l'intervalle est plutôt trop étroit que trop large. "
            "Attendez-vous donc à des écarts hors intervalle plus fréquents que "
            "le graphique ne le laisse penser.",
        )
    if laagste > doel:
        return zin + t(
            ": de band is eerder te ruim dan te smal — de werkelijkheid blijft "
            "er vaker binnen dan bedoeld.",
            " : l'intervalle est plutôt trop large que trop étroit — la réalité "
            "y reste plus souvent que prévu.",
        )
    # De band ligt om het doel heen. "Schommelt rond dat doel" was hier tot
    # 15 augustus 2026 het enige wat er stond, en dat is te welwillend zodra de
    # zwakste horizonstap er ver onder zit: bij 69% tot 82% op een doel van 80%
    # haalt de verste stap het duidelijk niet, en juist die stap draagt het
    # weektotaal. De kalibratie stuurt op het gewogen gemiddelde, niet op de
    # slechtste stap, dus dit is geen fout maar wel iets om te weten.
    return zin + t(
        "; de meting schommelt per horizonstap rond dat doel, en de zwakste "
        "stap haalt het niet. Verderop in de week valt de werkelijkheid dus "
        "vaker buiten de band dan vooraan.",
        " ; la mesure oscille autour de cette cible selon le pas d'horizon, et "
        "le pas le plus faible ne l'atteint pas. En fin de semaine, la réalité "
        "sort donc plus souvent de l'intervalle qu'en début.",
    )


def prognose(
    dagen: pd.DataFrame,
    *,
    bron: list[str],
    bijgewerkt_op: datetime,
    baseline_naam: str,
    wape: float,
    venster: canoniek.Prognosevenster,
    stappen: pd.DataFrame | None = None,
    track: pd.DataFrame | None = None,
    banddekking: pd.DataFrame | None = None,
    band_kwantielen: tuple[float, float] | None = None,
    band_doel: float | None = None,
    categorieen: list | None = None,
    categorieen_overgeslagen: list[str] | None = None,
    kalenderdekking: date | None = None,
    sluitingsdekking: date | None = None,
    #: De dagen waarover een beheerder een uitspraak heeft gedaan op het
    #: scherm Sluitingsdagen (bevestigd open; bevestigd dicht staat al in
    #: `gepland_dicht` en komt niet in het venster). Stuurt het per-dag-
    #: voorbehoud: een bevestigde dag heeft geen aanname meer nodig.
    bevestigde_dagen: frozenset = frozenset(),
    #: De wacht uit `sluitingsdagen.lopende_sluiting`: eindigt de meting in een
    #: gesloten reeks die de sluitingslijst niet verklaart, dan draagt dit het
    #: signaal. `None` betekent: niets aan de hand, of niet gemeten.
    lopende_sluiting=None,
    opbouw: pd.DataFrame | None = None,
    meting: dict | None = None,
) -> dict:
    """De prognose met een band die uit de backtest komt.

    `kalenderdekking` is de laatste dag waarvoor de schoolvakantiekalender
    gevuld is. Reikt het venster daar voorbij, dan wordt dat gemeld: het model
    zou die dagen stil als gewone dagen behandelen, en een stil gat in een
    invoer is hetzelfde soort leugen als een stil gat in een cijfer (harde
    regel 8, toegepast op een invoer).

    `opbouw` (verfijning.opbouw) draagt per doeldag de decompositie
    basis × niveau × kalenderfactor — de kolommen zijn per test gelijk aan de
    voorspelling zelf, zodat de uitleg op het scherm nooit een tweede model
    is. `meting` draagt de kerncijfers van de backtest voor de modelkaart:
    n_dagen, van, tot, bias (fractie, + is te hoog), en optioneel wape_90,
    bias_90, wape_180, bias_180 over de jongste gemeten vensters.

    `wape` staat in de toelichting omdat een voorspelling zonder zijn gemeten
    nauwkeurigheid een mening is (harde regel 7).

    `venster` is het resultaat van de horizonregel (`canoniek.prognosevenster`) en
    draagt alles wat er over dit venster te zeggen valt: waar het begint, welke
    gesloten dagen eruit zijn gesneden, en of er een gat zit tussen de laatste
    meting en vandaag. Dat gat is geen randgeval — op 12 augustus 2026 was het elf
    dagen breed — en het hoort op het scherm, niet in een logbestand.

    Drie optionele metingen uit het harnas maken de belofte van dit scherm
    toetsbaar:

    `stappen` (rolling.per_horizon) draagt de fout per horizonstap; de eerste en
    de verste stap komen in de nauwkeurigheidstekst, want de onzekerheid van
    overmorgen is niet die van morgen.

    `track` (rolling.trackrecord) is voorspeld naast werkelijk voor de laatste
    gemeten open dagen, out-of-sample. De vraag die een CFO over een model stelt
    is niet hoe het werkt maar of het de vorige keer klopte — dit is dat antwoord,
    als grafiek. Werkelijk in warmgrijs, verwacht in bordeaux: de kleur zit in de
    lijnen van de grafiek en draagt identiteit, geen oordeel (huisstijl).

    `banddekking` (rolling.dekking) is hoe vaak de werkelijkheid werkelijk binnen
    de getoonde band viel. De meting van 13 augustus 2026 zegt 56 à 74% waar 80%
    bedoeld is; dat staat hier hardop, want een band die breder oogt dan hij
    dekt, is precies het soort stille leugen dat dit platform niet vertelt.
    """
    punten = [
        (_dag_label(pd.Timestamp(r.datum)), float(r.verwacht))
        for r in dagen.itertuples()
    ]
    maximum = float(dagen["boven"].max()) if not dagen.empty else 0.0

    grafiek = _lijn(punten, t("Verwachte omzet", "Chiffre d'affaires attendu"),
                    "bordeaux", maximum)
    grafiek["band"] = [
        {
            "x": _dag_label(pd.Timestamp(r.datum)),
            "onder": round(float(r.onder), 2),
            "boven": round(float(r.boven), 2),
        }
        for r in dagen.itertuples()
    ]

    onbeschikbaar: list[dict] = []

    # Nog vóór het meetgat: dit gaat niet over wat er ontbreekt maar over wat
    # er wél staat. Loopt er een sluiting door die de lijst niet kent, dan
    # kunnen de cijfers hieronder op gesloten dagen slaan, en dat moet een
    # lezer weten voordat hij ze leest.
    if lopende_sluiting is not None:
        onbeschikbaar.append({
            "veld": "prognose.lopende_sluiting",
            "reden": lopende_sluiting.melding(),
        })

    # Dan het gat, want dat bepaalt hoe de rest van dit scherm gelezen moet
    # worden: cijfers tot 31 juli, een prognose vanaf 12 augustus, en elf dagen
    # ertussen waarover niemand iets zegt.
    gat = venster.meetgat
    if gat is not None:
        deel, deel_fr = [], []
        if gat.gemeten_gesloten:
            deel.append(f"{_dagen_nl(gat.gemeten_gesloten)} zijn gemeten en "
                        "waren gesloten")
            deel_fr.append(f"{_dagen_nl(gat.gemeten_gesloten)} ont été mesurés "
                           "et la boutique était fermée")
        if gat.gepland_dicht:
            deel.append(f"{_dagen_nl(gat.gepland_dicht)} waren vooraf als "
                        "gesloten aangekondigd")
            deel_fr.append(f"{_dagen_nl(gat.gepland_dicht)} étaient annoncés "
                           "fermés à l'avance")
        if gat.niet_ingeladen:
            deel.append(f"{_dagen_nl(gat.niet_ingeladen)} zijn nog niet uit de "
                        "bronsystemen ingeladen")
            deel_fr.append(f"{_dagen_nl(gat.niet_ingeladen)} n'ont pas encore "
                           "été chargés depuis les systèmes sources")
        staart = ("Daarvan: " + "; ".join(deel) + "." if deel else "")
        staart_fr = ("Dont : " + "; ".join(deel_fr) + "." if deel_fr else "")
        onbeschikbaar.append({
            "veld": "prognose.meetgat",
            "reden": t(
                (
                    f"Over {_datum_nl(gat.van)} t/m {_datum_nl(gat.tot)} "
                    f"({_dagen_nl(gat.dagen)}) zegt dit scherm niets: die "
                    f"dagen liggen na de laatste meting en voor vandaag. "
                    + staart
                ).strip(),
                (
                    f"Sur la période du {_datum_nl(gat.van)} au "
                    f"{_datum_nl(gat.tot)} ({_dagen_nl(gat.dagen)}), cet "
                    "écran ne dit rien : ces jours se situent après la "
                    "dernière mesure et avant aujourd'hui. " + staart_fr
                ).strip(),
            ),
        })

    onbeschikbaar.append({
        "veld": "prognose.startpunt",
        "reden": t(
            f"De prognose begint op {_datum_nl(venster.start)} en beslaat "
            f"{_dagen_nl(len(dagen))}. Het startpunt is de dag na de laatste "
            f"gemeten open winkeldag ({_datum_nl(venster.gemeten_tot)}) of "
            f"vandaag ({_datum_nl(venster.vandaag)}), wat van de twee later "
            "valt: een verwachting voor een dag die al voorbij is, is geen "
            "verwachting. Tot wanneer de cijfers gemeten zijn, staat onderaan "
            "elk scherm.",
            f"La prévision commence le {_datum_nl(venster.start)} et couvre "
            f"{_dagen_nl(len(dagen))}. Le point de départ est le lendemain du "
            "dernier jour d'ouverture mesuré "
            f"({_datum_nl(venster.gemeten_tot)}) ou aujourd'hui "
            f"({_datum_nl(venster.vandaag)}), selon celui qui vient en "
            "dernier : une prévision pour un jour déjà écoulé n'est pas une "
            "prévision. La date jusqu'à laquelle les chiffres sont mesurés "
            "figure au bas de chaque écran.",
        ),
    })

    if venster.overgeslagen:
        lijst = ", ".join(_datum_nl(d) for d in venster.overgeslagen)
        onbeschikbaar.append({
            "veld": "prognose.gesloten_dagen",
            "reden": t(
                f"Overgeslagen in dit venster: {lijst}. Die dagen staan in de "
                "kalender als gemeten en gesloten, en op een dag dat de zaak "
                "dicht is valt er niets te voorspellen. Ze staan niet in de "
                "grafiek en tellen niet mee in het weektotaal.",
                f"Ignorés dans cette fenêtre : {lijst}. Ces jours figurent au "
                "calendrier comme mesurés et fermés, et un jour où la boutique "
                "est fermée, il n'y a rien à prévoir. Ils ne figurent pas dans "
                "le graphique et ne comptent pas dans le total hebdomadaire.",
            ),
        })

    # Aangekondigde sluitingen staan apart van `overgeslagen`, want het is een
    # ander verhaal: die dagen zijn gemeten en bleken dicht, deze zijn nog niet
    # gemeten en gaan dicht omdat de bakkerij dat vooraf zegt. Met de reden erbij,
    # letterlijk zoals ze aangeleverd is — de gebruiker die zich afvraagt waarom
    # er volgende week niets staat, hoort "Zomersluiting" te lezen en niet
    # "overgeslagen".
    if venster.gepland_gesloten:
        per_reden: dict[str, list[date]] = {}
        for dag, reden in venster.gepland_gesloten:
            per_reden.setdefault(
                reden or t("gepland gesloten", "fermeture planifiée"), []
            ).append(dag)
        # De Franse delen dragen hun eigen voorzetsel ("du ... au ...", "le
        # ..."), want in het Frans hangt dat aan de periode en niet aan de zin
        # eromheen. De zin hieronder eindigt daarom op "Aucune prévision" en
        # niet op "Aucune prévision pour".
        delen = [
            t(f"{_datum_nl(min(dagen))} t/m {_datum_nl(max(dagen))} ({reden})",
              f"du {_datum_nl(min(dagen))} au {_datum_nl(max(dagen))} ({reden})")
            if len(dagen) > 1
            else t(f"{_datum_nl(dagen[0])} ({reden})",
                   f"le {_datum_nl(dagen[0])} ({reden})")
            for reden, dagen in per_reden.items()
        ]
        opsomming = "; ".join(delen)
        onbeschikbaar.append({
            "veld": "prognose.geplande_sluiting",
            "reden": t(
                f"Geen verwachting voor {opsomming}. Die dagen zijn vooraf als "
                "gesloten aangekondigd, en op een dag dat de zaak dicht is "
                "valt er niets te voorspellen. Ze staan niet in de grafiek en "
                "tellen niet mee in het weektotaal; het venster schuift door "
                "naar de eerstvolgende open dagen.",
                f"Aucune prévision {opsomming}. Ces jours ont été "
                "annoncés comme fermés à l'avance, et un jour où la boutique "
                "est fermée, il n'y a rien à prévoir. Ils ne figurent pas dans "
                "le graphique et ne comptent pas dans le total hebdomadaire ; "
                "la fenêtre se décale vers les jours d'ouverture suivants.",
            ),
        })

    if venster.buiten_kalender:
        onbeschikbaar.append({
            "veld": "prognose.kalenderbereik",
            "reden": t(
                f"Voor {_dagen_nl(len(venster.buiten_kalender))} in dit venster "
                f"({_datum_nl(venster.buiten_kalender[0])} t/m "
                f"{_datum_nl(venster.buiten_kalender[-1])}) bestaat geen "
                "kalenderrij: de kalender loopt niet ver genoeg door voorbij de "
                "laatste meting. Voor die dagen is niet nagegaan of de winkel open "
                "is; ze zijn als onbekend meegenomen.",
                f"Pour {_dagen_nl(len(venster.buiten_kalender))} de cette "
                f"fenêtre (du {_datum_nl(venster.buiten_kalender[0])} au "
                f"{_datum_nl(venster.buiten_kalender[-1])}), il n'existe pas de "
                "ligne de calendrier : le calendrier ne va pas assez loin au-delà "
                "de la dernière mesure. Pour ces jours, l'ouverture de la "
                "boutique n'a pas été vérifiée ; ils sont repris comme inconnus.",
            ),
        })

    # De dekkingswacht op de vakantiekalender. Niet hetzelfde als
    # `buiten_kalender` hierboven: dat gaat over openingsdagen, dit over de
    # schoolvakanties waarmee de voorspeller corrigeert.
    if kalenderdekking is not None and len(venster.dagen) > 0:
        laatste_doeldag = venster.dagen.max().date()
        if laatste_doeldag > kalenderdekking:
            onbeschikbaar.append({
                "veld": "prognose.kalenderdekking",
                "reden": t(
                    f"De schoolvakantiekalender is gevuld tot "
                    f"{_datum_nl(kalenderdekking)}, maar dit venster loopt tot "
                    f"{_datum_nl(laatste_doeldag)}. Dagen voorbij de dekking "
                    "worden zonder vakantie-informatie voorspeld, alsof het "
                    "gewone dagen zijn. Ververs de kalender met "
                    "`make vakanties`.",
                    f"Le calendrier des vacances scolaires est rempli jusqu'au "
                    f"{_datum_nl(kalenderdekking)}, mais cette fenêtre va "
                    f"jusqu'au {_datum_nl(laatste_doeldag)}. Les jours situés "
                    "au-delà de la couverture sont prévus sans information de "
                    "vacances, comme s'il s'agissait de jours ordinaires. "
                    "Rafraîchissez le calendrier avec `make vakanties`.",
                ),
            })

    # Het per-dag-voorbehoud: welke doeldagen heeft niemand beantwoord? None
    # betekent "er is geen enkele sluitingsbron" en levert de oude, algemene
    # tekst; een lege tuple betekent "alles beantwoord" en dat is een andere
    # uitspraak (harde regel 8: onbekend is niet hetzelfde als open).
    if sluitingsdekking is None and not bevestigde_dagen:
        onbekend = None
    else:
        onbekend = sk.onbekende_dagen(
            dagen["datum"] if not dagen.empty else (),
            dekking_tot=sluitingsdekking,
            beantwoord=set(bevestigde_dagen),
        )
    onbeschikbaar.append({
        "veld": "prognose.sluitingsdagen",
        "reden": _kalenderreden(sluitingsdekking, onbekend),
    })

    if dagen.empty:
        onbeschikbaar.append({
            "veld": "prognose.weektotaal",
            "reden": t(
                f"Geen weektotaal: er blijft geen enkele dag over om te "
                f"voorspellen vanaf {_datum_nl(venster.start)}. Een nul zou hier "
                "een verwachte omzet van nul euro suggereren, en dat is niet wat "
                "er aan de hand is.",
                f"Pas de total hebdomadaire : il ne reste aucun jour à prévoir à "
                f"partir du {_datum_nl(venster.start)}. Un zéro laisserait "
                "croire à un chiffre d'affaires attendu de zéro euro, et ce "
                "n'est pas ce dont il s'agit.",
            ),
        })
    else:
        onbeschikbaar.append({"veld": "prognose.weektotaal",
                              "reden": t(BANDREDEN, BANDREDEN_FR)})

    # De bandtekst volgt de kalibratie: zonder meegegeven kwantielen geldt de
    # oude 10-90-standaard, mét kwantielen staat erbij dat ze gekózen zijn op
    # een out-of-sample gemeten dekking en niet op hun nominale naam.
    onder_p, boven_p = band_kwantielen if band_kwantielen else (0.10, 0.90)
    bandzin = t(
        f"De band is het {onder_p * 100:g}e tot {boven_p * 100:g}e percentiel "
        "van de fouten die deze methode in die backtest werkelijk maakte, "
        "niet een aangenomen verdeling.",
        f"L'intervalle va du {onder_p * 100:g}e au {boven_p * 100:g}e "
        "percentile des erreurs que cette méthode a réellement commises dans ce "
        "backtest, et non d'une distribution supposée.",
    )
    if band_kwantielen and band_doel is not None:
        # Deze zin beschrijft de PROCEDURE en belooft geen uitkomst. Ze zei tot
        # 15 augustus 2026 onvoorwaardelijk dat het gekozen paar het doel dekt,
        # terwijl `kalibreer_kwantielen` bij mislukking gewoon de breedste
        # kandidaat teruggeeft — dan stond hier een gehaald doel dat niet
        # gehaald was, en sprak deze alinea zichzelf twee zinnen verderop tegen.
        # Wat de band werkelijk dekt, staat hieronder bij de gemeten dekking:
        # daar hoort het, want dat is een meting en dit is een werkwijze.
        bandzin += t(
            f" Die kwantielen zijn gekalibreerd: gekozen is het smalste paar "
            f"dat out-of-sample zo dicht mogelijk bij {_pct_tekst(band_doel)} van "
            "de dagen uitkomt.",
            f" Ces quantiles sont calibrés : on retient la paire la plus "
            f"étroite qui, remesurée out-of-sample, s'approche le plus de "
            f"{_pct_tekst(band_doel)} des jours.",
        )
    # `baseline_naam` komt uit de modellaag en is daar nog Nederlands; alleen
    # de zin eromheen hoort bij dit bestand.
    reden_nauwkeurigheid = t(
        f"Methode: {baseline_naam}. Gemeten in een rolling-origin "
        f"backtest op de eigen historiek: gemiddelde afwijking "
        f"{_pct_tekst(wape)} van de dagomzet. ",
        f"Méthode : {baseline_naam}. Mesurée dans un backtest rolling-origin "
        f"sur l'historique propre : écart moyen de {_pct_tekst(wape)} du chiffre "
        "d'affaires journalier. ",
    ) + bandzin
    if stappen is not None and not stappen.empty:
        eerste = stappen.iloc[0]
        verste = stappen.iloc[-1]
        reden_nauwkeurigheid += t(
            f" Elke dag draagt de band van zijn eigen horizonstap: voor de "
            f"eerstvolgende open dag is de gemeten afwijking "
            f"{_pct_tekst(float(eerste['wape']))}, voor de verste dag in dit venster "
            f"{_pct_tekst(float(verste['wape']))} — morgen is beter te voorspellen "
            "dan over een week, en de band hoort dat te tonen.",
            f" Chaque jour porte l'intervalle de son propre pas d'horizon : pour "
            f"le prochain jour d'ouverture, l'écart mesuré est de "
            f"{_pct_tekst(float(eerste['wape']))}, pour le jour le plus éloigné de "
            f"cette fenêtre {_pct_tekst(float(verste['wape']))} — demain se prévoit "
            "mieux que dans une semaine, et l'intervalle doit le montrer.",
        )
    if banddekking is not None and not banddekking.empty:
        gemeten = banddekking.dropna(subset=["binnen_band"])
        gemeten = gemeten[gemeten["n"] > 0]
        if not gemeten.empty:
            laagste = float(gemeten["binnen_band"].min())
            hoogste = float(gemeten["binnen_band"].max())
            # Zonder een opgegeven doel wordt hier GEEN doel meer verzonnen.
            # De terugval was `beloofd`, en dat is `boven - onder`: de nominale
            # breedte van het kwantielpaar (vandaag 90%), niet het dekkingsdoel
            # (80%). Het scherm zou dan "waar 90,0% bedoeld is" hebben gezegd
            # over een band die op 80% gekalibreerd is, en de twee takken
            # hieronder zouden bovendien de verkeerde kant op wijzen.
            if band_doel is None:
                reden_nauwkeurigheid += t(
                    f" Out-of-sample nagemeten dekt die band "
                    f"{_pct_tekst(laagste)} tot {_pct_tekst(hoogste)} van de dagen.",
                    f" Remesuré out-of-sample, cet intervalle couvre de "
                    f"{_pct_tekst(laagste)} à {_pct_tekst(hoogste)} des jours.",
                )
            else:
                reden_nauwkeurigheid += _banduitspraak(laagste, hoogste,
                                                       band_doel)
    onbeschikbaar.append({
        "veld": "prognose.nauwkeurigheid",
        "reden": reden_nauwkeurigheid,
    })

    if categorieen_overgeslagen:
        onbeschikbaar.append({
            "veld": "prognose.categorieen",
            "reden": t(
                "Zonder eigen prognose, want te weinig gemeten open dagen om "
                "de fout betrouwbaar te meten (harde regel 7): "
                + ", ".join(categorieen_overgeslagen) + ".",
                "Sans prévision propre, faute d'assez de jours d'ouverture "
                "mesurés pour mesurer l'erreur de façon fiable (règle stricte "
                "7) : " + ", ".join(categorieen_overgeslagen) + ".",
            ),
        })

    # Het trackrecord: voorspeld naast werkelijk, elke dag out-of-sample. Geen
    # trackrecord is een reden, geen leeg vak.
    trackrecord_data = None
    if track is not None and not track.empty:
        labels = [_dag_label(pd.Timestamp(d)) for d in track["datum"]]
        maximum_track = float(
            max(track["verwacht"].max(), track["werkelijk"].max())
        )
        som_werkelijk = float(track["werkelijk"].sum())
        track_wape = (
            float((track["verwacht"] - track["werkelijk"]).abs().sum())
            / som_werkelijk
            if som_werkelijk > 0
            else None
        )
        trackrecord_data = {
            "grafiek": {
                "reeksen": [
                    {
                        "naam": t("Werkelijke omzet", "Chiffre d'affaires réel"),
                        "kleur": "warmgrijs",
                        "punten": [
                            {"x": x, "y": round(float(y), 2)}
                            for x, y in zip(labels, track["werkelijk"], strict=True)
                        ],
                    },
                    {
                        "naam": t("Wat het model voorspelde", "Prévision du modèle"),
                        "kleur": "bordeaux",
                        "punten": [
                            {"x": x, "y": round(float(y), 2)}
                            for x, y in zip(labels, track["verwacht"], strict=True)
                        ],
                    },
                ],
                "y_as": _euro_as(maximum_track),
            },
            "dagen": len(track),
            "wape": _pct_machine(track_wape * 100) if track_wape is not None else None,
            "van": pd.Timestamp(track["datum"].iloc[0]).date().isoformat(),
            "tot": pd.Timestamp(track["datum"].iloc[-1]).date().isoformat(),
        }
    else:
        onbeschikbaar.append({
            "veld": "prognose.trackrecord",
            "reden": t(
                "Geen trackrecord: de historiek is te kort om dagen te tonen "
                "die het model out-of-sample voorspeld heeft. Zodra er genoeg "
                "gemeten dagen zijn, staat hier voorspeld naast werkelijk.",
                "Pas d'historique de performance : l'historique est trop court "
                "pour montrer des jours que le modèle a prévus out-of-sample. "
                "Dès qu'il y aura assez de jours mesurés, le prévu figurera ici "
                "à côté du réel.",
            ),
        })

    # De opbouw per dag, op ISO-datum gekoppeld aan de dagenlijst hieronder.
    # Een kalenderfactor van precies 1 wordt None: er is dan geen correctie,
    # en het scherm hoort geen "× 1,000" te tonen die niets betekent.
    opbouw_per_dag: dict[str, dict] = {}
    if opbouw is not None and not opbouw.empty:
        for r in opbouw.itertuples():
            opbouw_per_dag[pd.Timestamp(r.datum).date().isoformat()] = {
                "basis": _s(float(r.basis)),
                "niveau": _factor(r.niveau),
                "kalenderfactor": (_factor(r.kalenderfactor)
                                   if float(r.kalenderfactor) != 1.0 else None),
                "kenmerk": r.kenmerk or None,
            }

    # De modelkaart: de verantwoording van het model in één blok — methode,
    # meting, bias, band en kalenderdekking. Alles hier is gemeten, niets is
    # een belofte; de audit van 14 augustus noemde het gemis "model
    # governance" en dit is dat antwoord.
    modelkaart = None
    if meting is not None:
        rijen = [
            {"label": t("Methode", "Méthode"), "waarde": baseline_naam},
            {"label": t("Laatste herrekening", "Dernier recalcul"),
             "waarde": _datum_nl(bijgewerkt_op)},
            {"label": t("Backtest", "Backtest"),
             "waarde": t(
                 f"{_dagen_nl(int(meting['n_dagen']))} out-of-sample "
                 f"voorspeld, {_datum_nl(meting['van'])} t/m "
                 f"{_datum_nl(meting['tot'])}",
                 f"{_dagen_nl(int(meting['n_dagen']))} prévus out-of-sample, du "
                 f"{_datum_nl(meting['van'])} au {_datum_nl(meting['tot'])}",
             )},
            {"label": t("Gemeten afwijking (WAPE)", "Écart mesuré (WAPE)"),
             "waarde": t(f"{_pct_tekst(wape)} van de dagomzet",
                         f"{_pct_tekst(wape)} du chiffre d'affaires journalier")},
            {"label": t("Systematische afwijking", "Biais systématique"),
             "waarde": _bias_nl(float(meting["bias"]))},
        ]
        for sleutel, label, label_fr in (
            ("90", "Jongste 90 gemeten dagen", "90 derniers jours mesurés"),
            ("180", "Jongste 180 gemeten dagen", "180 derniers jours mesurés"),
        ):
            w = meting.get(f"wape_{sleutel}")
            if w is not None:
                waarde = _pct_tekst(float(w))
                b = meting.get(f"bias_{sleutel}")
                if b is not None:
                    waarde += f", {_bias_nl(float(b))}"
                rijen.append({"label": t(label, label_fr), "waarde": waarde})
        if banddekking is not None and not banddekking.empty and \
                band_doel is not None:
            g = banddekking.dropna(subset=["binnen_band"])
            g = g[g["n"] > 0]
            if not g.empty:
                rijen.append({
                    "label": t("Band", "Intervalle"),
                    "waarde": t(
                        f"doel {_pct_tekst(band_doel)} van de dagen binnen "
                        f"de band; out-of-sample gemeten "
                        f"{_pct_tekst(float(g['binnen_band'].min()))} tot "
                        f"{_pct_tekst(float(g['binnen_band'].max()))} "
                        "per horizonstap",
                        f"cible {_pct_tekst(band_doel)} des jours dans "
                        f"l'intervalle ; mesuré out-of-sample de "
                        f"{_pct_tekst(float(g['binnen_band'].min()))} à "
                        f"{_pct_tekst(float(g['binnen_band'].max()))} par pas "
                        "d'horizon",
                    ),
                })
        if kalenderdekking is not None:
            rijen.append({
                "label": t("Kalenderdekking", "Couverture du calendrier"),
                "waarde": t(
                    "schoolvakanties gevuld t/m "
                    f"{_datum_nl(kalenderdekking)}",
                    "vacances scolaires renseignées jusqu'au "
                    f"{_datum_nl(kalenderdekking)}",
                ),
            })
        modelkaart = {
            "rijen": rijen,
            "toelichting": t(
                "Alles op deze kaart is gemeten in dezelfde rolling-origin "
                "backtest op de eigen historiek — train tot een dag, voorspel "
                "de week erna, schuif op. Niets hiervan is een belofte.",
                "Tout ce qui figure sur cette fiche a été mesuré dans le même "
                "backtest rolling-origin sur l'historique propre — entraîner "
                "jusqu'à un jour, prévoir la semaine suivante, décaler. Rien de "
                "tout cela n'est une promesse.",
            ),
        }

    return antwoord(
        {
            "grafiek": grafiek,
            "dagen": [
                {
                    "datum": pd.Timestamp(r.datum).date().isoformat(),
                    "verwacht": _s(float(r.verwacht)),
                    "onder": _s(float(r.onder)),
                    "boven": _s(float(r.boven)),
                    "opbouw": opbouw_per_dag.get(
                        pd.Timestamp(r.datum).date().isoformat()
                    ),
                }
                for r in dagen.itertuples()
            ],
            "modelkaart": modelkaart,
            # Het weektotaal is de som van de puntvoorspellingen over de dagen die
            # werkelijk in het venster zitten — nooit over zeven kalenderdagen.
            # Bewust zonder band: de dagbanden optellen zou een zekerheid
            # suggereren die de backtest nooit gemeten heeft (zie onbeschikbaar).
            "weektotaal": None if dagen.empty else _s(float(dagen["verwacht"].sum())),
            # Hoeveel dagen in die som zitten, zodat het scherm "over 7 dagen" niet
            # hoeft aan te nemen. Na een sluiting kunnen het er minder zijn.
            "weektotaal_dagen": len(dagen),
            "trackrecord": trackrecord_data,
            # Per categorie een eigen prognose met een eigen gemeten fout.
            # De dagprognose hierboven blijft de directe: de som van de
            # categorieën won de backtest niet materieel (0,42 punt op een
            # lat van 0,5 — 13 augustus 2026). Dit blok wijst dus aan wélke
            # hoek van het assortiment de week draagt; het telt bewust niet
            # op tot het weektotaal hierboven, en dat staat in de toelichting.
            "categorieen": {
                "blokken": [
                    {
                        "categorie": str(c.categorie),
                        "aandeel": _pct_machine(float(c.aandeel_pct)),
                        "wape": _pct_machine(float(c.wape) * 100),
                        "weektotaal": _s(float(c.weektotaal)),
                        "dagen": [
                            {
                                "datum": _iso_datum(r.datum),
                                "verwacht": _s(float(r.verwacht)),
                                "onder": _s(float(r.onder)),
                                "boven": _s(float(r.boven)),
                            }
                            for r in c.band.itertuples()
                        ],
                    }
                    for c in categorieen
                ],
                "toelichting": t(
                    "Elke categorie draagt haar eigen prognose met haar eigen "
                    "gemeten afwijking uit dezelfde rolling-origin backtest. "
                    "De categorieën tellen niet exact op tot het weektotaal "
                    "hierboven: dat komt uit de directe dagprognose, die de "
                    "backtest (net) beter doorstond dan de som van de "
                    "categorieën.",
                    "Chaque catégorie porte sa propre prévision, avec son propre "
                    "écart mesuré dans le même backtest rolling-origin. Les "
                    "catégories ne s'additionnent pas exactement pour donner le "
                    "total hebdomadaire ci-dessus : celui-ci vient de la "
                    "prévision journalière directe, qui a passé le backtest "
                    "(de justesse) mieux que la somme des catégories.",
                ),
            } if categorieen else None,
        },
        bron=bron,
        bijgewerkt_op=bijgewerkt_op,
        gemeten_tot=venster.gemeten_tot,
        onbeschikbaar=onbeschikbaar,
    )


def nu() -> datetime:
    return datetime.now(TIJDZONE)
