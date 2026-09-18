"""Het ophalen en de configuratie van de optionele agendafeed (iCal).

Dit is de tweede helft van het agendaspoor uit vraag 46: `agenda.py` leest een
iCal-tekst, dit bestand haalt die tekst op en zegt waar hij vandaan komt. De
splitsing is opzet — alles wat rekent staat in een module zonder netwerk, en
alles wat het netwerk raakt staat hier en levert nooit meer dan tekst af.

VIER EIGENSCHAPPEN DIE DEZE LAAG ONSCHADELIJK MAKEN

1. *Zonder configuratie doet ze niets.* `AGENDA_ICS_URL` leeg of afwezig, of
   zelfs helemaal geen `.env`, betekent één `Agenda` met `bruikbaar=False` en
   een reden in gewone taal. Geen uitzondering, geen lege feed die als "open"
   gelezen wordt, geen halve gok.

2. *Ze faalt netjes.* Onbereikbaar, 404, een inlogpagina in plaats van een
   agenda, een bestand dat geen UTF-8 is: elk daarvan wordt één onbruikbare
   `Agenda` met de reden erbij. De nachtelijke keten loopt door. Wat we níét
   opvangen is een fout in onze eigen code — die hoort luidruchtig te crashen
   (de les van O18).

3. *De link is een geheim.* Een geheime iCal-link is een wachtwoord: wie hem
   heeft, leest de agenda. Hij staat daarom in `.env` en nergens anders, en hij
   komt nooit in een foutmelding terecht — voor logregels bestaat `kort_adres()`,
   dat alleen schema en host toont. Alleen `http` en `https` zijn toegestaan,
   zodat een verkeerd geplakte waarde nooit een lokaal bestand kan lezen.

4. *Ze hangt aan niets.* Deze module importeert alleen `agenda.py` en de
   standaardbibliotheek, en niets in `bakkerij/` importeert haar. Wijst de
   klant vraag 46 af, dan is het opruimen: twee bestanden in `bakkerij/sources/`,
   twee testbestanden, één make-doel en één regel in `.env.example`.

Waarom hier een eigen `.env`-lezer staat en niet die van `odoo_client`: daar is
een ontbrekende `.env` fataal (`SystemExit`), en dat is voor Odoo juist goed.
Hier is een ontbrekende `.env` de normale toestand zolang vraag 46 openstaat.
Hetzelfde mechanisme — sleutels in `.env` in de repo-root — met een andere
afloop.
"""

from __future__ import annotations

import http.client
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bakkerij.sources.agenda import Agenda, lees_ics

REPO = Path(__file__).resolve().parents[2]

SLEUTEL = "AGENDA_ICS_URL"
STANDAARD_TIMEOUT = 20.0
MAX_BYTES = 5_000_000
TOEGESTANE_SCHEMAS = ("http", "https")
AGENT = "asklien-bakkerij/1.0 (agendalaag)"


@dataclass(frozen=True)
class Instelling:
    """Waar de feed staat, en waar we dat vandaan hebben.

    `herkomst` is er voor de mens die zich afvraagt waarom de laag wél of niet
    draait: een sleutel in de omgeving en een sleutel in `.env` geven hetzelfde
    resultaat maar een heel ander gesprek.
    """

    url: str = ""
    herkomst: str = "nergens ingesteld"

    @property
    def ingesteld(self) -> bool:
        return bool(self.url)


def _zonder_aanhalingstekens(waarde: str) -> str:
    if len(waarde) >= 2 and waarde[0] == waarde[-1] and waarde[0] in "\"'":
        return waarde[1:-1]
    return waarde


def lees_env_bestand(pad: Path) -> dict[str, str]:
    """Lees `SLEUTEL=waarde` uit een .env-bestand. Geen bestand is geen sleutels.

    Onleesbaar of geen tekst telt hier als afwezig: dit is een optionele laag en
    een kapotte `.env` mag geen enkele andere stap tegenhouden. Wat er wél toe
    doet, meldt de laag verderop als reden.
    """
    if not pad.exists():
        return {}
    try:
        tekst = pad.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    uit: dict[str, str] = {}
    for ruwe in tekst.splitlines():
        regel = ruwe.strip()
        if not regel or regel.startswith("#") or "=" not in regel:
            continue
        naam, _, waarde = regel.partition("=")
        uit[naam.strip()] = _zonder_aanhalingstekens(waarde.strip())
    return uit


def lees_instelling(omgeving: Mapping[str, str] | None = None,
                    env_pad: Path | None = None) -> Instelling:
    """De omgevingsvariabele wint van `.env`, zoals overal in dit project."""
    omgeving = os.environ if omgeving is None else omgeving
    env_pad = (REPO / ".env") if env_pad is None else env_pad

    uit_omgeving = (omgeving.get(SLEUTEL) or "").strip()
    if uit_omgeving:
        return Instelling(url=uit_omgeving, herkomst=f"omgevingsvariabele {SLEUTEL}")

    uit_bestand = lees_env_bestand(env_pad).get(SLEUTEL, "").strip()
    if uit_bestand:
        return Instelling(url=uit_bestand, herkomst=f"{SLEUTEL} in {env_pad.name}")

    return Instelling()


def normaliseer_url(url: str) -> str:
    """`webcal://` is https met een andere jas aan.

    Apple en Outlook geven hun abonneerlink vaak als `webcal://` uit, en Google
    biedt hem naast de `https`-variant ook zo aan. Dat is dezelfde HTTPS-URL;
    de klant een schema laten omtypen is een foutbron zonder opbrengst.
    """
    schoon = url.strip()
    if schoon.lower().startswith("webcal://"):
        return "https://" + schoon[len("webcal://"):]
    return schoon


def reden_url_geweigerd(url: str) -> str:
    """Lege tekst betekent: hier mag over het net op af. Anders de reden waarom niet."""
    ontleed = urllib.parse.urlsplit(url)
    schema = ontleed.scheme.lower()
    if schema not in TOEGESTANE_SCHEMAS:
        gevonden = schema or "geen"
        return (f"{SLEUTEL} moet met http:// of https:// beginnen "
                f"(schema in de instelling: {gevonden})")
    if not ontleed.netloc:
        return f"{SLEUTEL} bevat geen hostnaam"
    return ""


def kort_adres(url: str) -> str:
    """Schema en host, zonder het geheime pad. Het enige dat naar een log mag."""
    ontleed = urllib.parse.urlsplit(normaliseer_url(url))
    if not ontleed.netloc:
        return "(geen geldig adres)"
    return f"{ontleed.scheme}://{ontleed.hostname or ontleed.netloc}/…"


def haal_tekst(url: str, timeout: float = STANDAARD_TIMEOUT,
               max_bytes: int = MAX_BYTES) -> tuple[str, str]:
    """(tekst, reden_mislukt). Precies één van de twee is gevuld.

    Elke `except` hieronder vangt een fout die het net echt maakt. Een
    `TypeError` uit onze eigen code valt er niet onder en crasht dus, en dat is
    de bedoeling: een stille agendalaag die eigenlijk stuk is, is erger dan een
    keten die valt.
    """
    verzoek = urllib.request.Request(
        url, headers={"User-Agent": AGENT, "Accept": "text/calendar, text/plain"})
    try:
        # Het schema is hierboven al op http/https gecontroleerd; urlopen kan
        # hier dus geen file:// of ftp:// openen.
        with urllib.request.urlopen(verzoek, timeout=timeout) as antwoord:
            # Eén byte meer dan toegestaan lezen is genoeg om te weten dat het
            # er te veel zijn, zonder de rest binnen te halen.
            ruw = antwoord.read(max_bytes + 1)
            charset = antwoord.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as fout:
        return "", f"De agenda antwoordde met HTTP {fout.code} ({fout.reason})"
    except urllib.error.URLError as fout:
        return "", f"De agenda is niet bereikbaar: {fout.reason}"
    except TimeoutError:
        return "", f"De agenda antwoordde niet binnen {timeout:g} seconden"
    except http.client.HTTPException as fout:
        return "", f"De verbinding met de agenda brak af: {type(fout).__name__}"

    if len(ruw) > max_bytes:
        return "", (f"Het opgehaalde bestand is groter dan {max_bytes} bytes; "
                    "dit lijkt geen agenda te zijn")
    try:
        return ruw.decode(charset), ""
    except LookupError:
        return "", f"De agenda meldt een tekenset die we niet kennen ({charset})"
    except UnicodeDecodeError:
        return "", f"Het opgehaalde bestand is geen leesbare tekst ({charset})"


def agenda_uit_tekst(tekst: str) -> Agenda:
    """De poortwachter vóór de parser: is dit überhaupt een iCal-bestand?

    Zonder deze controle levert een inlogpagina of een foutpagina met status 200
    dezelfde melding op als een lege agenda, en dat zijn twee heel verschillende
    problemen voor wie het moet oplossen.
    """
    if "BEGIN:VCALENDAR" not in tekst.upper():
        return Agenda(
            bruikbaar=False,
            reden_onbruikbaar=("Wat er op dat adres staat is geen iCal-bestand "
                               "(geen BEGIN:VCALENDAR); klopt de link nog?"))
    return lees_ics(tekst)


def haal_agenda_en_tekst(instelling: Instelling | None = None,
                         timeout: float = STANDAARD_TIMEOUT,
                         max_bytes: int = MAX_BYTES) -> tuple[Agenda, str]:
    """De hele keten in één aanroep: (agenda, ruwe iCal-tekst).

    De ruwe tekst komt mee zodat wie hem wil bewaren de agenda niet een tweede
    keer hoeft te bevragen. Mislukt het ophalen, dan is de tekst leeg en zegt de
    agenda waarom.
    """
    instelling = lees_instelling() if instelling is None else instelling
    if not instelling.ingesteld:
        return Agenda(
            bruikbaar=False,
            reden_onbruikbaar=(f"{SLEUTEL} is niet ingesteld; de agendalaag "
                               "doet niets")), ""

    url = normaliseer_url(instelling.url)
    geweigerd = reden_url_geweigerd(url)
    if geweigerd:
        return Agenda(bruikbaar=False, reden_onbruikbaar=geweigerd), ""

    tekst, mislukt = haal_tekst(url, timeout=timeout, max_bytes=max_bytes)
    if mislukt:
        return Agenda(bruikbaar=False, reden_onbruikbaar=mislukt), ""
    return agenda_uit_tekst(tekst), tekst


def haal_agenda(instelling: Instelling | None = None,
                timeout: float = STANDAARD_TIMEOUT,
                max_bytes: int = MAX_BYTES) -> Agenda:
    """Geeft altijd een `Agenda` terug, nooit een fout.

    Geen configuratie, een kapotte link, een onbereikbare server of een bestand
    dat geen agenda is: allemaal een `Agenda` met `bruikbaar=False` en een reden.
    Die reden is geschreven om letterlijk aan de klant te tonen — daarom staat
    het geheime adres er niet in.
    """
    return haal_agenda_en_tekst(instelling, timeout=timeout, max_bytes=max_bytes)[0]
