"""De contractboom omzetten naar rijen voor `contract_antwoord`.

De contractbouw schrijft bestanden (platform/contract/), migratie 006 is de
gehoste vorm van diezelfde bestanden. Deze module doet de vertaling tussen
die twee — en niets meer: geen normalisatie, geen herberekening, de JSON gaat
er bit voor bit in zoals hij gebouwd is (Postgres' jsonb bewaart geen
witruimte of sleutelvolgorde, maar de inhoud is dezelfde).

De boom die de contractbouw schrijft, en dus de boom die hier gelezen wordt:

    platform/contract/
      overzicht.json ... sluitingsdagen.json   de zeven antwoorden, Nederlands
      winkels.json                             de winkelindex
      winkels/<slug>/*.json                    per winkel dezelfde zeven
      fr/                                      alles nog eens, Frans

Alles hier is streng, en dat is de bedoeling. Een ontbrekend scherm, een
onleesbare JSON of een winkelmap die niet in de index staat betekent een half
gebouwd contract, en een half contract uploaden is erger dan luid falen: de
sync draait 's nachts en niemand kijkt mee. Wie een zevende scherm toevoegt,
moet SCHERMEN hier bewust bijwerken — dezelfde afspraak als het Scherm-type
in platform/lib/laadContract.ts.

Pure functies, geen database en geen netwerk; het schrijven zelf doet
scripts/contract_laad.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bakkerij.taal import STANDAARDTAAL, TALEN

#: De zeven genummerde antwoorden. Moet gelijk lopen met wat de contractbouw
#: schrijft en met het Scherm-type in de UI; de tests leggen dat vast.
#: `sluitingsdagen` kwam er op 19 augustus 2026 bij: de kandidatenlijst voor
#: het beheerscherm van de sluitingskalender.
SCHERMEN = ("overzicht", "kanalen", "producten", "marge", "prognose", "stand",
            "sluitingsdagen")

#: De winkelindex reist mee als extra sleutel naast de schermen: de UI
#: (laadWinkels) heeft hem nodig om de kiezer te tonen, dus de database moet
#: hem dragen.
WINKELINDEX = "winkels"

#: In de database staat het totaal onder de lege string, niet onder null:
#: null kan geen deel van een primaire sleutel zijn.
TOTAAL = ""


@dataclass(frozen=True)
class ContractRij:
    scherm: str
    taal: str
    winkel: str  # winkelslug, of TOTAAL
    antwoord: str  # de JSON-tekst zoals de contractbouw haar schreef


def _lees_json(pad: Path) -> str:
    """Lees een contractbestand en toets dat het geldige JSON is.

    De inhoud wordt niet teruggegeven als object maar als tekst: wij vertalen
    het contract, we interpreteren het niet. De json.loads is alleen de wacht
    tegen een half weggeschreven of kapot bestand.
    """
    if not pad.is_file():
        raise FileNotFoundError(
            f"contractbestand ontbreekt: {pad.name} (in {pad.parent}). "
            "Draai eerst de contractbouw (make contract)."
        )
    tekst = pad.read_text(encoding="utf-8")
    try:
        json.loads(tekst)
    except json.JSONDecodeError as fout:
        raise ValueError(
            f"contractbestand is geen geldige JSON: {pad.name} "
            f"(in {pad.parent}): regel {fout.lineno}, kolom {fout.colno}."
        ) from fout
    return tekst


def _winkelslugs(index_tekst: str, waar: Path) -> list[str]:
    """De slugs uit de winkelindex, zoals de contractbouw ze vastlegde."""
    index = json.loads(index_tekst)
    winkels = index.get("winkels")
    if not isinstance(winkels, list):
        raise TypeError(
            f"winkels.json in {waar} mist de lijst 'winkels'; "
            "dit is geen uitvoer van de contractbouw."
        )
    slugs = []
    for w in winkels:
        slug = w.get("slug") if isinstance(w, dict) else None
        if not isinstance(slug, str) or not slug:
            raise ValueError(
                f"winkels.json in {waar} bevat een winkel zonder slug."
            )
        slugs.append(slug)
    return slugs


def _verzamel_map(map_: Path, taal: str) -> list[ContractRij]:
    """Alle rijen voor één taalmap: de zeven antwoorden, de index, de winkels."""
    if not map_.is_dir():
        raise FileNotFoundError(
            f"contractmap voor taal '{taal}' ontbreekt: {map_}. "
            "Draai eerst de contractbouw (make contract)."
        )

    rijen = [
        ContractRij(scherm, taal, TOTAAL, _lees_json(map_ / f"{scherm}.json"))
        for scherm in SCHERMEN
    ]

    index_tekst = _lees_json(map_ / f"{WINKELINDEX}.json")
    rijen.append(ContractRij(WINKELINDEX, taal, TOTAAL, index_tekst))

    slugs = _winkelslugs(index_tekst, map_)
    winkels_dir = map_ / "winkels"
    mappen = (
        sorted(p.name for p in winkels_dir.iterdir() if p.is_dir())
        if winkels_dir.is_dir()
        else []
    )
    # De index is de waarheid waarop de UI navigeert; een map zonder
    # indexvermelding (of andersom) is een half gebouwd contract.
    if mappen != sorted(slugs):
        raise ValueError(
            f"de winkelmappen in {map_} ({mappen}) dekken de index "
            f"({sorted(slugs)}) niet; het contract is half gebouwd. "
            "Draai de contractbouw opnieuw."
        )

    for slug in sorted(slugs):
        rijen.extend(
            ContractRij(
                scherm, taal, slug,
                _lees_json(winkels_dir / slug / f"{scherm}.json"),
            )
            for scherm in SCHERMEN
        )
    return rijen


def verzamel(contractmap: Path) -> list[ContractRij]:
    """De volledige contractboom als rijen, in vaste volgorde.

    De volgorde (taal, dan winkel, dan scherm zoals SCHERMEN ze noemt) is
    deterministisch zodat twee runs op dezelfde boom dezelfde lijst geven —
    een lijst die per run anders is, is niet reproduceerbaar.
    """
    rijen: list[ContractRij] = []
    for taal in TALEN:
        map_ = contractmap if taal == STANDAARDTAAL else contractmap / taal
        rijen.extend(_verzamel_map(map_, taal))
    return rijen


#: Eén statement, twee stappen, één transactie: eerst alles weg, dan alles
#: erin. Anders dan bij de feitentabellen is dat hier de juiste vorm — een
#: winkel die uit de indeling verdwijnt moet ook uit de database verdwijnen
#: (de contractbouw leegt om dezelfde reden eerst de winkels-map), en binnen
#: één transactie bestaat er geen moment waarop een lezer een lege tabel
#: ziet. Faalt de run, dan rolt alles terug en staat het oude contract er
#: nog. Bij ~14 rijen per taal is COPY-met-tijdelijke-tabel overkill.
VERWIJDER_SQL = "delete from public.contract_antwoord"

INVOEG_SQL = (
    "insert into public.contract_antwoord "
    "(scherm, taal, winkel, antwoord, gebouwd_op) "
    "values (%s, %s, %s, %s::jsonb, now())"
)

#: Wat er nu in staat, om te vergelijken met wat we gaan schrijven: de sleutel
#: én de twee velden waarin een antwoord zijn eigen rijkdom opschrijft. De JSON
#: zelf blijft in de database -- een `select antwoord` zou het hele contract
#: over de lijn trekken om er twee lijstjes uit te halen.
BESTAANDE_RIJKDOM_SQL = (
    "select scherm, taal, winkel, "
    "antwoord->'bron', antwoord->'onbeschikbaar' "
    "from public.contract_antwoord"
)


def ontbrekende_sleutels(
    bestaand: set[tuple[str, str, str]], nieuw: set[tuple[str, str, str]]
) -> set[tuple[str, str, str]]:
    """Welke antwoorden er nu wél staan en straks niet meer.

    WAAROM DEZE WACHT BESTAAT. Het schrijven is `delete` gevolgd door `insert`
    in één transactie, en dat is hier de juiste vorm: een winkel die uit de
    indeling verdwijnt, hoort ook uit de database te verdwijnen. Maar diezelfde
    vorm maakt een verarmde bouw gevaarlijk. De nachtelijke sync draait op een
    GitHub-runner, en die heeft `data/config/` niet -- dat staat gitignored en
    alleen op de machine van de bouwer. Bouwt de runner daar een contract
    zonder kostenmodel, dan schrijft hij dat met succes over het goede heen:
    een groene run, en minder cijfers op het scherm. Geen fout, geen melding,
    niemand die het merkt.

    Deze functie is opzettelijk dom en puur: ze vergelijkt sleutels, niet
    inhoud. Verdwijnt er een scherm, een taal of een winkel, dan is dat een
    beslissing die een mens hoort te nemen -- niet iets dat een cron 's nachts
    stilzwijgend doet.

    Sleutels zijn maar de helft van het verhaal; `verarming` hieronder doet de
    andere helft.
    """
    return bestaand - nieuw


# --- de tweede helft van de wacht: dezelfde sleutels, armere inhoud ----------
#
# `ontbrekende_sleutels` vangt het geval waarin er antwoorden verdwijnen. Het
# gevaarlijkere geval is dat er niets verdwijnt: een runner zonder een
# kanaalbron bouwt exact dezelfde zestien sleutels, met exact dezelfde
# schermen, en met één kanaal minder erin. Sleutel voor sleutel is dat contract
# compleet; inhoudelijk is het armer dan wat er stond, en het gaat er
# stilzwijgend overheen.
#
# Wat we daarvoor kunnen gebruiken, staat al in elk antwoord:
#
#   "bron":          welke kanalen dit antwoord gevoed hebben
#   "onbeschikbaar": [{veld, reden}] -- wat dit scherm niet kan tonen
#
# Van die twee is `bron` het scherpe signaal: een kanaal dat gisteren meetelde
# en vandaag niet, kan onmogelijk uit de wereld komen. Historiek verdwijnt niet.
# Zoiets komt uit de bouwomgeving, en dat is precies de fout die we zoeken.
#
# `onbeschikbaar` is grover en mag daarom NIET in zijn geheel gewogen worden.
# De meeste velden daarin dragen een gemeten feit ("geen vergelijking met vorig
# jaar, want vorig jaar telde 2 open dagen"), en die komen en gaan met de
# periode die op het scherm staat. Een wacht die daarop aanslaat, kleurt de
# nachtrun rood op een gewone dinsdag -- en een cron die vaak ten onrechte rood
# staat, is erger dan geen cron, want dan kijkt niemand nog.

#: De velden waarvan de onbeschikbaarheid een ontbrekende INVOER betekent en
#: geen gemeten feit. Alleen deze wegen mee in de wacht.
#:
#: Vandaag staat er één in: zonder kostenmodel klapt het hele margescherm om
#: naar onbeschikbaar, en dat is precies wat er gebeurt wanneer een omgeving de
#: beheerinvoer niet heeft. Wie hier een veld bijzet, hoort zich af te vragen:
#: kan dit veld onbeschikbaar worden doordat de wereld veranderde? Dan hoort
#: het hier niet. Alleen "een invoer die er hoorde te zijn, was er niet".
INPUTGEBONDEN_VELDEN = frozenset({"marge_per_groep"})


@dataclass(frozen=True)
class Rijkdom:
    """Wat een antwoord aan invoer had, samengevat tot twee verzamelingen."""

    bronnen: frozenset[str]
    ontbrekende_invoer: frozenset[str]


@dataclass(frozen=True)
class Verarming:
    """Eén sleutel die armer wordt, met het waarom erbij."""

    sleutel: tuple[str, str, str]
    verloren_bronnen: frozenset[str]
    verloren_invoer: frozenset[str]

    def beschrijf(self) -> str:
        """Eén regel voor de mens die de gefaalde run leest. Geen inhoud."""
        scherm, taal, winkel = self.sleutel
        waar = f"{scherm}/{taal}" + (f"/{winkel}" if winkel else "")
        redenen = []
        if self.verloren_bronnen:
            redenen.append("bron weg: " + ", ".join(sorted(self.verloren_bronnen)))
        if self.verloren_invoer:
            redenen.append(
                "invoer weg: " + ", ".join(sorted(self.verloren_invoer))
            )
        return f"{waar} ({'; '.join(redenen)})"


def rijkdom_uit_velden(bron: object, onbeschikbaar: object) -> Rijkdom:
    """De rijkdom uit de twee velden los, zoals de database ze teruggeeft.

    Alles wat niet de verwachte vorm heeft, telt als leeg in plaats van te
    werpen. Deze functie beoordeelt, ze valideert niet: `_lees_json` heeft de
    JSON al gekeurd, en een antwoord zonder `bron` (de winkelindex heeft er
    geen) is geen fout maar een antwoord zonder bronnen. Zou ze hier wél
    werpen, dan zou één afwijkend antwoord de hele nachtrun tegenhouden om iets
    wat de wacht niet eens meet.
    """
    bronnen = (
        frozenset(b for b in bron if isinstance(b, str))
        if isinstance(bron, list) else frozenset()
    )
    velden = (
        frozenset(
            item["veld"] for item in onbeschikbaar
            if isinstance(item, dict) and isinstance(item.get("veld"), str)
        )
        if isinstance(onbeschikbaar, list) else frozenset()
    )
    return Rijkdom(bronnen, velden & INPUTGEBONDEN_VELDEN)


def rijkdom_uit_json(antwoord: str) -> Rijkdom:
    """Dezelfde samenvatting, maar uit de JSON-tekst van een nieuw antwoord."""
    boom = json.loads(antwoord)
    if not isinstance(boom, dict):
        return Rijkdom(frozenset(), frozenset())
    return rijkdom_uit_velden(boom.get("bron"), boom.get("onbeschikbaar"))


def verarming(
    bestaand: dict[tuple[str, str, str], Rijkdom],
    nieuw: dict[tuple[str, str, str], Rijkdom],
) -> list[Verarming]:
    """Welke antwoorden dezelfde sleutel houden maar armer worden.

    Alleen sleutels die aan beide kanten staan: verdwijnt een sleutel helemaal,
    dan is dat het werk van `ontbrekende_sleutels` en zou hij hier dubbel
    gemeld worden. Rijker worden mag altijd en stilzwijgend -- de eerste nacht
    ná de Deliveroo-historiek hoort geen mens wakker te maken.

    De uitkomst staat op sleutelvolgorde, zodat twee runs op dezelfde stand
    dezelfde melding geven.
    """
    uit = []
    for sleutel in sorted(bestaand.keys() & nieuw.keys()):
        was, wordt = bestaand[sleutel], nieuw[sleutel]
        verloren_bronnen = was.bronnen - wordt.bronnen
        # Nieuw ontbrekende invoer: wat nú ontbreekt en toen niet.
        verloren_invoer = wordt.ontbrekende_invoer - was.ontbrekende_invoer
        if verloren_bronnen or verloren_invoer:
            uit.append(Verarming(sleutel, verloren_bronnen, verloren_invoer))
    return uit
