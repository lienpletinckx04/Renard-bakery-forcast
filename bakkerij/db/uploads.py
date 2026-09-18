"""De postbus lezen en haar rijen afvinken.

WAAROM DIT BESTAAT

Migratie 015 zette `bron_upload` neer: een beheerder legt via het platform een
export neer, en de bytes blijven daar staan tot iemand ze ophaalt. Dat
"iemand" is deze laag. Het platform ontleedt niets — het kent de vorm van een
Deliveroo-export niet en hoort die ook niet te kennen — dus alles wat na het
opladen komt, gebeurt hier.

WAT HIER NIET GEBEURT

Ontleden. Deze module haalt bytes op en schrijft een uitkomst terug; wat er in
die bytes staat, weet `bakkerij/sources/`. Zou hier ook maar één kolom gelezen
worden, dan bestond de kennis van de exportvorm op twee plaatsen — dezelfde
reden waarom `bevroren.py` niets herberekent.

HET ONDERSCHEID DAT ER ECHT TOE DOET

Een bestand dat we nog NIET KUNNEN lezen is iets anders dan een bestand dat
STUK is. Het eerste is onze schuld en gaat over met de tijd (de parser voor
dit formaat is nog niet gebouwd); het tweede is een eigenschap van het bestand
en gaat nooit meer over. Alleen het tweede wordt afgevinkt als 'mislukt'.

Het eerste blijft onaangeroerd in de wachtrij staan, want de dag dat de parser
er wél is, hoort dat bestand gewoon verwerkt te worden — zonder dat iemand
eerst een kolom moet terugzetten die een eerdere run per ongeluk heeft
ingevuld. Wie dat verschil niet maakt, bouwt een postbus die zichzelf leegt
door alles wat ze niet begrijpt als kapot te bestempelen.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

#: De bronnen waarvan de postbus iets kan bevatten. Spiegelt de check op
#: `bron_upload.bron` in migratie 015. Lopen die twee uit elkaar, dan vraagt de
#: inlaadlaag naar een bron die de database niet kent, of laat de database er
#: een toe die niemand ophaalt. `tests/test_uploads.py` bewaakt dat ze gelijk
#: blijven, want het is precies het soort verschil dat pas opvalt wanneer
#: iemand het voor het eerst nodig heeft.
BRONNEN = ("deliveroo",)

#: De stapnaam waarmee het leegmaken zich in `etl_run` boekhoudt. Toegestaan
#: sinds migratie 016; zonder die migratie breekt `laden.start_run` de
#: transactie op zijn eerste regel. Dat is dezelfde fout die 013 al eens voor
#: `kostenmodel` moest repareren, en de test hieronder bestaat om te voorkomen
#: dat ze een derde keer gemaakt wordt.
ETL_BRON = "uploads"

#: De wachtrij van één bron, oudste eerst. De inhoud zit hier NIET bij: die is
#: groot en een lijst opvragen hoort geen megabytes over de lijn te trekken.
#: De index `bron_upload_onverwerkt_idx` (015) draagt precies deze vraag.
ONVERWERKT_SQL = """
select upload_id, bron, bestandsnaam, mediatype, bytes, sha256,
       geladen_door, geladen_op
  from public.bron_upload
 where bron = %s
   and verwerkt_op is null
 order by geladen_op, upload_id
"""

#: Alles van één bron, verwerkt of niet -- voor het overzicht op de
#: opdrachtregel. Ook hier zonder de inhoud.
ALLES_SQL = """
select upload_id, bron, bestandsnaam, mediatype, bytes, sha256,
       geladen_door, geladen_op, verwerkt_op, verwerkt_status, verwerkt_reden
  from public.bron_upload
 where bron = %s
 order by geladen_op desc, upload_id desc
"""

INHOUD_SQL = "select inhoud from public.bron_upload where upload_id = %s"

AFVINK_SQL = """
update public.bron_upload
   set verwerkt_op = now(),
       verwerkt_status = %s,
       verwerkt_reden = %s
 where upload_id = %s
   and verwerkt_op is null
"""

#: Wat `verwerkt_status` mag dragen; de check in 015 dwingt hetzelfde af.
STATUSSEN = ("gelukt", "mislukt")

#: Hoeveel tekens van een foutmelding er in `verwerkt_reden` passen. Die kolom
#: is leesbaar voor elke ingelogde gebruiker, net als `etl_run.melding`, dus
#: hier hoort een reden in en nooit een datarij. De grens is er omdat een
#: pandas- of psycopg-fout een halve tabel kan meedragen.
MAX_REDEN = 500


@dataclass(frozen=True)
class Upload:
    """Eén rij uit de postbus, zonder de bytes."""

    upload_id: int
    bron: str
    bestandsnaam: str
    mediatype: str
    bytes: int
    sha256: str
    geladen_door: str
    geladen_op: dt.datetime
    verwerkt_op: dt.datetime | None = None
    verwerkt_status: str | None = None
    verwerkt_reden: str = ""

    @property
    def verwerkt(self) -> bool:
        return self.verwerkt_op is not None


def _naar_upload(rij) -> Upload:
    return Upload(*rij)


def lees_onverwerkt(verbinding, bron: str) -> list[Upload]:
    """De wachtrij van één bron, oudste eerst.

    Leeg is hier een gewone uitkomst en geen fout: een postbus die niets bevat,
    is een postbus waar niemand iets in gelegd heeft. Anders dan bij
    `bevroren.lees_verkopen`, waar leeg betekent dat een heel kanaal verdwenen
    is, valt hier niets weg.
    """
    with verbinding.cursor() as cur:
        cur.execute(ONVERWERKT_SQL, (bron,))
        return [_naar_upload(r) for r in cur.fetchall()]


def lees_alles(verbinding, bron: str) -> list[Upload]:
    """Alles van één bron, jongste eerst -- voor het overzicht."""
    with verbinding.cursor() as cur:
        cur.execute(ALLES_SQL, (bron,))
        return [_naar_upload(r) for r in cur.fetchall()]


def lees_inhoud(verbinding, upload_id: int) -> bytes:
    """De bytes van één oplading, apart opgehaald.

    Apart, omdat een overzicht van twintig opladingen anders twintig bestanden
    over de lijn trekt om twintig namen te kunnen tonen.
    """
    with verbinding.cursor() as cur:
        cur.execute(INHOUD_SQL, (upload_id,))
        rij = cur.fetchone()
    if rij is None:
        raise ValueError(f"oplading {upload_id} bestaat niet")
    return bytes(rij[0])


def vink_af(
    verbinding, upload_id: int, status: str, reden: str = "",
) -> bool:
    """Zet de uitkomst van een verwerking, en geef terug of dat iets deed.

    `False` betekent dat de rij al afgevinkt was. Dat is geen fout maar een
    wedloop: twee runs die tegelijk dezelfde wachtrij leegmaken. De `where
    verwerkt_op is null` in de query zorgt dat de tweede niets overschrijft, en
    de aanroeper hoort te weten dat zijn werk niet geteld heeft.

    Er wordt hier NIET gecommit. Het afvinken hoort in dezelfde transactie te
    zitten als wat er met het bestand gebeurd is; committen op twee plaatsen
    levert een bestand op dat verwerkt heet zonder dat het resultaat er staat.
    """
    if status not in STATUSSEN:
        raise ValueError(
            f"status moet een van {STATUSSEN} zijn, niet {status!r}"
        )
    kort = (reden or "").strip()[:MAX_REDEN]
    with verbinding.cursor() as cur:
        cur.execute(AFVINK_SQL, (status, kort, upload_id))
        return cur.rowcount == 1


# --- de wachtrij aflopen ----------------------------------------------------
#
# De lus staat hier en niet in `scripts/uploads_verwerk.py`, om dezelfde reden
# als overal in deze repo: een script is niet te testen zonder het te draaien,
# en wat niet getest is, werkt alleen bij wie het geschreven heeft. Het script
# eromheen doet de opdrachtregel, de afdruk en de etl_run-boekhouding.

#: Wat `verwerk_een` kan teruggeven. `nog-niet-leesbaar` is geen mislukking:
#: zie de moduletekst hierboven.
GELUKT = "gelukt"
MISLUKT = "mislukt"
NOG_NIET_LEESBAAR = "nog-niet-leesbaar"

#: Alles wat geen letter, cijfer, punt, streepje of liggend streepje is, gaat
#: eruit. De naam is bij het opladen al gecontroleerd, maar een bestandsnaam
#: die uit een database rechtstreeks een pad in loopt, is precies het soort
#: vertrouwen dat je geen twee lagen diep wil hebben.
_ONVEILIG = re.compile(r"[^A-Za-z0-9._-]+")


def veilige_naam(bestandsnaam: str, upload_id: int) -> str:
    """Een bestandsnaam die gegarandeerd binnen zijn map blijft.

    Het id gaat ervoor, zodat twee opladingen met dezelfde naam elkaar niet
    overschrijven en de bestanden op schijf in de volgorde staan waarin ze
    binnenkwamen.
    """
    kaal = _ONVEILIG.sub("_", bestandsnaam.strip()).strip("._-")
    return f"{upload_id:06d}_{kaal or 'zonder-naam'}"


def verwerk_een(verbinding, upload: Upload, lezers: dict) -> str:
    """Verwerkt één oplading en vinkt haar af waar dat hoort.

    Committeert per bestand. Een run die halverwege sterft hoort het werk te
    behouden dat al af was, en niet alles terug te draaien omdat het laatste
    bestand stuk bleek.

    De drie uitkomsten zijn niet symmetrisch, en dat is de kern van deze
    functie. `gelukt` en `mislukt` halen de rij uit de wachtrij;
    `nog-niet-leesbaar` laat haar met rust, want dat zegt iets over ons en
    niet over het bestand.
    """
    lezer = lezers.get(upload.bron)
    if lezer is None:
        return NOG_NIET_LEESBAAR

    try:
        inhoud = lees_inhoud(verbinding, upload.upload_id)
        regels = lezer(inhoud, upload)
    except NotImplementedError:
        verbinding.rollback()
        return NOG_NIET_LEESBAAR
    except Exception as fout:  # noqa: BLE001 -- de reden hoort in de kolom
        verbinding.rollback()
        vink_af(verbinding, upload.upload_id, MISLUKT,
                f"{type(fout).__name__}: {fout}")
        verbinding.commit()
        return MISLUKT

    vink_af(verbinding, upload.upload_id, GELUKT, f"{regels} regels")
    verbinding.commit()
    return GELUKT


def verwerk_wachtrij(
    verbinding, bron: str, lezers: dict,
) -> list[tuple[Upload, str]]:
    """Loopt de wachtrij van één bron af en geeft de uitkomst per oplading.

    Afdrukken gebeurt hier niet: deze functie geeft terug wat er gebeurd is en
    de aanroeper beslist hoe dat eruitziet. Zo is ze te testen zonder de
    uitvoer te moeten lezen.
    """
    return [
        (upload, verwerk_een(verbinding, upload, lezers))
        for upload in lees_onverwerkt(verbinding, bron)
    ]
