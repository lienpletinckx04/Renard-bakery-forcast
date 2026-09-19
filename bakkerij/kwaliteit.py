"""De datakwaliteitslaag en de dodemansknop: weet het platform of het nog leeft? (B6, O14/O15)

De nachtelijke run is best-effort. Zonder deze laag merkt niemand dat het
platform stilstaat: de schermen blijven gewoon de laatst geladen cijfers tonen,
en dat ziet er identiek uit aan een platform dat werkt. Deze module levert twee
soorten antwoord, allebei als pure functies (DataFrames in, dataclasses uit,
geen I/O), zodat de contractlaag er later een zesde antwoord `stand` van maakt:

  bronstanden  per bron (odoo-kassa, deliveroo): wanneer kwam er voor het
               laatst iets binnen, en is dat erg? — de dodemansknop (O14)
  wachters     controles op de data zelf: dubbele sleutels, negatieve waarden,
               gaten in de reeks, kalenderdekking, drempelranden (O15), en op
               bon- en uurniveau de bonnen-omzetdekking en de censurerings-
               drempel (O23)

DE KERNREGEL van de dodemansknop: een alarm dat vier weken zomersluiting lang
afgaat, is op de dag van de echte storing onzichtbaar geworden. Daarom slaat
'stil' alleen aan wanneer de kalender zegt dat de winkel open hoorde te zijn.
De kalender draagt daarvoor het onderscheid uit canoniek.bouw_kalender:

  winkel_gemeten=True,  winkel_open=False   gemeten en gesloten: geen meting
                                            verwacht, dus geen alarm ('gesloten')
  winkel_gemeten=True,  winkel_open=True    het gemeten patroon zegt open: een
                                            dag zonder één ingeladen rij is hier
                                            een echt alarm ('stil')
  winkel_gemeten=False, gepland_dicht=True  vooraf als gesloten aangekondigd:
                                            niet gemeten, maar wél verklaard.
                                            Geen alarm ('gesloten')
  winkel_gemeten=False, gepland_dicht=False buiten het gemeten bereik en door
                                            geen bron verklaard; 'niet
                                            ingeladen' is daar de juiste
                                            lezing, en te veel van zulke dagen
                                            heet 'achter' — nooit 'stil'

Een kalender die vers uit bouw_kalender komt op dezelfde verkopen kan de
stil-combinatie ná de laatste meetdag niet opleveren (winkel_open vergt daar
verkoop). De combinatie ontstaat wél zodra de kalender uit de database komt en
de verse inlaad leeg blijft — precies de storing die deze knop moet zien.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal

import pandas as pd

from bakkerij import censurering
from bakkerij.berekening import euro
from bakkerij.canoniek import (
    DELIVEROO_REDEN,
    DELIVEROO_REDEN_FR,
    DREMPEL_OPEN,
    MIN_DAGEN_PER_WEEKDAG,
    _als_datum,
    _gepland_dicht_per_dag,
    _status_per_dag,
)
from bakkerij.taal import kanaalnaam, procent_tekst, t

#: kanaal in het canonieke model -> naam van de bron die het levert.
BRONNEN = (("winkel", "odoo-kassa"), ("deliveroo", "deliveroo"))

#: Bronnen waarvan we wéten dat ze er nog niet zijn (open punt O2/G4). Hun
#: 'ontbreekt' is zichtbaar in het bronnenlijstje mét reden, maar telt niet mee
#: in 'ergste': een alarm dat permanent afgaat, is geen alarm (de kernregel).
#:
#: OP DE DAG DAT DELIVEROO GELADEN WORDT, VERHUIST HET KANAAL HIERUIT NAAR
#: `BEVROREN` HIERONDER -- in dezelfde commit, niet erna. Beide regels, niet
#: één. Waarom dat geen detail is: de ingestmailbox is op 17 augustus 2026
#: geschrapt, dus ook Deliveroo krijgt geen automatische aanvoer; de historiek
#: komt uit een handmatige download en staat daarna stil. Blijft het kanaal
#: hier staan, dan wordt zijn achterstand nooit gemeld terwijl er wél data is.
#: Haal je het hier weg zonder het in `BEVROREN` te zetten, dan valt het
#: kanaal in `bronstanden` niet in de bevroren tak maar in `_stand_dagelijks`,
#: en dat is de strengste lat die er is: MAX_ONGEMETEN_DAGEN staat op twee. Twee
#: dagen na de laatste geladen dag staat het kanaal dus 'achter', voorgoed, op
#: een bron die per definitie niet dagelijks bijkomt.
#:
#: Er is nog een tweede reden waarom `_stand_dagelijks` hier niet past: die
#: wachter verklaart ongemeten dagen aan de hand van de WINKELkalender
#: (winkel_open, gepland_dicht). Een bezorgplatform hoeft de openingsdagen van
#: de toog niet te volgen, dus die verklaring zou niet eens opgaan.
#:
#: Wordt er wél een periodieke Hub-download afgesproken (maandelijks of per
#: kwartaal, via het uploadscherm), dan is dat een derde mogelijkheid en geen
#: variant op de twee hierboven: het kanaal hoort in géén van beide lijsten,
#: want het is niet afwezig en het is niet bevroren — er komt gewoon periodiek
#: iets bij. ZO ZET JE DIE AAN: één regel in `ACHTER_DAGEN_PER_KANAAL` met de
#: eigen drempel, in de orde van 90 dagen. Dat is genoeg en er hoort niets
#: anders bij: `bronstanden` routeert op de vereniging van `BEVROREN` en de
#: sleutels van die tabel, dus een kanaal met een eigen lat komt vanzelf in
#: `_stand_periodiek` en nooit in `_stand_dagelijks`. Vergeet je die regel, dan
#: valt het alsnog in de dagelijkse tak — dezelfde val als hierboven.
#:
#: Zie `docs/beslissingen.md`, 25 augustus 2026.
#:
#: 19 SEPTEMBER 2026: DELIVEROO IS HIER WEG EN STAAT IN `ACHTER_DAGEN_PER_KANAAL`.
#: De derde mogelijkheid hierboven is werkelijkheid geworden: de historiek is
#: aangeleverd (23 Partner Hub-downloads, sep 2025 t/m sep 2026) en het kanaal
#: komt voortaan periodiek bij via het uploadscherm. Precies zoals hierboven
#: beschreven: één regel in die tabel, niets anders. De lijst blijft bestaan,
#: leeg, voor de volgende bron die wél bekend afwezig is.
BEKEND_AFWEZIG: tuple[str, ...] = ()

#: Bronnen die niet meer aangevuld wórden, en dus niet tegen de klok gemeten
#: mogen worden. De keerzijde van BEKEND_AFWEZIG: die bron kwam nooit, deze
#: komt niet meer.
#:
#: Vandaag leeg: er is geen kanaal in deze toestand. DELIVEROO KOMT HIER BIJ op
#: de dag dat het kanaal geladen wordt, en verdwijnt dan uit `BEKEND_AFWEZIG`
#: hierboven — om dezelfde reden: de ingestmailbox is geschrapt, dus de
#: historiek komt uit een handmatige Partner Hub-download en staat daarna
#: stil. De volledige afweging, inclusief de derde mogelijkheid (een
#: periodieke download, en dan hoort het kanaal in geen van beide lijsten),
#: staat bij `BEKEND_AFWEZIG`.
#:
#: DEZE LIJST ROUTEERT MEE: `bronstanden` stuurt een kanaal dat hier staat naar
#: `_stand_bevroren`. Een kanaal daar krijgt géén achterstandsalarm meer, wat
#: blijft is zijn jongste meetdag en de reden in het bronnenlijstje.
BEVROREN = ()

#: Zoveel dagen zonder meting en zonder kalenderverklaring mag een dagelijkse
#: bron achterlopen voor hij 'achter' heet. Twee, niet nul: de nachtelijke run
#: laadt gisteren, en één haperende nacht is nog geen storing.
MAX_ONGEMETEN_DAGEN = 2

#: De terugvallat voor een periodiek kanaal zonder eigen regel in
#: `ACHTER_DAGEN_PER_KANAAL`. Een maandritme is de voorzichtige keuze — het is
#: het enige aanleverritme dat we ooit gemeten hebben, en een strengere
#: terugval zou achterstand melden die er niet is.
STANDAARD_ACHTER_DAGEN = 45

#: De lat per kanaal, voor de bronnen die niet dagelijks bijkomen. DEZE TABEL
#: ROUTEERT MEE, en dat is haar tweede reden van bestaan: `bronstanden` stuurt
#: elk kanaal dat hier staat naar `_stand_periodiek` en nooit naar
#: `_stand_dagelijks`. Eén regel erbij is dus genoeg om een kanaal uit de
#: dagelijkse tak te houden — en die tak is de val: MAX_ONGEMETEN_DAGEN staat
#: op twee, en dat is een permanent 'achter' op een bron die per definitie niet
#: dagelijks bijkomt (zie `BEKEND_AFWEZIG` voor het hele verhaal).
#:
#: Een tabel en geen losse constante per kanaal, want zo staat de vraag "welk
#: aanleverritme heeft dit kanaal?" op één vindbare plaats in plaats van
#: verspreid door de functie die hem stelt.
#:
#: Een kanaal dat hier niet staat, valt in `_stand_periodiek` terug op
#: STANDAARD_ACHTER_DAGEN. Via `bronstanden` kan dat niet gebeuren — de
#: routering gebruikt deze sleutels — dus die terugval geldt alleen bij een
#: rechtstreekse aanroep. Ze staat er omdat een KeyError hier de hele `stand()`
#: zou meenemen, en dat is de dodemansknop die dan zwijgt: de laag die moet
#: melden dat het platform stilstaat, hoort zelf niet om te vallen.
#:
#: Vandaag leeg: alleen kanalen die vandaag laden staan hierin, en er is nu
#: geen kanaal met een periodiek (niet-dagelijks) ritme. Een lat voor een bron
#: die nog niet bestaat is een getal dat niemand ooit tegen de werkelijkheid
#: houdt.
#: Deliveroo: 90 dagen. Partner Hub levert per download hoogstens negentig
#: dagen, dus wie per kwartaal oplaadt loopt nooit meer dan dat achter; wie
#: het vergeet, ziet het hier als 'achter'. Gekozen op 19 september 2026, de
#: dag dat het kanaal geladen is.
ACHTER_DAGEN_PER_KANAAL: dict[str, int] = {"deliveroo": 90}

#: Zoveel dagen moet de kalender minstens voorbij vandaag lopen: de prognose
#: heeft voor elke voorspelde dag een kalenderrij nodig (zie VOORUIT_DAGEN in
#: canoniek), en een horizon van een week plus marge vraagt er veertien.
KALENDER_VOORUIT_MIN = 14

#: Een dag waarvan de dagomzet binnen deze marge van de open/dicht-drempel van
#: zijn weekdag ligt, is een grensgeval van de drempelregel: één cent verschil
#: en hij kantelt van openingsdag naar sluitingsdag. De meting van 12 augustus
#: vond een factor 25 leegte rond de drempel (zie DREMPEL_OPEN in canoniek);
#: zodra hier tóch dagen opduiken, is die leegte aan het dichtslibben en moet
#: iemand kijken.
DREMPELRAND_MARGE = 0.10

#: Over zoveel gemeten open dagen meet de censureringswachter het recente
#: aandeel leeg-reksignalen, en zoveel gemeten open dagen moeten er minstens
#: vóór dat venster liggen om het mee te vergelijken. Geteld in MEETDAGEN en
#: nooit in kalenderdagen: vier weken sluiting schuiven het venster niet op.
CENSURERING_VENSTER = 90
CENSURERING_MIN_ERVOOR = 60

#: Zoveel mag het recente censureringsaandeel afwijken van het aandeel over de
#: dagen ervoor. De meting van 13 augustus 2026 (529 gemeten open dagen, ruim
#: anderhalf jaar) zet het aandeel op 33,3% van de gewogen product-dagen, en
#: van alle 440 rollende vensters van 90 meetdagen in die reeks week er geen
#: enkel verder dan 3,7 procentpunt af van de rest. Acht procentpunt is ruim
#: twee keer die grootste uitschieter: geen enkel venster uit de gemeten
#: historiek zou hier zijn afgegaan, terwijl een breuk die een kwart van het
#: signaal verschuift (33% naar 25% of 41%) er meteen doorheen komt. Ruimer
#: zetten maakt de wachter blind, krapper laat hem afgaan op het seizoen.
CENSURERING_MARGE = 0.08

#: De sleutel waarop een canonieke verkooprij uniek hoort te zijn.
SLEUTEL = ["datum", "product_id", "kanaal", "filiaal_id"]

_RANG = {"goed": 0, "let_op": 1, "fout": 2}


@dataclass(frozen=True)
class Bronstand:
    """De stand van één bron: wat kwam er binnen, en verwachten we meer?

    status is een van:
      'vers'       de jongste meting is recent genoeg
      'achter'     er zouden metingen moeten zijn, maar de jongste is te oud
      'stil'       de kalender zegt dat de winkel open hoorde te zijn,
                   maar er komt niets binnen — het echte alarm
      'gesloten'   geen meting én de kalender zegt gemeten-gesloten:
                   geen meting verwacht, dus geen alarm
      'ontbreekt'  de bron is helemaal afwezig
    """

    bron: str
    laatste_meetdag: dt.date | None
    rijen: int
    status: str
    toelichting: str


@dataclass(frozen=True)
class Wachter:
    """Eén controle op de data zelf, met altijd een toelichting.

    Ook bij 'goed' staat er wat er gecontroleerd is: een leeg lijstje is niet
    te onderscheiden van een controle die nooit gedraaid heeft.
    """

    naam: str
    uitkomst: str  # 'goed' | 'let_op' | 'fout'
    toelichting: str


# --- de dodemansknop: bronstanden ------------------------------------------


def _datums(deel: pd.DataFrame) -> pd.Series:
    """De datumkolom genormaliseerd naar `date`, wat de aanroeper ook gaf."""
    return deel["datum"].map(_als_datum)


def _open_dagen_uit(kalender: pd.DataFrame) -> set[dt.date]:
    """De dagen die gemeten én open waren. Overal waar 'open' bedoeld wordt.

    `winkel_open` alleen zou niet volstaan: buiten het gemeten bereik staat
    die kolom ook op False, en 'niet gemeten' is iets anders dan 'dicht'.
    """
    if kalender.empty:
        return set()
    return {dag for dag, (gemeten, open_) in _status_per_dag(kalender).items()
            if gemeten and open_}


def _pct_nl(fractie: float) -> str:
    """'33,3 %'. Een toelichting is een zin voor een mens, en die heeft een
    komma en een spatie.

    De notatie komt uit `taal.procent_tekst` — dat is de laag ónder deze, dus
    geen kringimport. Van de contractlaag wordt hier nog steeds bewust niets
    geleend: de kwaliteitslaag ligt eronder en hoort er niets van te weten.
    """
    return procent_tekst(fractie)


def _euro_nl(bedrag: Decimal) -> str:
    """'€ 1.234,56'. Een bedrag in een zin die een mens leest."""
    heel, _, centen = f"{bedrag:.2f}".partition(".")
    return "€ " + f"{int(heel):,}".replace(",", ".") + "," + centen


def _stand_dagelijks(bron: str, deel: pd.DataFrame,
                     status_per_dag: dict[dt.date, tuple[bool, bool]],
                     gepland_dicht: dict[dt.date, str],
                     vandaag: dt.date) -> Bronstand:
    """Een bron die elke dag hoort te leveren, afgemeten aan de kalender.

    De dagen tussen de jongste meting en vandaag (vandaag zelf niet: de
    nachtelijke run laadt tot en met gisteren) vallen in vier bakjes, en de
    bakjes bepalen de status — zie de moduledocstring voor waarom deze indeling
    de hele reden van bestaan van deze laag is.

    HET VIERDE BAKJE IS ER PAS SINDS 18 AUGUSTUS 2026, en het ontbreken ervan
    liet deze wachter tijdens de zomersluiting 'achter' melden: tien ongemeten
    dagen "zonder kalenderverklaring", terwijl `gepland_dicht` voor elk van die
    dagen "Jaarlijkse sluiting" zei. Dat is dezelfde fout als in
    `canoniek._meetgat`, op een tweede plek — en precies het permanente alarm
    waar de kernregel bovenaan deze module tegen waarschuwt: een bron die vier
    weken zomersluiting lang 'achter' staat, valt op de dag van de echte
    achterstand niemand meer op.
    """
    laatste = _datums(deel).max()
    stil: list[dt.date] = []
    gesloten: list[dt.date] = []
    aangekondigd: list[dt.date] = []
    ongemeten: list[dt.date] = []
    dag = laatste + dt.timedelta(days=1)
    while dag < vandaag:
        gemeten, open_ = status_per_dag.get(dag, (False, False))
        if gemeten and open_:
            stil.append(dag)
        elif gemeten:
            gesloten.append(dag)
        elif dag in gepland_dicht:
            aangekondigd.append(dag)
        else:
            ongemeten.append(dag)
        dag += dt.timedelta(days=1)

    if stil:
        status = "stil"
        toelichting = t(
            f"{len(stil)} dag(en) waarop de winkel volgens de kalender open "
            f"hoorde te zijn zonder één ingeladen rij (eerste: "
            f"{stil[0].isoformat()}); jongste meting {laatste.isoformat()}.",
            f"{len(stil)} jour(s) où le magasin aurait dû être ouvert selon "
            f"le calendrier, sans une seule ligne chargée (premier : "
            f"{stil[0].isoformat()}) ; dernière mesure le "
            f"{laatste.isoformat()}.",
        )
    elif len(ongemeten) > MAX_ONGEMETEN_DAGEN:
        status = "achter"
        toelichting = t(
            f"Jongste meting {laatste.isoformat()}; {len(ongemeten)} dag(en) "
            f"zonder meting en zonder kalenderverklaring. Buiten het gemeten "
            f"bereik is dit 'niet ingeladen', geen stilte.",
            f"Dernière mesure le {laatste.isoformat()} ; {len(ongemeten)} "
            f"jour(s) sans mesure et sans explication du calendrier. Hors de "
            f"la période mesurée, c'est « pas chargé », pas un silence.",
        )
    elif gesloten or aangekondigd:
        status = "gesloten"
        # Beide lijstjes worden altijd gevuld; `t` hieronder kiest er één. Losse
        # `t`-aanroepen per deel zouden dezelfde tekst in twee talen door elkaar
        # laten lopen zodra er ooit één helft ontbreekt.
        deel_nl, deel_fr = [], []
        if gesloten:
            deel_nl.append(f"{len(gesloten)} gemeten-gesloten")
            deel_fr.append(f"{len(gesloten)} mesuré(s)-fermé(s)")
        if aangekondigd:
            deel_nl.append(f"{len(aangekondigd)} vooraf als gesloten "
                           f"aangekondigd")
            deel_fr.append(f"{len(aangekondigd)} annoncé(s) fermé(s) à "
                           f"l'avance")
        toelichting = t(
            f"Geen meting sinds {laatste.isoformat()}, maar de kalender "
            f"verklaart de tussenliggende dagen: {' en '.join(deel_nl)}. Geen "
            f"meting verwacht, geen alarm.",
            f"Aucune mesure depuis le {laatste.isoformat()}, mais le "
            f"calendrier explique les jours intermédiaires : "
            f"{' et '.join(deel_fr)}. Aucune mesure attendue, aucune alerte.",
        )
    else:
        status = "vers"
        toelichting = t(f"Jongste meting {laatste.isoformat()}.",
                        f"Dernière mesure le {laatste.isoformat()}.")

    return Bronstand(bron=bron, laatste_meetdag=laatste, rijen=len(deel),
                     status=status, toelichting=toelichting)


def _stand_bevroren(kanaal: str, deel: pd.DataFrame) -> Bronstand:
    """Een bron die niet meer aangevuld wórdt: klaar, en dus nooit een alarm.

    Er staat met opzet geen `vandaag` in de handtekening, en dat is de hele
    afspraak in één regel: een bevroren bron wordt niet tegen de klok gemeten,
    dus kan deze functie de klok niet eens lezen. Wie hier ooit toch een
    verstreken-dagen-lat in wil bouwen, moet eerst een argument verzinnen om
    die parameter terug te zetten — en dat argument bestaat niet zolang het
    kanaal in `BEVROREN` staat.

    De status 'bevroren' hoort uitsluitend bij deze functie. Een bron die nog
    wél bijkomt maar niet dagelijks is iets anders en gaat naar
    `_stand_periodiek`; die twee zijn hier bewust niet in één functie met een
    schakelaar gepropt, want dan zou 'bevroren' afhangen van een `if` in plaats
    van van de lijst waar het besluit in staat.

    `bron` is hier het kanaal zelf: `BRONNEN` geeft elke bron die niet
    dagelijks bijkomt dezelfde naam als haar kanaal (deliveroo), en de
    enige bron die anders heet — de kassa — komt hier per definitie nooit.
    """
    laatste = _datums(deel).max()
    # De toelichting noemt de jongste dag voluit, want dát is het feit dat een
    # lezer nodig heeft: tot wanneer loopt dit kanaal. Zie BEVROREN voor waarom
    # er verder geen oordeel bij hoort.
    return Bronstand(
        bron=kanaal,
        laatste_meetdag=laatste,
        rijen=len(deel),
        status="bevroren",
        toelichting=t(
            f"De historiek loopt tot {laatste.isoformat()}. Dit kanaal "
            f"wordt niet meer aangevuld: de periodieke aanlevering is op "
            f"17 augustus 2026 geschrapt op vraag van de opdrachtgever. "
            f"De cijfers hieronder zijn dus volledig voor het verleden en "
            f"groeien niet mee met vandaag.",
            f"L'historique va jusqu'au {laatste.isoformat()}. Ce canal "
            f"n'est plus alimenté : la livraison périodique a été "
            f"supprimée le 17 août 2026 à la demande du donneur d'ordre. "
            f"Les chiffres ci-dessous sont donc complets pour le passé "
            f"mais n'évoluent plus avec la date du jour.",
        ),
    )


def _stand_periodiek(kanaal: str, deel: pd.DataFrame,
                     vandaag: dt.date) -> Bronstand:
    """Een bron die wél bijkomt, maar niet dagelijks: zijn eigen lat, zijn ritme.

    Het verschil met `_stand_bevroren`: hier groeit de historiek nog, dus een
    achterstand ís weer een signaal en de status kan 'achter' worden. Het
    verschil met `_stand_dagelijks`: de lat is die van het aanleverritme van dit
    kanaal (`ACHTER_DAGEN_PER_KANAAL`) en niet de twee dagen van de nachtelijke
    run, en de winkelkalender doet hier niet mee — een kanaal dat per maand of
    per kwartaal binnenkomt volgt de openingsdagen van de toog niet, dus
    winkel_open en gepland_dicht zouden er niets over verklaren.

    Het kanaal draagt zijn eigen naam in de toelichting, uit `taal.kanaalnaam`
    — dezelfde bron als elk ander kanaallabel dat een mens leest — zodat de
    tekst klopt zodra een tweede kanaal langs dezelfde functie komt. Voor
    `bron` geldt hetzelfde als bij `_stand_bevroren`.
    """
    laatste = _datums(deel).max()
    # De lat van dít kanaal, met de terugval die bij ACHTER_DAGEN_PER_KANAAL
    # verantwoord staat: wie er geen heeft, krijgt die van de maandelijkse bron.
    lat = ACHTER_DAGEN_PER_KANAAL.get(kanaal, STANDAARD_ACHTER_DAGEN)
    naam = kanaalnaam(kanaal)
    oud = (vandaag - laatste).days
    if oud > lat:
        status = "achter"
        toelichting = t(
            f"Jongste {naam}-dag {laatste.isoformat()} is {oud} dagen oud; de "
            f"periodieke aanlevering mag hoogstens {lat} dagen achterlopen.",
            f"Le dernier jour {naam} {laatste.isoformat()} date d'il y a "
            f"{oud} jours ; la livraison périodique peut avoir au plus {lat} "
            f"jours de retard.",
        )
    else:
        status = "vers"
        toelichting = t(
            f"Jongste {naam}-dag {laatste.isoformat()} ({oud} dagen oud); "
            f"binnen het ritme van de periodieke aanlevering.",
            f"Dernier jour {naam} {laatste.isoformat()} (il y a {oud} jours) ; "
            f"dans le rythme de la livraison périodique.",
        )
    return Bronstand(bron=kanaal, laatste_meetdag=laatste, rijen=len(deel),
                     status=status, toelichting=toelichting)


def _stand_ontbreekt(bron: str) -> Bronstand:
    if bron == "deliveroo":
        toelichting = t(f"{DELIVEROO_REDEN} (open punt O2/G4).",
                        f"{DELIVEROO_REDEN_FR} (point ouvert O2/G4).")
    else:
        toelichting = t("Geen enkele rij ingeladen voor deze bron.",
                        "Pas une seule ligne chargée pour cette source.")
    return Bronstand(bron=bron, laatste_meetdag=None, rijen=0,
                     status="ontbreekt", toelichting=toelichting)


def bronstanden(verkopen: pd.DataFrame, kalender: pd.DataFrame, *,
                vandaag: dt.date) -> list[Bronstand]:
    """Per bron: wanneer kwam er voor het laatst iets binnen, en is dat erg?

    De kalender wordt alleen voor de kassabron geraadpleegd — winkel_gemeten,
    winkel_open en gepland_dicht gaan over de winkel. Een bron die niet
    dagelijks bijkomt kent geen winkelsluiting en krijgt zijn eigen lat.

    De routering leest twee lijsten en geen kanaalnamen: `BEVROREN` (komt niet
    meer bij) en de sleutels van `ACHTER_DAGEN_PER_KANAAL` (komt bij, maar niet
    dagelijks). Samen zijn dat precies de bronnen die niet in de dagelijkse tak
    horen; wie in geen van beide staat, wordt wél elke nacht verwacht. Zo staat
    elk van die twee begrippen op één plaats, en niet ook nog eens hier als
    naam. De volgorde is niet vrij: een bevroren kanaal dat nog een lat uit
    zijn actieve tijd heeft staan, blijft bevroren.
    """
    status_per_dag = {} if kalender.empty else _status_per_dag(kalender)
    gepland = {} if kalender.empty else _gepland_dicht_per_dag(kalender)
    standen = []
    for kanaal, bron in BRONNEN:
        deel = verkopen[verkopen["kanaal"] == kanaal]
        if deel.empty:
            standen.append(_stand_ontbreekt(bron))
        elif kanaal in BEVROREN:
            standen.append(_stand_bevroren(kanaal, deel))
        elif kanaal in ACHTER_DAGEN_PER_KANAAL:
            standen.append(_stand_periodiek(kanaal, deel, vandaag))
        else:
            standen.append(_stand_dagelijks(bron, deel, status_per_dag, gepland,
                                            vandaag))
    return standen


# --- de wachters -----------------------------------------------------------


def dubbele_sleutels(verkopen: pd.DataFrame) -> Wachter:
    """(datum, product_id, kanaal, filiaal_id) hoort uniek te zijn.

    Het extract aggregeert al per sleutel; een dubbel is dus een dubbele
    inlaad of een fout in de extractie, en telt bij elke som dubbel mee.
    """
    dubbel = int(verkopen.duplicated(subset=SLEUTEL).sum())
    if dubbel:
        return Wachter("dubbele_sleutels", "fout",
                       t(f"{dubbel} rij(en) met een sleutel die al bestaat.",
                         f"{dubbel} ligne(s) avec une clé qui existe déjà."))
    return Wachter("dubbele_sleutels", "goed",
                   t(f"{len(verkopen)} rijen gecontroleerd op de sleutel "
                     f"({', '.join(SLEUTEL)}); geen dubbels.",
                     f"{len(verkopen)} lignes contrôlées sur la clé "
                     f"({', '.join(SLEUTEL)}) ; aucun doublon."))


def negatieve_waarden(verkopen: pd.DataFrame) -> Wachter:
    """Negatieve omzet of aantallen: retourbonnen bestaan, dus geen 'fout'."""
    negatief = int(((verkopen["aantal"] < 0)
                    | (verkopen["omzet_excl_btw"] < 0)).sum())
    if negatief:
        return Wachter("negatieve_waarden", "let_op",
                       t(f"{negatief} rij(en) met negatieve omzet of negatief "
                         f"aantal; kan een retourbon zijn, kan een fout zijn.",
                         f"{negatief} ligne(s) avec un chiffre d'affaires ou "
                         f"une quantité en négatif ; peut être un ticket de "
                         f"retour, peut être une erreur."))
    return Wachter("negatieve_waarden", "goed",
                   t(f"{len(verkopen)} rijen gecontroleerd; geen negatieve "
                     f"omzet of aantallen.",
                     f"{len(verkopen)} lignes contrôlées ; pas de chiffre "
                     f"d'affaires ni de quantités en négatif."))


def gat_in_de_reeks(verkopen: pd.DataFrame, kalender: pd.DataFrame) -> Wachter:
    """Een open dag binnen het bereik van de ingeladen rijen zonder één rij.

    'Open' komt uit de kalender (winkel_gemeten én winkel_open), zodat een
    gesloten dag nooit als gat telt. Dagen ná de jongste ingeladen kassadag
    tellen hier evenmin: dat is geen gat maar stilte, en daar slaat de
    dodemansknop (`bronstanden`) op aan.
    """
    winkel = verkopen[verkopen["kanaal"] == "winkel"]
    if winkel.empty or kalender.empty:
        return Wachter("gat_in_de_reeks", "goed",
                       t("Geen kassadata of kalender om gaten in te zoeken; "
                         "niets gecontroleerd, niets gevonden.",
                         "Pas de données de caisse ni de calendrier où "
                         "chercher des trous ; rien de contrôlé, rien de "
                         "trouvé."))
    geladen = set(_datums(winkel))
    laatste = max(geladen)
    open_dagen = _open_dagen_uit(kalender)
    gaten = sorted(dag for dag in open_dagen
                   if dag <= laatste and dag not in geladen)
    if gaten:
        return Wachter("gat_in_de_reeks", "fout",
                       t(f"{len(gaten)} open dag(en) zonder één verkoopregel "
                         f"(eerste: {gaten[0].isoformat()}).",
                         f"{len(gaten)} jour(s) d'ouverture sans une seule "
                         f"ligne de vente (premier : {gaten[0].isoformat()})."))
    return Wachter("gat_in_de_reeks", "goed",
                   t(f"{len(open_dagen)} open dagen gecontroleerd; elke open "
                     f"dag heeft verkoopregels.",
                     f"{len(open_dagen)} jours d'ouverture contrôlés ; chaque "
                     f"jour d'ouverture a des lignes de vente."))


def kalenderdekking(kalender: pd.DataFrame, vandaag: dt.date) -> Wachter:
    """De prognose heeft kalenderrijen nodig voor dagen die nog moeten komen."""
    if kalender.empty:
        return Wachter("kalenderdekking", "let_op",
                       t("Geen kalender ingeladen; de prognose heeft voor elke "
                         "voorspelde dag een kalenderrij nodig.",
                         "Aucun calendrier chargé ; la prévision a besoin "
                         "d'une ligne de calendrier pour chaque jour prévu."))
    eind = _datums(kalender).max()
    vooruit = (eind - vandaag).days
    if vooruit < KALENDER_VOORUIT_MIN:
        return Wachter("kalenderdekking", "let_op",
                       t(f"De kalender loopt maar {vooruit} dag(en) voorbij "
                         f"vandaag; de prognose heeft er minstens "
                         f"{KALENDER_VOORUIT_MIN} nodig.",
                         f"Le calendrier ne va que {vooruit} jour(s) au-delà "
                         f"d'aujourd'hui ; la prévision en demande au moins "
                         f"{KALENDER_VOORUIT_MIN}."))
    return Wachter("kalenderdekking", "goed",
                   t(f"De kalender loopt {vooruit} dagen voorbij vandaag "
                     f"(minstens {KALENDER_VOORUIT_MIN} nodig).",
                     f"Le calendrier va {vooruit} jours au-delà d'aujourd'hui "
                     f"(au moins {KALENDER_VOORUIT_MIN} requis)."))


def drempelrand(verkopen: pd.DataFrame) -> Wachter:
    """Dagen die vlak bij de open/dicht-drempel van hun weekdag liggen.

    De drempel wordt hier op dezelfde manier herberekend als in
    canoniek._open_dagen: mediaan van de dagomzet per weekdag maal
    DREMPEL_OPEN, en hij vervalt onder MIN_DAGEN_PER_WEEKDAG dagen (dan is er
    geen drempel om een rand van te hebben). De weekdag volgt uit de datum
    zelf — dezelfde waarde als de weekdagkolom van de kalender.
    """
    winkel = verkopen[verkopen["kanaal"] == "winkel"]
    if winkel.empty:
        return Wachter("drempelrand", "goed",
                       t("Geen kassadata; geen drempel om een rand van te "
                         "hebben.",
                         "Pas de données de caisse ; pas de seuil, donc pas "
                         "de bord."))
    dagomzet = winkel.groupby(_datums(winkel))["omzet_excl_btw"].sum()
    wd = pd.Series([d.weekday() for d in dagomzet.index], index=dagomzet.index)
    mediaan = dagomzet.groupby(wd).median()
    aantal = dagomzet.groupby(wd).size()
    drempels = (mediaan * DREMPEL_OPEN).where(aantal >= MIN_DAGEN_PER_WEEKDAG, 0.0)
    lat = wd.map(drempels)
    rand = ((lat > 0)
            & (dagomzet >= lat * (1 - DREMPELRAND_MARGE))
            & (dagomzet <= lat * (1 + DREMPELRAND_MARGE)))
    randdagen = sorted(dagomzet.index[rand])
    rand_pct = procent_tekst(DREMPELRAND_MARGE, decimalen=0)
    if randdagen:
        return Wachter("drempelrand", "let_op",
                       t(f"{len(randdagen)} dag(en) met een dagomzet binnen "
                         f"{rand_pct} van de open/dicht-drempel "
                         f"van hun weekdag (eerste: "
                         f"{randdagen[0].isoformat()}); de drempelregel wordt "
                         f"daar een dubbeltje op zijn kant.",
                         f"{len(randdagen)} jour(s) dont le chiffre "
                         f"d'affaires journalier se trouve à moins de "
                         f"{rand_pct} du seuil ouvert/fermé de "
                         f"leur jour de semaine (premier : "
                         f"{randdagen[0].isoformat()}) ; la règle du seuil y "
                         f"tient à un fil."))
    return Wachter("drempelrand", "goed",
                   t(f"{len(dagomzet)} dagen getoetst aan de drempel van hun "
                     f"weekdag; geen dag binnen {rand_pct} van "
                     f"de rand.",
                     f"{len(dagomzet)} jours confrontés au seuil de leur jour "
                     f"de semaine ; aucun jour à moins de "
                     f"{rand_pct} du bord."))


# --- de wachters op bon- en uurniveau (O23) --------------------------------
#
# Deze twee lezen de twee losse extracties: de bonnentelling per dag
# (scripts/odoo_bonnen.py) en het eerste/laatste verkoopuur per product per dag
# (scripts/odoo_laatste_uur.py). Allebei zijn ze optioneel — die bestanden staan
# lokaal en niet in de repo — en dat stuurt hun vorm:
#
#   * ontbrekende invoer is geen fout. Een wachter die 'fout' roept omdat een
#     optionele extractie niet gedraaid heeft, staat permanent op rood, en een
#     alarm dat altijd afgaat is op de dag van de echte storing onzichtbaar
#     (dezelfde kernregel als bij de dodemansknop). De uitkomst is dan 'goed'
#     met een toelichting die zegt dat er niets gecontroleerd is en waarom —
#     precies wat `gat_in_de_reeks` en `drempelrand` doen bij lege invoer;
#   * een misvormde invoer is dat wél. Een bestand mét rijen maar zonder de
#     verwachte kolommen is een gebroken extractie, geen afwezige.


def bonnen_omzetdekking(verkopen: pd.DataFrame, bonnen: pd.DataFrame | None,
                        kalender: pd.DataFrame) -> Wachter:
    """Passen de bonnentelling en de omzet per dag bij elkaar?

    Twee extracties meten dezelfde dag: de verkopen leveren de omzet, de
    bonnentelling levert het aantal klanten. Een dag met omzet maar zonder
    bonnen (of andersom) betekent dat één van de twee daar een gat heeft. Dat
    gat is stil: het bonritme op het overzichtsscherm laat zo'n dag gewoon
    weg, en niemand ziet dat het gemiddelde bonbedrag over minder dagen loopt
    dan het lijkt.

    De bonnentelling is een onafhankelijke getuige, en dat is de winst
    tegenover `gat_in_de_reeks`. Die weegt de verkopen tegen de kalender, maar
    de kalender is zélf uit die verkopen gebouwd: mist een dag in het
    verkoopextract, dan weet de kalender daar niets van. De bonnen komen uit
    een andere query en zien dat wel.

    Getoetst wordt de AANWEZIGHEID van verkoopregels, niet de hoogte van de
    omzet. Dat is geen detail: een gemeten-gesloten dag heeft in dit model
    meestal wél een handvol bonnen (de drempelregel maakt een dag met
    verwaarloosbare omzet dicht, ze maakt hem niet leeg). Zou 'omzet' hier
    'omzet boven nul' betekenen, dan zou elke sluitingsdag met drie losse
    bonnen als gat op het scherm komen — het soort permanent alarm dat deze
    laag juist niet maakt.

    SLUITINGSBEWUST op drie manieren:

      * een echte sluiting laat in beide extracties niets achter. Zulke dagen
        vallen in het bakje 'geen van beide' en slaan nooit alarm; de kalender
        zegt erbij of die leegte een bekende sluiting is of een gat in allebei
        (dat laatste is het werk van `gat_in_de_reeks`);
      * een gesloten dag die tóch een paar bonnen droeg, heeft ze in allebei de
        extracties, en dat is geen mismatch;
      * er wordt alleen getoetst binnen het bereik dat BEIDE extracties dekken.
        Loopt de bonnenextractie achter — ze draait apart van de verkopen —
        dan verkort dat het bereik en slaat er niets aan. Achterstand is
        stilte, geen gat, en daar kijken de bronstanden naar.
    """
    if bonnen is None or bonnen.empty:
        return Wachter("bonnen_omzetdekking", "goed",
                       t("Niet gecontroleerd: de bonnentelling per dag is niet "
                         "ingeladen (scripts/odoo_bonnen.py). Zonder die "
                         "telling is er niets om naast de omzet te leggen.",
                         "Non contrôlé : le comptage des tickets par jour "
                         "n'est pas chargé (scripts/odoo_bonnen.py). Sans ce "
                         "comptage, il n'y a rien à mettre en regard du "
                         "chiffre d'affaires."))
    mist = {"datum", "bonnen"} - set(bonnen.columns)
    if mist:
        return Wachter("bonnen_omzetdekking", "fout",
                       t(f"De bonnentelling mist de kolom(men) "
                         f"{', '.join(sorted(mist))}; zo is ze niet te leggen "
                         f"naast de omzet.",
                         f"Le comptage des tickets n'a pas la ou les colonnes "
                         f"{', '.join(sorted(mist))} ; impossible ainsi de le "
                         f"mettre en regard du chiffre d'affaires."))

    winkel = verkopen[verkopen["kanaal"] == "winkel"]
    if winkel.empty:
        return Wachter("bonnen_omzetdekking", "goed",
                       t("Niet gecontroleerd: er is geen kassaverkoop "
                         "ingeladen om de bonnentelling naast te leggen.",
                         "Non contrôlé : aucune vente de caisse n'est chargée "
                         "pour être mise en regard du comptage des tickets."))

    dag_van_verkoop = _datums(winkel)
    regels_per_dag = winkel.groupby(dag_van_verkoop).size()
    omzet_per_dag = winkel.groupby(dag_van_verkoop)["omzet_excl_btw"].sum()
    bonnen_per_dag = bonnen.groupby(_datums(bonnen))["bonnen"].sum()

    van = max(regels_per_dag.index.min(), bonnen_per_dag.index.min())
    tot = min(regels_per_dag.index.max(), bonnen_per_dag.index.max())
    if van > tot:
        return Wachter("bonnen_omzetdekking", "let_op",
                       t(f"De twee extracties overlappen niet: de kassaverkoop "
                         f"loopt van {regels_per_dag.index.min().isoformat()} "
                         f"t/m {regels_per_dag.index.max().isoformat()}, de "
                         f"bonnentelling van "
                         f"{bonnen_per_dag.index.min().isoformat()} t/m "
                         f"{bonnen_per_dag.index.max().isoformat()}. Zonder "
                         f"gedeelde dag valt er niets te toetsen.",
                         f"Les deux extractions ne se recouvrent pas : les "
                         f"ventes de caisse vont du "
                         f"{regels_per_dag.index.min().isoformat()} au "
                         f"{regels_per_dag.index.max().isoformat()}, le "
                         f"comptage des tickets du "
                         f"{bonnen_per_dag.index.min().isoformat()} au "
                         f"{bonnen_per_dag.index.max().isoformat()}. Sans "
                         f"jour commun, il n'y a rien à vérifier."))

    status = _status_per_dag(kalender) if not kalender.empty else {}
    dagen = sorted(
        dag for dag in set(regels_per_dag.index) | set(bonnen_per_dag.index) | set(status)
        if van <= dag <= tot
    )

    # Aanwezigheid als verzameling: een dag telt mee zodra hij een verkoopregel
    # heeft (groupby.size is nooit nul) of een bonnentelling boven nul.
    met_verkoop = set(regels_per_dag.index)
    met_bonnen = set(bonnen_per_dag[bonnen_per_dag > 0].index)

    beide = gesloten = leeg = 0
    zonder_bonnen: list[dt.date] = []
    zonder_verkoop: list[dt.date] = []
    bedrag_zonder_bonnen = Decimal(0)
    for dag in dagen:
        heeft_verkoop = dag in met_verkoop
        heeft_bonnen = dag in met_bonnen
        if heeft_verkoop and heeft_bonnen:
            beide += 1
        elif heeft_verkoop:
            zonder_bonnen.append(dag)
            bedrag_zonder_bonnen += euro(float(omzet_per_dag.get(dag, 0.0)))
        elif heeft_bonnen:
            zonder_verkoop.append(dag)
        else:
            gemeten, open_ = status.get(dag, (False, False))
            if gemeten and not open_:
                gesloten += 1
            else:
                leeg += 1

    if zonder_bonnen or zonder_verkoop:
        deel = []
        if zonder_bonnen:
            deel.append(t(
                f"{len(zonder_bonnen)} dag(en) met kassaverkoop "
                f"({_euro_nl(bedrag_zonder_bonnen)}) maar zonder "
                f"bonnentelling (eerste: {zonder_bonnen[0].isoformat()})",
                f"{len(zonder_bonnen)} jour(s) avec des ventes de caisse "
                f"({_euro_nl(bedrag_zonder_bonnen)}) mais sans comptage des "
                f"tickets (premier : {zonder_bonnen[0].isoformat()})",
            ))
        if zonder_verkoop:
            deel.append(t(
                f"{len(zonder_verkoop)} dag(en) met bonnen maar zonder "
                f"één verkoopregel (eerste: "
                f"{zonder_verkoop[0].isoformat()})",
                f"{len(zonder_verkoop)} jour(s) avec des tickets mais sans "
                f"une seule ligne de vente (premier : "
                f"{zonder_verkoop[0].isoformat()})",
            ))
        return Wachter("bonnen_omzetdekking", "fout",
                       t(f"Binnen het bereik dat beide extracties dekken "
                         f"({van.isoformat()} t/m {tot.isoformat()}): ",
                         f"Dans la période couverte par les deux extractions "
                         f"(du {van.isoformat()} au {tot.isoformat()}) : ")
                       + t(" en ", " et ").join(deel)
                       + t(". Eén van de twee extracties heeft daar een gat; "
                           "die dagen vallen stilzwijgend uit het bonritme.",
                           ". L'une des deux extractions y a un trou ; ces "
                           "jours disparaissent en silence du rythme des "
                           "tickets."))

    staart = ""
    if leeg:
        staart = t(
            f" {leeg} dag(en) hebben verkoop noch bonnen zonder dat de "
            "kalender daar een sluiting kent; dat is geen "
            "dekkingsprobleem maar een gat in allebei, en daar kijkt de "
            "wachter op de reeks naar.",
            f" {leeg} jour(s) n'ont ni ventes ni tickets sans que le "
            "calendrier y connaisse une fermeture ; ce n'est pas un problème "
            "de couverture mais un trou dans les deux, et c'est le gardien "
            "de la série qui s'en occupe.",
        )
    return Wachter("bonnen_omzetdekking", "goed",
                   t(f"{beide} dag(en) tussen {van.isoformat()} en "
                     f"{tot.isoformat()} dragen zowel kassaverkoop als een "
                     f"bonnentelling; {gesloten} gemeten gesloten dag(en) zijn "
                     f"in beide extracties leeg. Buiten dit bereik dekt maar "
                     f"één van de twee de dagen — dat is achterstand, geen "
                     f"gat.",
                     f"{beide} jour(s) entre le {van.isoformat()} et le "
                     f"{tot.isoformat()} portent à la fois des ventes de "
                     f"caisse et un comptage des tickets ; {gesloten} jour(s) "
                     f"mesurés fermés sont vides dans les deux extractions. "
                     f"Hors de cette période, une seule des deux couvre les "
                     f"jours — c'est du retard, pas un trou.")
                   + staart)


def censureringsdrempel(uren: pd.DataFrame | None,
                        kalender: pd.DataFrame) -> Wachter:
    """Loopt het aandeel leeg-reksignalen weg van wat gebruikelijk is?

    De meting zelf staat in bakkerij/censurering.py en wordt hier niet
    overgedaan: een product-dag draagt een leeg-reksignaal wanneer drie dingen
    samenvallen — genoeg bonnen, de laatste bon ruim vóór de winkelsluiting
    van diezelfde dag, en ruim onder het eigen p90-uur. Op 13 augustus 2026
    gold dat voor 33,3% van de gewogen product-dagen (O8).

    Wat deze wachter toevoegt is de vraag of dat aandeel stabiel is. Het cijfer
    zelf is een bevinding voor het rapport; een plotselinge verschuiving is een
    signaal dat er iets aan de bron of aan de meting veranderd is — een andere
    productindeling, een gebroken uur- of bonnenveld, een winkel die anders is
    gaan bakken. In alle gevallen meet de prognose vanaf dat moment iets anders
    dan de dag ervoor, en dat hoort iemand te weten.

    SLUITINGSBEWUST op twee manieren. De vensters worden geteld in gemeten open
    dagen uit de kalender, nooit in kalenderdagen: vier weken zomersluiting
    schuiven het venster niet op en verdunnen het aandeel niet. En de meting
    zelf legt elk product naast de winkelsluiting van diezelfde dag, zodat een
    korte dag geen uitverkoop wordt.

    De referentie-uren worden één keer over het hele bereik berekend en daarna
    pas in twee periodes gesneden. Andersom — per periode meten — zou de lat
    meeschuiven met de verandering die deze wachter juist moet zien.
    """
    if uren is None or uren.empty:
        return Wachter("censureringsdrempel", "goed",
                       t("Niet gecontroleerd: het extract met het eerste en "
                         "laatste verkoopuur per product per dag is niet "
                         "ingeladen (scripts/odoo_laatste_uur.py). Zonder dat "
                         "extract bestaat het leeg-reksignaal niet.",
                         "Non contrôlé : l'extraction avec la première et la "
                         "dernière heure de vente par produit et par jour "
                         "n'est pas chargée (scripts/odoo_laatste_uur.py). "
                         "Sans cette extraction, le signal de rayon vide "
                         "n'existe pas."))
    mist = set(censurering.KOLOMMEN) - set(uren.columns)
    if mist:
        return Wachter("censureringsdrempel", "fout",
                       t(f"Het urenextract mist de kolom(men) "
                         f"{', '.join(sorted(mist))}; het leeg-reksignaal is "
                         f"er niet uit te rekenen.",
                         f"L'extraction des heures n'a pas la ou les colonnes "
                         f"{', '.join(sorted(mist))} ; impossible d'en "
                         f"calculer le signal de rayon vide."))

    open_dagen = _open_dagen_uit(kalender)
    if not open_dagen:
        return Wachter("censureringsdrempel", "goed",
                       t("Niet gecontroleerd: de kalender wijst geen enkele "
                         "gemeten open dag aan, en op een gesloten dag zegt "
                         "een leeg rek niets.",
                         "Non contrôlé : le calendrier n'indique aucun jour "
                         "d'ouverture mesuré, et un jour de fermeture, un "
                         "rayon vide ne dit rien."))

    per_dag = censurering.signaal_per_dag(
        uren.assign(datum=_datums(uren)), open_dagen=open_dagen
    )
    # Alleen product-dagen die kúnnen vlaggen: genoeg bonnen om iets over het
    # rek te zeggen, en een eigen referentie-uur om tegen af te zetten. Dat is
    # dezelfde noemer als `censurering.samenvatting`, en dus hetzelfde cijfer
    # als in het rapport.
    kern = per_dag
    dagen: list[dt.date] = []
    if not per_dag.empty:
        kern = per_dag[per_dag["gewogen"] & per_dag["referentie_uur"].notna()]
        dagen = sorted(set(kern["datum"]))
    nodig = CENSURERING_VENSTER + CENSURERING_MIN_ERVOOR
    if len(dagen) < nodig:
        return Wachter("censureringsdrempel", "goed",
                       t(f"Niet vergeleken: {len(dagen)} gemeten open dag(en) "
                         f"dragen een meetbaar leeg-reksignaal, en er zijn er "
                         f"{nodig} nodig ({CENSURERING_VENSTER} recent en "
                         f"{CENSURERING_MIN_ERVOOR} ervoor). Een aandeel op "
                         f"een handvol dagen is een gok en geen lat.",
                         f"Pas de comparaison : {len(dagen)} jour(s) "
                         f"d'ouverture mesuré(s) portent un signal de rayon "
                         f"vide mesurable, et il en faut {nodig} "
                         f"({CENSURERING_VENSTER} récents et "
                         f"{CENSURERING_MIN_ERVOOR} avant). Une part calculée "
                         f"sur une poignée de jours est un pari, pas une "
                         f"référence."))

    recent_dagen = set(dagen[-CENSURERING_VENSTER:])
    recent = kern[kern["datum"].isin(recent_dagen)]
    ervoor = kern[~kern["datum"].isin(recent_dagen)]
    aandeel_recent = float(recent["gecensureerd"].mean())
    aandeel_ervoor = float(ervoor["gecensureerd"].mean())
    verschil = aandeel_recent - aandeel_ervoor

    samen = t(
        f"{_pct_nl(aandeel_recent)} van de {len(recent)} gewogen "
        f"product-dagen in de laatste {CENSURERING_VENSTER} gemeten open "
        f"dagen (t/m {dagen[-1].isoformat()}) draagt een leeg-reksignaal, "
        f"tegen {_pct_nl(aandeel_ervoor)} over de {len(ervoor)} "
        f"product-dagen daarvóór",
        f"{_pct_nl(aandeel_recent)} des {len(recent)} jours-produits pondérés "
        f"des {CENSURERING_VENSTER} derniers jours d'ouverture mesurés "
        f"(jusqu'au {dagen[-1].isoformat()}) portent un signal de rayon vide, "
        f"contre {_pct_nl(aandeel_ervoor)} sur les {len(ervoor)} "
        f"jours-produits qui précèdent",
    )
    punten = f"{verschil * 100:+.1f}".replace(".", ",")
    marge = f"{CENSURERING_MARGE * 100:.0f}".replace(".", ",")
    if abs(verschil) > CENSURERING_MARGE:
        return Wachter("censureringsdrempel", "let_op",
                       t(f"{samen}: {punten} procentpunt, meer dan de marge "
                         f"van {marge} procentpunt die op deze reeks nog "
                         f"nooit overschreden werd. Er is iets aan de bron of "
                         f"aan de meting veranderd; de prognose meet vanaf "
                         f"hier iets anders dan daarvoor.",
                         f"{samen} : {punten} point(s) de pourcentage, plus "
                         f"que la marge de {marge} points de pourcentage qui "
                         f"n'a jamais été dépassée sur cette série. Quelque "
                         f"chose a changé à la source ou dans la mesure ; à "
                         f"partir d'ici, la prévision mesure autre chose "
                         f"qu'avant."))
    return Wachter("censureringsdrempel", "goed",
                   t(f"{samen}: {punten} procentpunt, binnen de marge van "
                     f"{marge} procentpunt. Het leeg-reksignaal meet nog "
                     f"hetzelfde als voorheen.",
                     f"{samen} : {punten} point(s) de pourcentage, dans la "
                     f"marge de {marge} points de pourcentage. Le signal de "
                     f"rayon vide mesure encore la même chose qu'avant."))


def wachters(verkopen: pd.DataFrame, kalender: pd.DataFrame, *,
             vandaag: dt.date, bonnen_df: pd.DataFrame | None = None,
             uren_df: pd.DataFrame | None = None) -> list[Wachter]:
    """Alle wachters, in vaste volgorde.

    `vandaag` is nodig voor de kalenderdekking en komt van de aanroeper: deze
    laag kijkt zelf nooit op de klok. `bonnen_df` en `uren_df` zijn de twee
    losse extracties op bon- en uurniveau; ze mogen None of leeg zijn, en de
    wachters die ze lezen zeggen dat dan met zoveel woorden.
    """
    return [
        dubbele_sleutels(verkopen),
        negatieve_waarden(verkopen),
        gat_in_de_reeks(verkopen, kalender),
        kalenderdekking(kalender, vandaag),
        drempelrand(verkopen),
        bonnen_omzetdekking(verkopen, bonnen_df, kalender),
        censureringsdrempel(uren_df, kalender),
    ]


# --- het gebundelde antwoord -----------------------------------------------


def _alarm(stand: Bronstand) -> str:
    """Wat een bronstatus bijdraagt aan 'ergste'.

    'gesloten' en 'vers' zijn goed nieuws. 'ontbreekt' van een bekend-afwezige
    bron ook: die afwezigheid staat mét reden in het bronnenlijstje, en een
    permanent alarm is onzichtbaar op de dag van de echte storing (de
    kernregel). 'stil' is het echte alarm en weegt als 'fout'.
    """
    if stand.status == "stil":
        return "fout"
    if stand.status == "achter":
        return "let_op"
    if stand.status == "ontbreekt" and stand.bron not in BEKEND_AFWEZIG:
        return "let_op"
    # 'bevroren' valt hier stilzwijgend onder 'goed', en dat is de bedoeling:
    # zie BEVROREN. De toestand staat mét datum en reden in het bronnenlijstje.
    return "goed"


def _ergste(uitkomsten: list[str]) -> str:
    return max(uitkomsten, key=_RANG.__getitem__, default="goed")


def stand(verkopen: pd.DataFrame, kalender: pd.DataFrame, *,
          vandaag: dt.date, bonnen_df: pd.DataFrame | None = None,
          uren_df: pd.DataFrame | None = None) -> dict:
    """Bronstanden en wachters gebundeld tot één antwoord voor de contractlaag.

    Datums staan als ISO-strings in de dict: het contract levert JSON, en de
    serialisatie hoort hier te gebeuren en niet in de UI (harde regel 4 in de
    geest: de UI vertaalt niets, ze toont).
    """
    bronnen = bronstanden(verkopen, kalender, vandaag=vandaag)
    controles = wachters(verkopen, kalender, vandaag=vandaag,
                         bonnen_df=bonnen_df, uren_df=uren_df)

    bronnen_dicts = []
    for b in bronnen:
        d = asdict(b)
        if d["laatste_meetdag"] is not None:
            d["laatste_meetdag"] = d["laatste_meetdag"].isoformat()
        bronnen_dicts.append(d)

    return {
        "bronnen": bronnen_dicts,
        "wachters": [asdict(w) for w in controles],
        "ergste": _ergste([_alarm(b) for b in bronnen]
                          + [w.uitkomst for w in controles]),
    }
