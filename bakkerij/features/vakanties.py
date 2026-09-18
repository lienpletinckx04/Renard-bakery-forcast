"""Schoolvakanties als verversbare data: het bestand is de waarheid, niet de code.

Het ontwerp is "verversbaar, niet zelfwijzigend" (beslissing 14 augustus 2026):

  * De periodes staan in `schoolvakanties.json`, naast deze module in de repo.
    Het is publieke data — geen klantdata — dus ze mag geversioneerd worden,
    en een verse kloon bouwt zonder netwerk exact dezelfde kalender.
  * `scripts/vakanties_ververs.py` haalt de officiële periodes op bij de
    OpenHolidays-API en past het bestand aan via `vergelijk`/`pas_toe` hier.
  * Nieuwe periodes in de toekomst gaan er automatisch in, gelogd. Elke
    wijziging die het verleden raakt, wordt geweigerd zonder expliciete
    `--forceer`: die verandert de trainingskenmerken en maakt het getoonde
    trackrecord onvergelijkbaar, en dat mag nooit stil gebeuren.

Waarom twee regimes: sinds de hervorming van 2022 lopen de gemeenschappen
niet meer gelijk, en in Elsene leven beide door elkaar. Wélk regime het
koopgedrag stuurt is empirisch beslist (FR, zie E4) maar blijft open punt O10
(vraag 47), dus beide blijven bijgehouden. De Duitstalige Gemeenschap (BE-DE)
is bewust geen kandidaat: geen aanwijsbare klandizie in Elsene.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

VAKANTIES_PAD = Path(__file__).with_name("schoolvakanties.json")

REGIMES = ("VL", "FR")

API_URL = ("https://openholidaysapi.org/SchoolHolidays"
           "?countryIsoCode=BE&languageIsoCode=NL"
           "&validFrom={van}&validTo={tot}")

GROEP_NAAR_REGIME = {"BE-NL": "VL", "BE-FR": "FR"}

#: Korter dan dit is geen vakantieregime maar een losse sluitingsdag (de "Dag
#: van de Gemeenschap" staat als eendagsrecord in de API); langer dan de
#: zomer plus een marge is vrijwel zeker een datafout.
MIN_DAGEN = 5
MAX_DAGEN = 70

#: API-namen naar de korte slugs die als `vakantienaam` in de kalender komen.
#: Een onbekende naam wordt NIET weggegooid maar krijgt een afgeleide slug:
#: een nieuw vakantietype stil laten vallen is precies het soort gat dat dit
#: bestand moet voorkomen.
NAAM_SLUG = {
    "herfstvakantie": "herfst",
    "kerstvakantie": "kerst",
    "krokusvakantie": "krokus",
    "paasvakantie": "paas",
    "zomervakantie": "zomer",
}


@dataclass(frozen=True)
class Periode:
    """Eén vakantieperiode; `van` en `tot` zijn ISO-datums, beide inclusief."""

    naam: str
    van: str
    tot: str
    bron: str | None = None


@dataclass(frozen=True)
class Wijziging:
    """Eén verschil tussen het bestand en wat de bron nu zegt.

    `soort` is "nieuw", "gewijzigd", "hernoemd" of "vervallen".
    `raakt_verleden` betekent: minstens één dag die door deze wijziging van
    vlag verandert, ligt op of vóór vandaag — en dus in het trainingsvenster.
    """

    regime: str
    soort: str
    oud: Periode | None
    nieuw: Periode | None
    raakt_verleden: bool

    @property
    def automatisch(self) -> bool:
        """Mag dit zonder menselijke bevestiging? Hernoemen is cosmetisch
        (het model kijkt alleen naar de vlag, niet naar de naam); al het
        andere alleen als het verleden onaangeroerd blijft. Een vervallen
        periode is altijd handwerk: een officieel geschrapte vakantie is
        zeldzaam genoeg om een mens te verdienen."""
        if self.soort == "hernoemd":
            return True
        if self.soort == "vervallen":
            return False
        return not self.raakt_verleden

    def omschrijving(self) -> str:
        p = self.nieuw or self.oud
        assert p is not None
        basis = f"[{self.regime}] {self.soort}: {p.naam} {p.van} t/m {p.tot}"
        if self.soort in ("gewijzigd", "hernoemd") and self.oud is not None:
            basis += f" (was: {self.oud.naam} {self.oud.van} t/m {self.oud.tot})"
        return basis


def _datum(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _dagen_van(p: Periode) -> set[dt.date]:
    van, tot = _datum(p.van), _datum(p.tot)
    return {van + dt.timedelta(days=i) for i in range((tot - van).days + 1)}


def _overlapt(a: Periode, b: Periode) -> bool:
    return _datum(a.van) <= _datum(b.tot) and _datum(b.van) <= _datum(a.tot)


# -- lezen en valideren -------------------------------------------------------

def lees(pad: Path | None = None) -> dict:
    """Lees en valideer het vakantiebestand. Een kapot of ontbrekend bestand
    is een harde fout: de productieprognose draait op deze data, en stil
    zonder vakanties doorbouwen is erger dan stoppen."""
    pad = pad or VAKANTIES_PAD
    try:
        data = json.loads(pad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(
            f"Vakantiebestand ontbreekt: {pad}. Het hoort in de repo te staan; "
            "herstel het uit git of draai scripts/vakanties_ververs.py."
        ) from None
    except json.JSONDecodeError as fout:
        raise ValueError(f"Vakantiebestand onleesbaar ({pad}): {fout}") from None
    valideer(data)
    return data


def valideer(data: dict) -> None:
    """Structuur en plausibiliteit. Vangt wat een bron- of schrijffout zou
    aanrichten vóór het de kalender in gaat."""
    if not isinstance(data, dict) or "regimes" not in data:
        raise ValueError("Vakantiebestand mist de sleutel 'regimes'.")
    for regime in REGIMES:
        periodes = data["regimes"].get(regime)
        if not isinstance(periodes, list) or not periodes:
            raise ValueError(f"Regime {regime} ontbreekt of is leeg.")
        gezien: list[tuple[dt.date, dt.date]] = []
        namen: set[str] = set()
        for p in periodes:
            try:
                van, tot = _datum(p["van"]), _datum(p["tot"])
                naam = p["naam"]
            except (KeyError, TypeError, ValueError) as fout:
                raise ValueError(f"Onleesbare periode in {regime}: {p!r} "
                                 f"({fout})") from None
            duur = (tot - van).days + 1
            if duur < MIN_DAGEN or duur > MAX_DAGEN:
                raise ValueError(
                    f"{regime}/{naam}: duur {duur} dagen valt buiten "
                    f"[{MIN_DAGEN}, {MAX_DAGEN}] — geen plausibele vakantie."
                )
            if naam in namen:
                raise ValueError(f"{regime}: naam '{naam}' komt tweemaal voor.")
            namen.add(naam)
            for (v2, t2) in gezien:
                if van <= t2 and v2 <= tot:
                    raise ValueError(
                        f"{regime}/{naam}: overlapt met een andere periode "
                        f"({v2} t/m {t2}). Vakanties binnen één regime "
                        "overlappen nooit."
                    )
            gezien.append((van, tot))


def regime_tabel(regime: str, pad: Path | None = None) -> dict[str, tuple[str, str]]:
    """De vorm die `markeer_schoolvakanties` verwacht: naam -> (van, tot)."""
    data = lees(pad)
    return {p["naam"]: (p["van"], p["tot"]) for p in data["regimes"][regime]}


def dekking_tot(tabel: dict[str, tuple[str, str]]) -> dt.date:
    """Tot welke datum de kalender gevuld is. Voorbij deze datum weet de
    prognose niet of een dag vakantie is — de dekkingswacht in de
    contractbouw zegt dat er dan eerlijk bij (harde regel 8)."""
    return max(_datum(tot) for (_, tot) in tabel.values())


# -- schrijven ---------------------------------------------------------------

def schrijf(data: dict, pad: Path | None = None) -> None:
    """Atomair: eerst een tijdelijk bestand, dan os.replace — hetzelfde
    patroon als de contract-JSON's, en om dezelfde reden."""
    pad = pad or VAKANTIES_PAD
    valideer(data)
    tmp = pad.with_name(pad.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, pad)


# -- ophalen bij de bron ------------------------------------------------------

def haal_periodes(van: dt.date, tot: dt.date, *, vandaag: dt.date,
                  ophaler=None) -> dict[str, list[Periode]]:
    """Haal de officiële periodes op en normaliseer ze per regime.

    `vandaag` gaat alleen het bronlabel in. `ophaler` is injecteerbaar voor
    tests: een functie (url) -> geparste JSON. De standaard gaat het netwerk
    op; dat hoort alleen in het ververs-script te gebeuren, nooit tijdens een
    contractbouw of test.
    """
    if ophaler is None:
        def ophaler(url: str):  # pragma: no cover - netwerk
            with urllib.request.urlopen(url, timeout=30) as antwoord:
                return json.loads(antwoord.read().decode("utf-8"))

    # De API weigert vensters van veel jaren in één verzoek (HTTP 400), dus
    # halen we in blokken van hooguit drie jaar en ontdubbelen we op datums —
    # een periode die op een bloknaad ligt, komt in beide blokken terug.
    rauw: list[dict] = []
    gezien_ids: set[tuple[str, str, str]] = set()
    blok_van = van
    while blok_van <= tot:
        blok_tot = min(tot, dt.date(blok_van.year + 3, blok_van.month,
                                    blok_van.day) - dt.timedelta(days=1))
        for record in ophaler(API_URL.format(van=blok_van.isoformat(),
                                             tot=blok_tot.isoformat())):
            sleutel = (record.get("id", ""), record["startDate"], record["endDate"])
            if sleutel not in gezien_ids:
                gezien_ids.add(sleutel)
                rauw.append(record)
        blok_van = blok_tot + dt.timedelta(days=1)
    bronlabel = f"openholidaysapi.org, opgehaald {vandaag.isoformat()}"

    per: dict[str, list[Periode]] = {r: [] for r in REGIMES}
    for record in rauw:
        start, eind = record["startDate"], record["endDate"]
        duur = (_datum(eind) - _datum(start)).days + 1
        if duur < MIN_DAGEN:
            continue  # losse sluitingsdag, geen regime
        api_naam = record["name"][0]["text"].strip().lower()
        slug = NAAM_SLUG.get(api_naam,
                             api_naam.replace("vakantie", "").replace(" ", "_")
                             or "vakantie")
        naam = f"{slug}_{start[:4]}"
        for groep in record.get("groups") or []:
            regime = GROEP_NAAR_REGIME.get(groep.get("code", ""))
            if regime is not None:
                per[regime].append(Periode(naam, start, eind, bron=bronlabel))

    for regime, lijst in per.items():
        lijst.sort(key=lambda p: p.van)
        # Zelfde slug tweemaal in één jaar (komt voor bij rare bronrecords):
        # nummer de tweede, want valideer eist unieke namen.
        gezien: dict[str, int] = {}
        genummerd = []
        for p in lijst:
            teller = gezien.get(p.naam, 0)
            gezien[p.naam] = teller + 1
            genummerd.append(p if teller == 0 else
                             Periode(f"{p.naam}_{teller + 1}", p.van, p.tot, p.bron))
        per[regime] = genummerd
    return per


# -- vergelijken en toepassen -------------------------------------------------

def vergelijk(oud: list[Periode], nieuw: list[Periode], *, regime: str,
              vandaag: dt.date, venster_van: dt.date,
              venster_tot: dt.date) -> list[Wijziging]:
    """Wat zegt de bron anders dan het bestand? Periodes worden gekoppeld op
    datumoverlap, niet op naam: de namen zijn cosmetisch en mogen wijzigen
    zonder dat dat als inhoudelijke wijziging telt.

    Een bestaande periode geldt pas als "vervallen" wanneer ze binnen het
    opgevraagde venster ÉN binnen de aantoonbare dekking van de bron ligt
    (van de vroegste tot de laatste teruggekregen periode). De API heeft
    bijvoorbeeld niets vóór eind 2019: dat een handmatig aangevulde periode
    daar niet terugkomt, zegt niets — afwezigheid telt alleen waar de bron
    in de buurt wél aanwezig is.
    """
    wijzigingen: list[Wijziging] = []
    resterend = list(oud)
    if nieuw:
        venster_van = max(venster_van, min(_datum(n.van) for n in nieuw))
        venster_tot = min(venster_tot, max(_datum(n.tot) for n in nieuw))
    else:
        # Een lege bron mag nooit het hele bestand als "vervallen" bestempelen.
        venster_tot = venster_van - dt.timedelta(days=1)
    for n in nieuw:
        partner = next((o for o in resterend if _overlapt(o, n)), None)
        if partner is None:
            raakt = _datum(n.van) <= vandaag
            wijzigingen.append(Wijziging(regime, "nieuw", None, n, raakt))
            continue
        resterend.remove(partner)
        if (partner.van, partner.tot) == (n.van, n.tot):
            if partner.naam != n.naam:
                wijzigingen.append(Wijziging(regime, "hernoemd", partner, n, False))
            continue
        verschoven = _dagen_van(partner) ^ _dagen_van(n)
        raakt = any(d <= vandaag for d in verschoven)
        wijzigingen.append(Wijziging(regime, "gewijzigd", partner, n, raakt))

    for o in resterend:
        if venster_van <= _datum(o.van) and _datum(o.tot) <= venster_tot:
            raakt = _datum(o.van) <= vandaag
            wijzigingen.append(Wijziging(regime, "vervallen", o, None, raakt))
    return wijzigingen


def pas_toe(oud: list[Periode], wijzigingen: list[Wijziging], *,
            forceer: bool = False) -> tuple[list[Periode], list[Wijziging],
                                            list[Wijziging]]:
    """Pas toe wat mag; geef terug (nieuwe lijst, toegepast, geweigerd).

    Zonder `forceer` gaat alleen door wat `Wijziging.automatisch` toestaat.
    De teruggegeven lijst is gesorteerd op begindatum.
    """
    periodes = list(oud)
    toegepast: list[Wijziging] = []
    geweigerd: list[Wijziging] = []
    for w in wijzigingen:
        if not (w.automatisch or forceer):
            geweigerd.append(w)
            continue
        if w.oud is not None:
            periodes = [p for p in periodes
                        if (p.van, p.tot) != (w.oud.van, w.oud.tot)]
        if w.nieuw is not None:
            periodes.append(w.nieuw)
        toegepast.append(w)
    periodes.sort(key=lambda p: p.van)
    return periodes, toegepast, geweigerd


def naar_json(periodes: list[Periode]) -> list[dict]:
    """Periodes terug naar de bestandsvorm; `bron` alleen als hij er is."""
    uit = []
    for p in periodes:
        rij = {"naam": p.naam, "van": p.van, "tot": p.tot}
        if p.bron:
            rij["bron"] = p.bron
        uit.append(rij)
    return uit


def uit_json(rijen: list[dict]) -> list[Periode]:
    return [Periode(r["naam"], r["van"], r["tot"], r.get("bron")) for r in rijen]
