"""De databaselaag: verbinding, migraties, en het wegschrijven van aggregaten.

Wat hier NIET gebeurt: rekenen. De berekeningslaag produceert de tabellen,
deze laag zet ze weg. Andersom leest het contract eruit. Zodra deze laag
begint te aggregeren, staat dezelfde logica op twee plaatsen en lopen ze uit
elkaar -- dat is precies wat harde regel 4 voorkomt, één laag hoger.
"""
import os


def droge_modus(omgeving: dict | None = None) -> bool:
    """Eén lezing van DROOG voor alle scripts die de database raken.

    Vier scripts lazen deze variabele elk op hun eigen manier, en drie van de
    vier zagen DROOG=0 als "droog" (bool("0") is True). Wie 'DROOG=nee make
    sync' typte, kreeg bovendien een échte sync met dróge substappen: de
    orkestrator las streng ("1"), de kinderen lazen los (truthy). Eén helper,
    één waarheid: alleen 1/ja/true betekent droog.
    """
    waarde = (omgeving or os.environ).get("DROOG", "")
    return waarde.strip().lower() in ("1", "ja", "true")


#: De twee bronnen waaruit het contract en de beheerinvoer kunnen komen. Zelfde
#: paar en zelfde standaard als `platform/lib/contract-bron.ts`; die twee horen
#: gelijk te lopen, want ze beschrijven één omgeving.
BRONNEN = ("bestand", "db")


def contract_bron(omgeving: dict | None = None) -> str:
    """Waar het contract en de beheerinvoer leven: bestanden of de database.

    De spiegel van `contractBron` in `platform/lib/contract-bron.ts`, met
    dezelfde drie regels:

      * zonder de variabele verandert er níéts -- 'bestand', zoals altijd;
      * 'db' zet de leesplek om naar Postgres;
      * elke andere waarde is een configuratiefout en werpt. Stil terugvallen op
        de bestanden zou een verkeerd gezette vlag verzwijgen als een werkende
        run, en op een runner zonder `data/config/` is dat precies het verschil
        tussen een volledig contract en een verarmd contract.

    Waarom de berekeningslaag dit moet weten en niet alleen de UI: het
    kostenmodel is invoer, geen uitvoer. Leest het platform het contract uit de
    database, dan schrijft het formulier de invoer óók daar -- en dan moet de
    contractbouw haar daar ophalen. Zou hij dan nog het bestand lezen, dan
    bestaan er twee kostenmodellen die kunnen uiteenlopen, en toont het
    margescherm cijfers uit het model dat niemand heeft ingevuld.
    """
    bron = (omgeving or os.environ).get("CONTRACT_BRON", "").strip() or "bestand"
    if bron not in BRONNEN:
        raise ValueError(
            f"CONTRACT_BRON={bron} is onbekend (keuze: {', '.join(BRONNEN)}); "
            "zonder de variabele leest de bouw de bestanden."
        )
    return bron
