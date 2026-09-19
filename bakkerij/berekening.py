"""Berekeningslaag: van de feiten naar de afgeleide tabellen.

Dit is laag 3 uit CLAUDE.md. Alles hier is een pure functie op DataFrames: geen
database, geen bestanden, geen tijd-van-nu. De nachtelijke run roept deze
functies aan en schrijft het resultaat weg; de contractlaag erboven maakt er
JSON van. Dat de UI nooit rekent, begint hier: elk getal dat straks op een
scherm staat, komt uit een functie in dit bestand.

VIER REGELS DIE OVERAL GELDEN

*Alleen open dagen tellen mee.* Voor het kanaal winkel wordt eerst door
`alleen_open_dagen()` gefilterd. Een sluitingsdag is geen nulverkoop, en een
gemiddelde dat sluitingsdagen meerekent, is te laag zonder dat iemand ziet
waarom.

*Geld is Decimal.* Binnen pandas rekenen we in float omdat dat moet, maar alles
wat naar buiten gaat is `Decimal`, afgerond op centen. Nooit een float in een
antwoord.

*Er is geen "vandaag".* Elke functie krijgt een `peildatum` mee. De data loopt
tot een gemeten laatste dag en dat is zelden gisteren — op het moment van
schrijven stond de bakkerij in zomerverlof. Een kengetal dat "deze week" zegt
terwijl de meting drie dagen oud is, liegt op een manier die niemand opmerkt.
Daarom heet het hier "de laatste N gemeten open dagen" en draagt elk antwoord
zijn eigen peildatum.

*Twee periodes vergelijken alleen als ze even veel gemeten open dagen tellen.*
Een venster van 30 kalenderdagen telt kort na een sluitingsperiode minder
verkoopdagen dan het venster ervoor. Wie die twee toch naast elkaar zet, ziet
elk product "stijgen" en noemt producten dalers die niet gedaald zijn. Daarom
lopen alle vergelijkingen hier over gemeten open dagen (`_aangrenzende_vensters`
en `Venster`), en is het antwoord bij ongelijke vensters: er is geen
vergelijking, met het aantal dagen erbij zodat de contractlaag de reden kan
tonen. Nooit een vergelijking verzinnen die niet klopt.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

# Als module en niet als `from ... import t`: verderop bestaat een lokale `t`
# (omzet per bon), en een geschaduwde vertaalfunctie is een stille fout.
from bakkerij import taal as tl
from bakkerij.canoniek import alleen_open_dagen, tarief_voor

# De nl-kolom uit bakkerij/taal.py, en geen eigen kopie meer (18 augustus
# 2026): twee tabellen die hetzelfde moeten zeggen, lopen anders uit elkaar.
# Bewust vastgeprikt op "nl" en niet via tl.weekdag_kort(): deze labels gaan
# als machinewaarde de afgeleide tabel in, en die verandert niet mee met de
# ingestelde taal — vertalen gebeurt in de contractlaag.
WEEKDAGEN_KORT = tl.WEEKDAGEN_KORT["nl"]

CENT = Decimal("0.01")

# Hoever "een jaar eerder" terugligt. 364 dagen = 52 hele weken, zodat een
# maandag naast een maandag komt te liggen. Zie de uitleg in `venster()`:
# met 365 verschuift elk jaar-op-jaarcijfer een weekdag, en in een bakkerij
# is dat het verschil tussen zaterdag en vrijdag.
JAARSCHUIF = pd.Timedelta(days=364)


def euro(waarde: float | Decimal) -> Decimal:
    """Naar centen, half naar boven. De enige plek waar een bedrag wordt afgerond."""
    return Decimal(str(waarde)).quantize(CENT, rounding=ROUND_HALF_UP)


def _stuks(waarde: float) -> Decimal:
    """Stuks kunnen fractioneel zijn (gewicht), maar tonen als geheel getal."""
    return Decimal(str(waarde)).quantize(Decimal(1), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Venster:
    """Een periode plus dezelfde periode een jaar eerder, om mee te vergelijken.

    `vorig_volledig` zegt of het vorige jaar evenveel gemeten open dagen had. Zo
    niet, dan is de vergelijking scheef en dat moet zichtbaar zijn in plaats van
    weggemoffeld — het verschil wordt dan niet getoond.
    """

    van: pd.Timestamp
    tot: pd.Timestamp
    vorig_van: pd.Timestamp
    vorig_tot: pd.Timestamp
    dagen: int
    vorig_dagen: int

    @property
    def vorig_volledig(self) -> bool:
        return self.vorig_dagen == self.dagen


def open_verkopen(verkopen: pd.DataFrame, kalender: pd.DataFrame) -> pd.DataFrame:
    """De feiten waarop de hele berekeningslaag rust."""
    df = alleen_open_dagen(verkopen, kalender)
    return df.assign(datum=pd.to_datetime(df["datum"]))


def peildatum(open_verkopen_df: pd.DataFrame, kanaal: str = "winkel") -> pd.Timestamp:
    """De laatste dag waarop dit kanaal gemeten is. Niet 'vandaag'."""
    deel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal]
    if deel.empty:
        raise ValueError(f"Geen gemeten dagen voor kanaal {kanaal!r}")
    return pd.Timestamp(deel["datum"].max())


def dagtotalen(open_verkopen_df: pd.DataFrame) -> pd.DataFrame:
    """Per datum en kanaal: omzet en stuks. De basis onder alle andere tabellen."""
    uit = (
        open_verkopen_df.groupby(["datum", "kanaal"], as_index=False)
        .agg(omzet=("omzet_excl_btw", "sum"), stuks=("aantal", "sum"))
        .sort_values(["datum", "kanaal"], kind="stable")
        .reset_index(drop=True)
    )
    return uit


def _open_dagen_reeks(dagtotalen_df: pd.DataFrame, kanaal: str) -> pd.DatetimeIndex:
    deel = dagtotalen_df[dagtotalen_df["kanaal"] == kanaal]
    return pd.DatetimeIndex(sorted(deel["datum"].unique()))


def _aangrenzende_vensters(
    df: pd.DataFrame, tot: pd.Timestamp, dagen: int, kanaal: str
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """De laatste N gemeten open dagen t/m `tot`, en de N open dagen daarvóór.

    Beide vensters zijn een verzameling dagen en geen datumbereik: dat is het
    verschil tussen "de laatste 30 verkoopdagen" en "de laatste 30 dagen op de
    kalender". Na een sluitingsperiode van acht dagen bevat een kalendervenster
    acht verkoopdagen minder dan zijn voorganger, en dan is elke vergelijking
    tussen de twee scheef.

    De aanroeper vergelijkt alleen als `len(huidig) == len(vorig)` en meldt het
    verschil anders als "geen vergelijking, en dit is waarom". Werkt op elk frame
    met een kolom `datum` en een kolom `kanaal`: de dagtotalen én de open
    verkopen zelf.
    """
    alle = _open_dagen_reeks(df, kanaal)
    binnen = alle[alle <= tot]
    if len(binnen) == 0:
        raise ValueError(f"Geen open dagen tot en met {tot.date()}")
    huidig = binnen[-dagen:]
    vorig = binnen[: len(binnen) - len(huidig)][-dagen:]
    return huidig, vorig


def _productnamen(open_verkopen_df: pd.DataFrame) -> pd.Series:
    """Per `product_id` de jongste niet-lege productnaam.

    Het canonieke model kent een product op `product_id`; de naam is een
    attribuut en hoort niet in de groepeersleutel. Groeperen op (id, naam) heeft
    twee gevolgen die niemand wil:

      * pandas gooit met de standaard `dropna=True` elke rij zonder naam weg. In
        de echte data zijn dat 28 van 221.375 rijen, verdeeld over 4 producten,
        en die 4 groepen verdwijnen dus volledig uit de uitkomst. Een product dat
        hard daalt maar geen naam heeft, staat niet bij de dalers.
      * een product dat van naam verandert, valt uiteen in twee groepen: een
        "nieuw" product plus een volledige daling van het oude.

    Daarom: groeperen op id, en de naam er hier bijhalen. Een product waarvoor
    nergens een naam staat, komt niet in deze reeks voor en houdt in de tabel een
    lege naam. De consument zet daar een neutrale aanduiding op basis van
    `product_id` neer — een ontbrekend label is geen ontbrekend cijfer.
    """
    naam = open_verkopen_df["product_naam"]
    heeft_naam = naam.notna() & naam.fillna("").astype(str).str.strip().ne("")
    met_naam = open_verkopen_df[heeft_naam].sort_values("datum", kind="stable")
    return met_naam.groupby("product_id")["product_naam"].last()


def venster(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int, kanaal: str = "winkel"
) -> Venster:
    """De laatste N gemeten open dagen tot en met `tot`, plus dezelfde kalender-
    periode een jaar eerder.

    Het vorige jaar wordt op de kalender verschoven en niet op het aantal
    rijen. Een jaar eerder lag de zomersluiting op een andere plek, dus
    hetzelfde aantal open dagen zou een andere periode van het jaar beslaan en
    de vergelijking betekenisloos maken.

    De schuif is 364 dagen en geen 365. In een bakkerij is de weekdag de
    sterkste verklarende variabele die er is -- zaterdag doet het dubbele van
    dinsdag -- en 365 is geen veelvoud van zeven. Een schuif van 365 legt dus
    zaterdag naast vrijdag, en dat verschil zit in élk jaar-op-jaarcijfer op
    het overzichtsscherm. Gemeten op de echte reeks (18 aug 2026): over 30 open
    dagen gaf 365 een jaarverschil van +22,1% en 364 een van +26,9%. Bijna vijf
    procentpunt, puur uit de keuze van deze constante.

    364 = 52 weken. De prijs is dat het vergelijkingsvenster elk jaar één dag
    verder van de kalenderdatum af komt te liggen; over de horizon van dit
    platform (twee jaar historiek) is dat één à twee dagen, en dat weegt niet
    op tegen een structureel verschoven weekdag. `vorig_volledig` telt alleen
    open dagen en kan een faseverschuiving niet zien: die wacht vangt dit
    niet, en zou het ook niet moeten hoeven.
    """
    alle = _open_dagen_reeks(dagtotalen_df, kanaal)
    binnen = alle[alle <= tot]
    if len(binnen) == 0:
        raise ValueError(f"Geen open dagen tot en met {tot.date()}")
    gekozen = binnen[-dagen:]
    van = gekozen[0]

    vorig_van = van - JAARSCHUIF
    vorig_tot = tot - JAARSCHUIF
    vorig = alle[(alle >= vorig_van) & (alle <= vorig_tot)]

    return Venster(
        van=van, tot=tot,
        vorig_van=vorig_van, vorig_tot=vorig_tot,
        dagen=len(gekozen), vorig_dagen=len(vorig),
    )


def _som(
    dagtotalen_df: pd.DataFrame,
    van: pd.Timestamp,
    tot: pd.Timestamp,
    kanaal: str | None,
    kolom: str,
) -> float:
    deel = dagtotalen_df[
        (dagtotalen_df["datum"] >= van) & (dagtotalen_df["datum"] <= tot)
    ]
    if kanaal is not None:
        deel = deel[deel["kanaal"] == kanaal]
    return float(deel[kolom].sum())


@dataclass(frozen=True)
class Kerncijfer:
    """Eén getal bovenaan een scherm, met zijn eigen naam in twee registers.

    `sleutel` is de machinenaam en `label` is wat een mens leest. Dat zijn twee
    dingen en niet één, sinds 19 augustus 2026.

    WAAROM. `contract.py` bouwt de sleutel van een ontbrekende vergelijking als
    `f"kerncijfer.{...}"`, en dat was tot vandaag het lábel. Zolang de labels
    Nederlands waren viel dat niet op; sinds ze tweetalig zijn, heet dezelfde
    toestand in het Nederlands `kerncijfer.Omzet laatste 7 open dagen` en in het
    Frans `kerncijfer.Chiffre d'affaires, 7 derniers jours d'ouverture`. Een
    contractsleutel die met de taal van de lezer meebeweegt, is geen sleutel:
    `lib/toelichting.ts` belooft over `veld` uitdrukkelijk dat hij "stabiel is,
    een hertaling overleeft en door de app van fase 2 herkend wordt", en
    `reden(regels, "kerncijfer.…")` was daarmee onbruikbaar. Het brak niets op
    het scherm — er is een voorvoegselvangnet dat er "Kerncijfer: …" van maakt —
    maar het was een belofte die niet waargemaakt werd.

    De sleutels zijn kort, Engels noch Nederlands opgesmukt, en veranderen niet
    meer: `omzet_7`, `omzet_30`, `stuks_7`, `gemiddelde_dagomzet`. Wie er een
    vijfde bij zet, zet er ook een label bij in `platform/lib/toelichting.ts` —
    een test bewaakt dat die twee lijsten gelijk blijven.
    """

    sleutel: str
    label: str
    waarde: Decimal
    soort: str  # "euro" of "aantal"
    verschil_pct: Decimal | None
    richting: str | None  # "op", "neer" of None
    toelichting: str


def _verschil(nu: float, toen: float) -> tuple[Decimal | None, str | None]:
    """Procentueel verschil. Zonder vergelijkbaar verleden: niets, geen nul."""
    if toen == 0:
        return None, None
    pct = Decimal(str(100.0 * (nu - toen) / toen)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    if pct > 0:
        return pct, "op"
    if pct < 0:
        return pct, "neer"
    return pct, None


def kerncijfers(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, kanaal: str = "winkel"
) -> list[Kerncijfer]:
    """De vier getallen bovenaan het overzichtsscherm.

    Elk kengetal draagt zijn eigen toelichting, want "laatste 7 open dagen" is
    iets anders dan "deze week" en de gebruiker moet dat kunnen zien zonder het
    te moeten vragen.
    """
    week = venster(dagtotalen_df, tot, 7, kanaal)
    maand = venster(dagtotalen_df, tot, 30, kanaal)
    uit: list[Kerncijfer] = []

    # Waarom deze twee helpers bestaan, en niet vier keer met de hand:
    #
    # Tot 18 aug 2026 droeg elk kerncijfer zijn eigen wacht. Drie van de vier
    # deden dat goed; de gemiddelde dagomzet hieronder was er ooit los aan
    # toegevoegd en rekende zijn percentage kaal uit. Op het overzichtsscherm
    # stond daardoor: drie cijfers die zeggen "een vergelijking zou scheef
    # zijn", en ernaast een pijl omhoog uit precies diezelfde afgekeurde
    # vensters. Dat is harde regel 8 op zijn kop -- niet een ontbrekend cijfer,
    # maar een aanwezig cijfer dat niemand kan wantrouwen.
    #
    # Eén wacht en één reden, gedeeld door alle vier. Wie er een vijfde
    # kerncijfer bij zet, krijgt de wacht er gratis bij of moet er bewust
    # omheen werken.
    def _jaarverschil(v: Venster, nu: float, toen: float):
        return _verschil(nu, toen) if v.vorig_volledig else (None, None)

    def _reden(v: Venster) -> str:
        """De zin die uitlegt waarom er geen jaarvergelijking staat."""
        return tl.t(
            f"Vorig jaar telde {v.vorig_dagen} open dagen in dezelfde periode, "
            f"nu {v.dagen}; een vergelijking zou scheef zijn",
            f"L'an dernier, la même période comptait {v.vorig_dagen} jours "
            f"d'ouverture, contre {v.dagen} aujourd'hui ; une comparaison "
            f"serait faussée")

    for v, n in ((week, 7), (maand, 30)):
        nu = _som(dagtotalen_df, v.van, v.tot, kanaal, "omzet")
        toen = _som(dagtotalen_df, v.vorig_van, v.vorig_tot, kanaal, "omzet")
        pct, richting = _jaarverschil(v, nu, toen)
        toelichting = (
            tl.t(f"{v.van.date()} t/m {v.tot.date()}, {v.dagen} gemeten open "
                 f"dagen",
                 f"Du {v.van.date()} au {v.tot.date()}, {v.dagen} jours "
                 f"d'ouverture mesurés")
            if v.vorig_volledig
            else tl.t(f"{v.van.date()} t/m {v.tot.date()}. ",
                      f"Du {v.van.date()} au {v.tot.date()}. ") + _reden(v)
        )
        uit.append(Kerncijfer(
            sleutel=f"omzet_{n}",
            label=tl.t(f"Omzet laatste {n} open dagen",
                       f"Chiffre d'affaires, {n} derniers jours d'ouverture"),
            waarde=euro(nu), soort="euro",
            verschil_pct=pct, richting=richting, toelichting=toelichting,
        ))

    nu_stuks = _som(dagtotalen_df, week.van, week.tot, kanaal, "stuks")
    toen_stuks = _som(dagtotalen_df, week.vorig_van, week.vorig_tot, kanaal, "stuks")
    pct, richting = _jaarverschil(week, nu_stuks, toen_stuks)
    uit.append(Kerncijfer(
        sleutel="stuks_7",
        label=tl.t("Stuks laatste 7 open dagen",
                   "Unités, 7 derniers jours d'ouverture"),
        waarde=_stuks(nu_stuks), soort="aantal",
        verschil_pct=pct, richting=richting,
        # Ook hier de reden erbij: dit cijfer onderdrukte zijn vergelijking wél,
        # maar zweeg over het waarom. Een weggelaten percentage zonder uitleg
        # is voor een lezer niet te onderscheiden van een vergeten percentage.
        toelichting=(
            tl.t(f"{week.van.date()} t/m {week.tot.date()}",
                 f"Du {week.van.date()} au {week.tot.date()}")
            if week.vorig_volledig
            else tl.t(f"{week.van.date()} t/m {week.tot.date()}. ",
                      f"Du {week.van.date()} au {week.tot.date()}. ") + _reden(week)
        ),
    ))

    gem_nu = _som(dagtotalen_df, maand.van, maand.tot, kanaal, "omzet") / maand.dagen
    gem_toen = (
        _som(dagtotalen_df, maand.vorig_van, maand.vorig_tot, kanaal, "omzet")
        / maand.vorig_dagen
        if maand.vorig_dagen
        else 0.0
    )
    pct, richting = _jaarverschil(maand, gem_nu, gem_toen)
    uit.append(Kerncijfer(
        sleutel="gemiddelde_dagomzet",
        label=tl.t("Gemiddelde dagomzet", "Chiffre d'affaires moyen par jour"),
        waarde=euro(gem_nu), soort="euro",
        verschil_pct=pct, richting=richting,
        toelichting=(
            tl.t(f"over de laatste {maand.dagen} open dagen",
                 f"sur les {maand.dagen} derniers jours d'ouverture")
            if maand.vorig_volledig
            else tl.t(f"over de laatste {maand.dagen} open dagen. ",
                      f"sur les {maand.dagen} derniers jours d'ouverture. ")
            + _reden(maand)
        ),
    ))
    return uit


def omzetverloop(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int = 30,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """De laatste N open dagen als reeks, klaar om te plotten."""
    v = venster(dagtotalen_df, tot, dagen, kanaal)
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal)
        & (dagtotalen_df["datum"] >= v.van)
        & (dagtotalen_df["datum"] <= v.tot)
    ]
    return deel[["datum", "omzet", "stuks"]].sort_values("datum").reset_index(drop=True)


def maandomzet(dagtotalen_df: pd.DataFrame, kanaal: str = "winkel") -> pd.DataFrame:
    """Omzet per jaar en maand, met het aantal gemeten open dagen erbij.

    Dat aantal is geen sierlijkheid: augustus 2026 telt drie gemeten open dagen
    en augustus 2025 telde er negen. Een staaf naast een staaf zetten zonder dat
    erbij te zeggen, is de meest voorkomende manier om een dashboard te laten
    liegen.
    """
    deel = dagtotalen_df[dagtotalen_df["kanaal"] == kanaal].copy()
    deel["jaar"] = deel["datum"].dt.year
    deel["maand"] = deel["datum"].dt.month
    return (
        deel.groupby(["jaar", "maand"], as_index=False)
        .agg(omzet=("omzet", "sum"), open_dagen=("datum", "nunique"))
        .sort_values(["jaar", "maand"])
        .reset_index(drop=True)
    )


def kanaalverdeling(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int = 30
) -> pd.DataFrame:
    """Per kanaal de omzet over de laatste N kalenderdagen, plus het aandeel.

    Hier telt de kalender en niet het aantal open dagen, want de kanalen hebben
    verschillende meetvensters: Deliveroo loopt door op een dag dat de winkel
    dicht is.
    """
    van = tot - pd.Timedelta(days=dagen - 1)
    deel = dagtotalen_df[
        (dagtotalen_df["datum"] >= van) & (dagtotalen_df["datum"] <= tot)
    ]
    per = deel.groupby("kanaal", as_index=False).agg(
        omzet=("omzet", "sum"), stuks=("stuks", "sum"), dagen=("datum", "nunique")
    )
    totaal = float(per["omzet"].sum())
    per["aandeel_pct"] = (
        100.0 * per["omzet"] / totaal if totaal else 0.0
    )
    return per.sort_values("omzet", ascending=False).reset_index(drop=True)


def topproducten(
    open_verkopen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int = 30,
    aantal: int = 15, kanaal: str = "winkel",
) -> pd.DataFrame:
    """De best verkopende producten over de laatste N kalenderdagen.

    Gegroepeerd op `product_id`; de naam komt er via `_productnamen` bij, uit de
    volledige historiek van dit kanaal en niet alleen uit het venster.
    """
    van = tot - pd.Timedelta(days=dagen - 1)
    kanaaldeel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal]
    deel = kanaaldeel[
        (kanaaldeel["datum"] >= van) & (kanaaldeel["datum"] <= tot)
    ]
    per = (
        deel.groupby("product_id", as_index=False, dropna=False)
        .agg(stuks=("aantal", "sum"), omzet=("omzet_excl_btw", "sum"))
    )
    per["product_naam"] = per["product_id"].map(_productnamen(kanaaldeel))
    totaal = float(per["omzet"].sum())
    per["aandeel_pct"] = 100.0 * per["omzet"] / totaal if totaal else 0.0
    per = per[["product_id", "product_naam", "stuks", "omzet", "aandeel_pct"]]
    return per.nlargest(aantal, "omzet").reset_index(drop=True)


def productdekking(
    open_verkopen_df: pd.DataFrame, kalender: pd.DataFrame, drempel: float = 0.95
) -> pd.DataFrame:
    """Per product op hoeveel van de open dagen het verkocht is.

    Dit is de tabel achter de beslissing van 12 augustus: bij een product met een
    aanbodpatroon is een lege dag geen nulvraag. `kern` markeert de producten
    waarvoor een dagvoorspelling verantwoord is.

    Gegroepeerd op `product_id`: een product zonder naam hoort in deze tabel te
    staan, juist omdat de dekking bepaalt of het voorspelbaar is.
    """
    n_open = int(kalender["winkel_open"].sum())
    winkel = open_verkopen_df[open_verkopen_df["kanaal"] == "winkel"]
    per = (
        winkel.groupby("product_id", as_index=False, dropna=False)
        .agg(dagen=("datum", "nunique"), stuks=("aantal", "sum"),
             omzet=("omzet_excl_btw", "sum"),
             eerste=("datum", "min"), laatste=("datum", "max"))
    )
    per["product_naam"] = per["product_id"].map(_productnamen(winkel))
    per["dekking"] = per["dagen"] / n_open if n_open else 0.0
    per["kern"] = per["dekking"] >= drempel
    return per.sort_values("omzet", ascending=False).reset_index(drop=True)


def omzet_per_groep(
    open_verkopen_df: pd.DataFrame,
    groepen: pd.Series,
    tot: pd.Timestamp,
    dagen: int = 30,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """Omzet per productcategorie over de laatste N kalenderdagen.

    `groepen` is een reeks product_id -> categorie uit de productendimensie.
    Een product zonder categorie komt onder "Overige" terecht en verdwijnt niet:
    stil weglaten zou het totaal laten afwijken van het overzichtsscherm.
    """
    van = tot - pd.Timedelta(days=dagen - 1)
    deel = open_verkopen_df[
        (open_verkopen_df["kanaal"] == kanaal)
        & (open_verkopen_df["datum"] >= van)
        & (open_verkopen_df["datum"] <= tot)
    ].copy()
    deel["groep"] = (
        deel["product_id"].astype(str).map(groepen)
        .fillna(tl.t("Overige", "Autres"))
    )
    return (
        deel.groupby("groep", as_index=False)
        .agg(omzet=("omzet_excl_btw", "sum"), stuks=("aantal", "sum"))
        .sort_values("omzet", ascending=False)
        .reset_index(drop=True)
    )


@dataclass(frozen=True)
class Periodecontext:
    """De samenvatting onder het omzetverloop: wat was deze periode, en hoe
    verhoudt ze zich tot de periode ervoor."""

    totaal: Decimal
    gemiddelde: Decimal
    beste_datum: pd.Timestamp
    beste_omzet: Decimal
    verschil_pct: Decimal | None  # t.o.v. de N open dagen vóór deze periode
    richting: str | None
    dagen: int
    vorig_dagen: int


def periodecontext(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int = 30,
    kanaal: str = "winkel",
) -> Periodecontext:
    """Totaal, gemiddelde en beste dag over de laatste N gemeten open dagen,
    met het verschil ten opzichte van de N open dagen daarvóór.

    De vergelijking loopt hier niet met vorig jaar (dat doen de kerncijfers al)
    maar met de aangrenzende periode: dat is de vraag "trekt het aan of zakt
    het" die een zaakvoerder aan dit verloop stelt. Ze wordt alleen getoond als
    de vorige periode evenveel gemeten open dagen telt; anders is ze scheef en
    zegt het antwoord dat er geen vergelijking is.
    """
    huidig, vorig = _aangrenzende_vensters(dagtotalen_df, tot, dagen, kanaal)

    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal) & dagtotalen_df["datum"].isin(huidig)
    ]
    totaal = float(deel["omzet"].sum())
    beste = deel.loc[deel["omzet"].idxmax()]

    verschil_pct, richting = (None, None)
    if len(vorig) == len(huidig):
        toen = _som(dagtotalen_df, vorig[0], vorig[-1], kanaal, "omzet")
        verschil_pct, richting = _verschil(totaal, toen)

    return Periodecontext(
        totaal=euro(totaal),
        gemiddelde=euro(totaal / len(huidig)),
        beste_datum=pd.Timestamp(beste["datum"]),
        beste_omzet=euro(float(beste["omzet"])),
        verschil_pct=verschil_pct,
        richting=richting,
        dagen=len(huidig),
        vorig_dagen=len(vorig),
    )


def weekdagprofiel(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, weken: int = 8,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """Gemiddelde omzet per weekdag over de laatste N kalenderweken.

    Dit is het patroon waar de prognosebaseline op draait (het gemiddelde van
    gelijke weekdagen), zichtbaar gemaakt. Een weekdag waarop nooit gemeten is
    — de vaste sluitingsdag — komt niet in de uitkomst voor: een lege staaf
    zou een nulomzet suggereren die er niet is; de contractlaag maakt daar een
    onbeschikbaar-reden van, want stil weglaten mag niet (harde regel 8).

    `meetdagen` is het aantal dagen dat aan die weekdag heeft meegemeten, en gaat
    mee naar buiten. Zonder dat getal staat een weekdag met één meting op het
    scherm gelijk aan een weekdag met acht, terwijl het ene gemiddelde een
    patroon is en het andere een toevallige dag.
    """
    van = tot - pd.Timedelta(days=7 * weken - 1)
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal)
        & (dagtotalen_df["datum"] >= van)
        & (dagtotalen_df["datum"] <= tot)
    ].copy()
    deel["weekdag"] = deel["datum"].dt.dayofweek
    return (
        deel.groupby("weekdag", as_index=False)
        .agg(gemiddelde=("omzet", "mean"), meetdagen=("datum", "nunique"))
        .sort_values("weekdag")
        .reset_index(drop=True)
    )


VERSCHUIVING_KOLOMMEN = ["product_id", "product_naam", "omzet_nu", "omzet_vorig",
                         "verschil", "verschil_pct", "nieuw"]

VERSCHUIVING_DTYPES = {"product_id": "object", "product_naam": "object",
                       "omzet_nu": "float64", "omzet_vorig": "float64",
                       "verschil": "float64", "verschil_pct": "object",
                       "nieuw": "bool"}


def _leeg_verschuivingsframe() -> pd.DataFrame:
    """Nul rijen, maar wél de kolommen en de dtypes.

    Zo hoeft de aanroeper geen uitzondering te schrijven: `rijen["verschil"] > 0`
    doet het ook op een lege uitkomst. Een leeg frame is hier een antwoord ("geen
    vergelijking mogelijk") en geen fout.
    """
    return pd.DataFrame({k: pd.Series(dtype=v) for k, v in VERSCHUIVING_DTYPES.items()})


@dataclass(frozen=True)
class Verschuiving:
    """Wat er beweegt in het assortiment, plus of de vergelijking mag bestaan.

    `rijen` heeft de kolommen uit `VERSCHUIVING_KOLOMMEN`, gerangschikt op het
    verschil in euro's (aflopend). `dagen` en `vorig_dagen` zijn de gemeten open
    dagen in de twee vensters. Zijn die niet gelijk, dan is er geen vergelijking:
    `rijen` is dan leeg en de aanroeper maakt er een onbeschikbaar-reden van, met
    beide aantallen erin. Dat is dezelfde keuze als bij `Periodecontext` en
    `Venster`, en dus geen uitzondering.
    """

    rijen: pd.DataFrame
    dagen: int
    vorig_dagen: int

    @property
    def vergelijkbaar(self) -> bool:
        return self.dagen > 0 and self.vorig_dagen == self.dagen


def productverschuiving(
    open_verkopen_df: pd.DataFrame, tot: pd.Timestamp, dagen: int = 30,
    kanaal: str = "winkel",
) -> Verschuiving:
    """Per product de omzet in de laatste N gemeten open dagen naast de N ervoor.

    Het antwoord op "wat beweegt er in het assortiment", gerangschikt op het
    verschil in euro's en niet in procenten: een product dat van € 10 naar € 30
    gaat is geen groter nieuws dan een brood dat € 400 inlevert. Een product
    zonder omzet in de vorige periode krijgt geen percentage (deling door nul
    is geen groei van oneindig); `nieuw` markeert het.

    Twee dingen die deze functie bewust NIET doet:

    *Vergelijken in kalenderdagen.* De vensters zijn verzamelingen gemeten open
    dagen (`_aangrenzende_vensters`). Kort na een sluitingsperiode van acht dagen
    zou een kalendervenster van 30 dagen acht verkoopdagen minder tellen dan zijn
    voorganger; dan stijgt op papier elk product en staan er dalers op het scherm
    die niet gedaald zijn. Tellen de twee vensters niet evenveel open dagen, dan
    is de uitkomst leeg met de aantallen erbij, niet een vergelijking die niet
    klopt.

    *Groeperen op de naam.* De sleutel is `product_id`, de naam een attribuut
    (`_productnamen`). Anders verdwijnt een product zonder naam volledig uit de
    dalers, en valt een product dat van naam verandert uiteen in een "nieuw"
    product plus een volledige daling.
    """
    huidig, vorig = _aangrenzende_vensters(open_verkopen_df, tot, dagen, kanaal)
    kanaaldeel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal]

    if len(vorig) != len(huidig):
        return Verschuiving(
            rijen=_leeg_verschuivingsframe(),
            dagen=len(huidig),
            vorig_dagen=len(vorig),
        )

    def _per_product(venster_dagen: pd.DatetimeIndex) -> pd.DataFrame:
        deel = kanaaldeel[kanaaldeel["datum"].isin(venster_dagen)]
        return deel.groupby("product_id", as_index=False, dropna=False).agg(
            omzet=("omzet_excl_btw", "sum")
        )

    nu = _per_product(huidig).rename(columns={"omzet": "omzet_nu"})
    toen = _per_product(vorig).rename(columns={"omzet": "omzet_vorig"})
    samen = nu.merge(toen, on="product_id", how="outer").fillna(
        {"omzet_nu": 0.0, "omzet_vorig": 0.0}
    )
    samen["product_naam"] = samen["product_id"].map(_productnamen(kanaaldeel))
    samen["verschil"] = samen["omzet_nu"] - samen["omzet_vorig"]
    samen["verschil_pct"] = pd.Series(
        [
            100.0 * v / w if w > 0 else None
            for v, w in zip(samen["verschil"], samen["omzet_vorig"], strict=True)
        ],
        index=samen.index,
        dtype=object,
    )
    samen["nieuw"] = samen["omzet_vorig"] == 0.0
    rijen = (
        samen[VERSCHUIVING_KOLOMMEN]
        .sort_values("verschil", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    return Verschuiving(rijen=rijen, dagen=len(huidig), vorig_dagen=len(vorig))


# De vroegere `residu_kwantielen` en `prognose` stonden hier tot 18 augustus
# 2026. Productie loopt via bakkerij/backtest/rolling.py (kalibreer_kwantielen
# + band_naar_prognose), dat per horizonstap kalibreert; een tweede, simpeler
# prognosepad zonder aanroepers was alleen een plek om uit elkaar te lopen.


# --- hele weken -------------------------------------------------------------


@dataclass(frozen=True)
class Weekvenster:
    """Eén volledige kalenderweek, maandag tot en met zondag.

    `open_dagen` telt de gemeten open dagen in die week (winkel_gemeten én
    winkel_open). Een week vóór het meetbereik of middenin een sluiting telt
    nul; dat getal gaat mee zodat de consument ziet dat twee weken met een
    verschillend aantal open dagen niet zomaar naast elkaar mogen staan.
    """

    van: pd.Timestamp   # maandag
    tot: pd.Timestamp   # zondag
    open_dagen: int


def heleweken(
    kalender_df: pd.DataFrame, tot: pd.Timestamp, *, weken: int = 4
) -> list[Weekvenster]:
    """De laatste N volledige weken (ma t/m zo) die geheel op of vóór `tot`
    eindigen, oudste eerst.

    Nodig omdat een week-op-weekcijfer nooit een halve week mag vergelijken:
    een peildatum op woensdag zou anders "deze week" (drie dagen) naast een
    volle week zetten en een daling tonen die er niet is. De lopende, nog
    onvolledige week doet dus bewust niet mee.
    """
    tot = pd.Timestamp(tot)
    laatste_zondag = tot - pd.Timedelta(days=(tot.dayofweek + 1) % 7)
    open_dagen = {
        pd.Timestamp(d)
        for d in kalender_df.loc[
            kalender_df["winkel_gemeten"] & kalender_df["winkel_open"], "datum"
        ]
    }
    uit: list[Weekvenster] = []
    for terug in range(weken):
        zondag = laatste_zondag - pd.Timedelta(days=7 * terug)
        maandag = zondag - pd.Timedelta(days=6)
        telling = sum(
            1 for d in pd.date_range(maandag, zondag) if d in open_dagen
        )
        uit.append(Weekvenster(van=maandag, tot=zondag, open_dagen=telling))
    uit.reverse()
    return uit


WEEKOMZET_KOLOMMEN = ["van", "tot", "open_dagen", "omzet", "omzet_per_dag", "reden"]


def weekomzet(
    dagtotalen_df: pd.DataFrame, kalender_df: pd.DataFrame, tot: pd.Timestamp,
    *, weken: int = 4, kanaal: str = "winkel",
) -> pd.DataFrame:
    """Omzet per volledige kalenderweek, de laatste N t/m `tot`, oudste eerst.

    De vensters komen uit `heleweken` en niet uit een groupby op weeknummer: dat
    laatste zou de lopende halve week als een volle week tonen, en een week met
    drie verkoopdagen ziet er dan uit als een week die instortte.

    Naast de weekomzet staat `omzet_per_dag`, om dezelfde reden als bij
    `maandritme`: een week met een feestdag erin is geen slechte week, ze is een
    korte week, en alleen het dagcijfer houdt die twee uit elkaar. `open_dagen`
    gaat mee zodat de consument dat verschil ook kan tonen.

    Een week zonder gemeten open dagen krijgt None met de reden erbij en
    verdwijnt niet uit de tabel — een ontbrekende week is onzichtbaar, een week
    met een reden niet.

    Kolommen: van | tot | open_dagen | omzet (Decimal of None) |
    omzet_per_dag (Decimal of None) | reden (str of None).
    """
    vensters = heleweken(kalender_df, tot, weken=weken)
    deel = dagtotalen_df[dagtotalen_df["kanaal"] == kanaal]
    per_dag = deel.groupby("datum")["omzet"].sum()

    rijen = []
    for week in vensters:
        if week.open_dagen == 0:
            rijen.append({
                "van": week.van, "tot": week.tot, "open_dagen": 0,
                "omzet": None, "omzet_per_dag": None,
                "reden": "geen gemeten open dagen",
            })
            continue
        in_week = per_dag[(per_dag.index >= week.van) & (per_dag.index <= week.tot)]
        som = float(in_week.sum())
        rijen.append({
            "van": week.van, "tot": week.tot, "open_dagen": week.open_dagen,
            "omzet": euro(som),
            "omzet_per_dag": euro(som / week.open_dagen),
            "reden": None,
        })

    uit = pd.DataFrame(rijen, columns=WEEKOMZET_KOLOMMEN)
    # Zoals bij `maandritme`: de constructor maakt van None een NaN terwijl de
    # belofte None is.
    for kolom in ("omzet", "omzet_per_dag", "reden"):
        uit[kolom] = uit[kolom].astype(object).where(uit[kolom].notna(), None)
    return uit


# --- concentratie -----------------------------------------------------------


@dataclass(frozen=True)
class Concentratie:
    """Hoe zwaar de omzet op de kop van het assortiment leunt (Pareto).

    `voor_50` is het kleinste aantal producten dat samen minstens 50% van de
    omzet draagt, en zo verder. `staart_omzet` is de omzet van alles buiten de
    95%-kop: het bedrag waarover een assortimentsdiscussie werkelijk gaat.
    `dagen` is het aantal gemeten open dagen waarover geteld is.
    """

    voor_50: int
    voor_80: int
    voor_95: int
    totaal_producten: int
    staart_omzet: Decimal
    dagen: int


def concentratie(
    open_verkopen_df: pd.DataFrame, tot: pd.Timestamp, *, dagen: int = 90,
    kanaal: str = "winkel",
) -> Concentratie | None:
    """Omzetconcentratie over de laatste N gemeten open dagen.

    Gegroepeerd op `product_id` (zie `_productnamen` voor waarom nooit op de
    naam). `None` betekent: er is in het venster geen omzet om een verdeling
    over te berekenen — de contractlaag toont dat als onbeschikbaar met die
    reden, niet als "1 product draagt alles".
    """
    huidig, _ = _aangrenzende_vensters(open_verkopen_df, tot, dagen, kanaal)
    deel = open_verkopen_df[
        (open_verkopen_df["kanaal"] == kanaal)
        & open_verkopen_df["datum"].isin(huidig)
    ]
    per = (
        deel.groupby("product_id", dropna=False)["omzet_excl_btw"]
        .sum()
        .sort_values(ascending=False)
    )
    totaal = float(per.sum())
    if totaal <= 0:
        return None
    cumulatief = per.cumsum() / totaal

    def _kop(aandeel: float) -> int:
        """Het kleinste aantal producten waarmee `aandeel` gehaald wordt."""
        return int((cumulatief < aandeel).sum()) + 1

    voor_95 = _kop(0.95)
    return Concentratie(
        voor_50=_kop(0.50),
        voor_80=_kop(0.80),
        voor_95=voor_95,
        totaal_producten=len(per),
        staart_omzet=euro(float(per.iloc[voor_95:].sum())),
        dagen=len(huidig),
    )


# --- ontbinding prijs/volume ------------------------------------------------


@dataclass(frozen=True)
class Ontbinding:
    """Δomzet ontbonden: verkochten we minder, of verkochten we goedkoper?

    Alle bedragen zijn totalen over het venster, in euro. Zijn de twee
    vensters niet even lang (`vergelijkbaar` is False), dan zijn alle
    bedragen None en dragen `dagen` en `vorig_dagen` de reden — dezelfde
    redenlogica als bij `Verschuiving`.
    """

    verschil: Decimal | None    # Δomzet, het getal dat ontbonden wordt
    volume: Decimal | None      # (q1-q0)·p0 over de gemeenschappelijke producten
    prijs: Decimal | None       # q0·(p1-p0), prijs- en mixeffect
    kruisterm: Decimal | None   # (q1-q0)·(p1-p0)
    nieuw: Decimal | None       # omzet van producten die alleen in venster 1 staan
    verdwenen: Decimal | None   # omzet van producten die alleen in venster 0 staan
    dagen: int
    vorig_dagen: int

    @property
    def vergelijkbaar(self) -> bool:
        return self.dagen > 0 and self.vorig_dagen == self.dagen


def ontbinding_prijs_volume(
    open_verkopen_df: pd.DataFrame, tot: pd.Timestamp, *, dagen: int = 30,
    kanaal: str = "winkel",
) -> Ontbinding:
    """Δomzet tussen de laatste N gemeten open dagen en de N ervoor, ontbonden
    in volume, prijs/mix, kruisterm, nieuw en verdwenen.

    Per product dat in beide vensters met stuks verkocht is, met p = omzet/stuks
    in dat venster: volume-effect (q1−q0)·p0, prijs/mix-effect q0·(p1−p0) en de
    kruisterm (q1−q0)·(p1−p0). Producten die maar in één venster voorkomen — of
    in een venster wel omzet maar geen positieve stuks hebben, want daar bestaat
    geen prijs per stuk — tellen als `nieuw` respectievelijk `verdwenen`.

    De invariant is exact, op de cent:

        volume + prijs + kruisterm + nieuw − verdwenen == verschil

    Dat kan alleen doordat de kruisterm als sluitpost berekend wordt: de vier
    andere termen en Δomzet worden elk op de cent afgerond, en de kruisterm is
    het verschil. Wiskundig ís de kruisterm dat restant — (q1−q0)·(p1−p0) —
    en de afwijking met de rechtstreekse berekening is hooguit de som van de
    afrondingen. Vijf termen elk apart afronden en dan eisen dat ze optellen,
    kan er tot twee cent naast zitten, en een ontbinding die niet optelt is
    geen ontbinding.
    """
    huidig, vorig = _aangrenzende_vensters(open_verkopen_df, tot, dagen, kanaal)
    if len(vorig) != len(huidig):
        return Ontbinding(
            verschil=None, volume=None, prijs=None, kruisterm=None,
            nieuw=None, verdwenen=None,
            dagen=len(huidig), vorig_dagen=len(vorig),
        )

    kanaaldeel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal]

    def _per_product(venster_dagen: pd.DatetimeIndex) -> pd.DataFrame:
        deel = kanaaldeel[kanaaldeel["datum"].isin(venster_dagen)]
        return deel.groupby("product_id", dropna=False).agg(
            stuks=("aantal", "sum"), omzet=("omzet_excl_btw", "sum")
        )

    samen = (
        _per_product(huidig)
        .join(_per_product(vorig), how="outer", lsuffix="_1", rsuffix="_0")
        .fillna(0.0)
    )
    gemeenschappelijk = (samen["stuks_0"] > 0) & (samen["stuks_1"] > 0)
    g = samen[gemeenschappelijk]
    p0 = g["omzet_0"] / g["stuks_0"]
    p1 = g["omzet_1"] / g["stuks_1"]

    verschil = euro(float(samen["omzet_1"].sum() - samen["omzet_0"].sum()))
    volume = euro(float(((g["stuks_1"] - g["stuks_0"]) * p0).sum()))
    prijs = euro(float((g["stuks_0"] * (p1 - p0)).sum()))
    rest = samen[~gemeenschappelijk]
    nieuw = euro(float(rest["omzet_1"].sum()))
    verdwenen = euro(float(rest["omzet_0"].sum()))
    kruisterm = verschil - volume - prijs - nieuw + verdwenen

    return Ontbinding(
        verschil=verschil, volume=volume, prijs=prijs, kruisterm=kruisterm,
        nieuw=nieuw, verdwenen=verdwenen,
        dagen=len(huidig), vorig_dagen=len(vorig),
    )


# --- maandritme -------------------------------------------------------------

MAANDRITME_KOLOMMEN = ["jaar", "maand", "open_dagen", "omzet_per_dag", "reden"]


def maandritme(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, *, maanden: int = 12,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """Per kalendermaand, de laatste twaalf t/m de maand van `tot`: omzet per
    gemeten open dag, en het aantal van die dagen.

    Omzet per open dag en niet maandomzet: een maand met een zomersluiting is
    geen slechte maand, ze is een korte maand, en alleen het dagcijfer maakt
    die twee uit elkaar te houden. Een maand zonder gemeten open dagen krijgt
    `omzet_per_dag` None met de reden erbij — nooit een geëxtrapoleerd of
    nulcijfer, want "dicht" is geen "geen vraag" (zie canoniek.py).

    Kolommen: jaar | maand | open_dagen | omzet_per_dag (Decimal of None) |
    reden (str of None). Alle `maanden` rijen bestaan, oudste eerst: een gat
    in de tabel zou onzichtbaar zijn, een rij met een reden niet.
    """
    tot = pd.Timestamp(tot)
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal) & (dagtotalen_df["datum"] <= tot)
    ]
    per_maand = (
        deel.assign(periode=deel["datum"].dt.to_period("M"))
        .groupby("periode")
        .agg(omzet=("omzet", "sum"), open_dagen=("datum", "nunique"))
    )
    rijen = []
    for periode in pd.period_range(end=tot.to_period("M"), periods=maanden):
        if periode in per_maand.index and per_maand.loc[periode, "open_dagen"] > 0:
            n_dagen = int(per_maand.loc[periode, "open_dagen"])
            rijen.append({
                "jaar": periode.year, "maand": periode.month,
                "open_dagen": n_dagen,
                "omzet_per_dag": euro(
                    float(per_maand.loc[periode, "omzet"]) / n_dagen
                ),
                "reden": None,
            })
        else:
            rijen.append({
                "jaar": periode.year, "maand": periode.month, "open_dagen": 0,
                "omzet_per_dag": None, "reden": "geen gemeten open dagen",
            })
    uit = pd.DataFrame(rijen, columns=MAANDRITME_KOLOMMEN)
    # De constructor maakt van None een NaN; de belofte is None, dus terugzetten.
    for kolom in ("omzet_per_dag", "reden"):
        uit[kolom] = uit[kolom].astype(object).where(uit[kolom].notna(), None)
    return uit


# --- weekdagmix -------------------------------------------------------------


def weekdagmix(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, *, dagen: int = 56,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """Gemiddelde omzet per weekdag over de laatste N gemeten open dagen, plus
    het aandeel van elke weekdag in het totaal van dat venster.

    Anders dan `weekdagprofiel` (dat over kalenderweken kijkt) loopt dit venster
    over gemeten open dagen, zodat een sluitingsperiode het gemiddelde niet
    verwatert. Een weekdag zonder meting in het venster ontbreekt en wordt geen
    nulstaaf; `meetdagen` gaat mee zodat één toevallige zaterdag niet even hard
    op het scherm staat als acht maandagen.

    Kolommen: weekdag (0=ma) | weekdag_kort | meetdagen | gemiddelde |
    aandeel_pct. Bedragen zijn hier floats, zoals in elke tabel van deze laag;
    de contractlaag maakt er Decimals van via `euro()`.
    """
    huidig, _ = _aangrenzende_vensters(dagtotalen_df, tot, dagen, kanaal)
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal)
        & dagtotalen_df["datum"].isin(huidig)
    ].copy()
    deel["weekdag"] = deel["datum"].dt.dayofweek
    per = (
        deel.groupby("weekdag", as_index=False)
        .agg(gemiddelde=("omzet", "mean"), totaal=("omzet", "sum"),
             meetdagen=("datum", "nunique"))
        .sort_values("weekdag")
        .reset_index(drop=True)
    )
    per["weekdag_kort"] = per["weekdag"].map(lambda w: WEEKDAGEN_KORT[w])
    som = float(per["totaal"].sum())
    per["aandeel_pct"] = 100.0 * per["totaal"] / som if som else 0.0
    return per[["weekdag", "weekdag_kort", "meetdagen", "gemiddelde",
                "aandeel_pct"]]


# --- afwijkende dagen -------------------------------------------------------

AFWIJKING_KOLOMMEN = ["datum", "omzet", "verwacht_mediaan", "z"]

#: De robuuste z-score waarboven een dag een uitschieter heet, en het minimum
#: aantal waarnemingen dat een weekdag nodig heeft om mee te doen.
#:
#: Sinds 19 augustus 2026 moduleconstanten en geen kale getallen meer in de
#: signatuur. De contractlaag schrijft deze twee drempels namelijk voluit in
#: haar toelichting ("een robuuste afwijking van 3,5", "minder dan acht"), en
#: die proza stond los van de berekening: `contract._afwijkende_dagen` geeft
#: geen van beide argumenten mee, dus wie hier een drempel verzette, kreeg een
#: scherm dat een ander getal beloofde dan het toonde. Nu leest het contract
#: dezelfde constanten en kan de tekst niet meer uit de pas lopen.
AFWIJKING_DREMPEL = 3.5
AFWIJKING_MIN_PER_WEEKDAG = 8


def afwijkende_dagen(
    dagtotalen_df: pd.DataFrame, tot: pd.Timestamp, *, dagen: int = 90,
    drempel: float = AFWIJKING_DREMPEL,
    min_per_weekdag: int = AFWIJKING_MIN_PER_WEEKDAG,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """De dagen die hard afwijken van hun eigen weekdag, nieuwste eerst.

    Robuuste z-score per weekdag: z = 0.6745·(x − mediaan)/MAD, met mediaan en
    MAD over de waarnemingen van diezelfde weekdag binnen het venster. Mediaan
    en MAD in plaats van gemiddelde en standaardafwijking, omdat de uitschieter
    die we zoeken anders zijn eigen maatstaf opblaast en zichzelf verstopt.

    Een weekdag met minder dan `min_per_weekdag` waarnemingen doet niet mee
    (een mediaan van drie dagen is geen verwachting), en een weekdag met
    MAD nul evenmin: daar is elke afwijking oneindig veel en dus niets gezegd.
    Zulke dagen ontbreken in de uitkomst — dit is een uitschieterlijst, geen
    volledigheidstabel; wat hier niet staat, is niet "normaal verklaard".

    Kolommen: datum | omzet | verwacht_mediaan | z. Leeg-met-kolommen als er
    niets afwijkt, zodat de aanroeper geen uitzondering hoeft te schrijven.
    """
    huidig, _ = _aangrenzende_vensters(dagtotalen_df, tot, dagen, kanaal)
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal)
        & dagtotalen_df["datum"].isin(huidig)
    ].copy()
    deel["weekdag"] = deel["datum"].dt.dayofweek

    stukken = []
    for _, groep in deel.groupby("weekdag"):
        if groep["datum"].nunique() < min_per_weekdag:
            continue
        mediaan = float(groep["omzet"].median())
        mad = float((groep["omzet"] - mediaan).abs().median())
        if mad == 0:
            continue
        stuk = groep[["datum", "omzet"]].copy()
        stuk["verwacht_mediaan"] = mediaan
        stuk["z"] = 0.6745 * (stuk["omzet"] - mediaan) / mad
        stukken.append(stuk[stuk["z"].abs() >= drempel])

    if not stukken:
        return pd.DataFrame({
            "datum": pd.Series(dtype="datetime64[ns]"),
            "omzet": pd.Series(dtype="float64"),
            "verwacht_mediaan": pd.Series(dtype="float64"),
            "z": pd.Series(dtype="float64"),
        })
    return (
        pd.concat(stukken)[AFWIJKING_KOLOMMEN]
        .sort_values("datum", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


# --- bonritme ---------------------------------------------------------------


@dataclass(frozen=True)
class Bonritme:
    """Omzet = bonnen × gemiddeld bonbedrag, en welke van de twee bewoog.

    Minder klanten is een ander probleem dan een kleinere mand; deze ontbinding
    houdt ze uit elkaar. B = bonnen per dag, T = gemiddeld bonbedrag; `verschil`
    is B1·T1 − B0·T0, de verandering in omzet per dag tussen de twee vensters.

    `dagen_zonder_bonnen` telt de open dagen mét omzet maar zónder bonnen in
    het beschouwde bereik: die dagen vallen uit de vergelijking en de UI toont
    dat als beperking. Zonder vergelijkbare vensters zijn de effectvelden None,
    met `dagen` en `vorig_dagen` als reden — de bestaande redenlogica.
    """

    bonnen_per_dag: Decimal | None       # B1, gemiddeld over het huidige venster
    gemiddeld_bonbedrag: Decimal | None  # T1 = omzet/bonnen in het huidige venster
    verschil: Decimal | None             # B1·T1 − B0·T0, omzet per dag
    bonneneffect: Decimal | None         # (B1−B0)·T0
    bonbedrag_effect: Decimal | None     # B0·(T1−T0)
    kruisterm: Decimal | None            # (B1−B0)·(T1−T0)
    dagen: int
    vorig_dagen: int
    dagen_zonder_bonnen: int
    # B0 en T0: de twee getallen waar de effecten hierboven van afgeleid zijn.
    # Ze staan erbij zodat het scherm kan zeggen "312 klanten per dag tegenover
    # 240" in plaats van alleen "+ € 4.525": een lezer vergelijkt getallen,
    # geen effecten. None zolang er geen vergelijkbaar vorig venster is.
    vorig_bonnen_per_dag: Decimal | None = None
    vorig_bonbedrag: Decimal | None = None

    @property
    def vergelijkbaar(self) -> bool:
        return self.dagen > 0 and self.vorig_dagen == self.dagen


def bonritme(
    bonnen_df: pd.DataFrame, dagtotalen_df: pd.DataFrame, tot: pd.Timestamp,
    *, dagen: int = 30, kanaal: str = "winkel",
) -> Bonritme:
    """Bonnen per dag en gemiddeld bonbedrag over de laatste N gemeten open
    dagen die in beide bronnen zitten, plus de ontbinding tegenover het
    aangrenzende evenlange venster.

    `bonnen_df` is de aparte distinct-telling per dag per kassa
    (scripts/odoo_bonnen.py); de som over de kassa's per dag is correct, de
    som van bonnen per product-dag zou dat NIET zijn — een bon met drie
    producten telt daar drie keer, en dan zakt het bonbedrag mee met de
    assortimentsbreedte in plaats van met de klant.

    De vensters lopen over de open dagen waarvoor beide bronnen een meting
    hebben: een dag met omzet maar zonder bonnen kan niet meedoen, en doen
    alsof (bonnen nul, bonbedrag oneindig) zou de ontbinding vergiftigen.
    Zulke dagen worden geteld in `dagen_zonder_bonnen`.

    De invariant is exact, op de cent:

        bonneneffect + bonbedrag_effect + kruisterm == verschil

    om dezelfde reden en op dezelfde manier als bij `ontbinding_prijs_volume`:
    de kruisterm is de sluitpost, wat hij wiskundig ook is.
    """
    tot = pd.Timestamp(tot)
    bonnen = bonnen_df.copy()
    bonnen["datum"] = pd.to_datetime(bonnen["datum"])
    # Distinct per kassa aan de bron; de som over kassa's per dag mag wél.
    bonnen_per_dag = bonnen.groupby("datum")["bonnen"].sum()

    omzet_per_dag = (
        dagtotalen_df[dagtotalen_df["kanaal"] == kanaal]
        .groupby("datum")["omzet"].sum()
    )
    open_dagen = pd.DatetimeIndex(sorted(omzet_per_dag.index))
    binnen = open_dagen[open_dagen <= tot]
    if len(binnen) == 0:
        raise ValueError(f"Geen open dagen tot en met {tot.date()}")

    beide = binnen[binnen.isin(bonnen_per_dag.index)]
    huidig = beide[-dagen:]
    vorig = beide[: len(beide) - len(huidig)][-dagen:]

    # De open dagen die uit de vergelijking vallen omdat de bonnen ontbreken,
    # binnen het bereik dat de vensters beslaan (tot en met de peildatum).
    bereik_van = vorig[0] if len(vorig) else (
        huidig[0] if len(huidig) else binnen[-dagen:][0]
    )
    bereik = binnen[binnen >= bereik_van]
    zonder_bonnen = int((~bereik.isin(bonnen_per_dag.index)).sum())

    if len(huidig) == 0:
        return Bonritme(
            bonnen_per_dag=None, gemiddeld_bonbedrag=None, verschil=None,
            bonneneffect=None, bonbedrag_effect=None, kruisterm=None,
            dagen=0, vorig_dagen=0, dagen_zonder_bonnen=zonder_bonnen,
        )

    def _b_en_t(venster_dagen: pd.DatetimeIndex) -> tuple[float, float | None]:
        """Bonnen per dag en gemiddeld bonbedrag over een venster."""
        b_som = float(bonnen_per_dag.loc[venster_dagen].sum())
        o_som = float(omzet_per_dag.loc[venster_dagen].sum())
        b = b_som / len(venster_dagen)
        t = o_som / b_som if b_som > 0 else None
        return b, t

    b1, t1 = _b_en_t(huidig)

    verschil = bonneneffect = bonbedrag_effect = kruisterm = None
    vorig_b = vorig_t = None
    if len(vorig) == len(huidig) and t1 is not None:
        b0, t0 = _b_en_t(vorig)
        if t0 is not None:
            verschil = euro(b1 * t1 - b0 * t0)
            bonneneffect = euro((b1 - b0) * t0)
            bonbedrag_effect = euro(b0 * (t1 - t0))
            kruisterm = verschil - bonneneffect - bonbedrag_effect
            vorig_b = Decimal(str(b0)).quantize(Decimal("0.1"),
                                                rounding=ROUND_HALF_UP)
            vorig_t = euro(t0)

    return Bonritme(
        bonnen_per_dag=Decimal(str(b1)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        ),
        gemiddeld_bonbedrag=euro(t1) if t1 is not None else None,
        verschil=verschil,
        bonneneffect=bonneneffect,
        bonbedrag_effect=bonbedrag_effect,
        kruisterm=kruisterm,
        dagen=len(huidig),
        vorig_dagen=len(vorig),
        dagen_zonder_bonnen=zonder_bonnen,
        vorig_bonnen_per_dag=vorig_b,
        vorig_bonbedrag=vorig_t,
    )


# --- de CFO-dagtabel ---------------------------------------------------------


CFO_DAGTABEL_KOLOMMEN = [
    "datum", "klanten", "omzet", "gemiddeld_ticket", "deliveroo", "totaal",
]


def cfo_dagtabel(
    bonnen_df: pd.DataFrame, dagtotalen_df: pd.DataFrame, tot: pd.Timestamp,
    *, dagen: int = 7, kanaal: str = "winkel",
) -> pd.DataFrame:
    """Per dag: hoeveel klanten, hoeveel omzet, en wat ze gemiddeld afrekenden.

    De vorm komt van de opdrachtgever zelf. Die maakt met de hand een
    weekrapport per winkel met precies deze kolommen (datum, klanten, omzet,
    gemiddeld ticket) en las die tot nu toe naast dit platform in plaats van
    erin. Dit is dat rapport, uit de gemeten data in plaats van uit een
    spreadsheet.

    WAAROM DIT NAAST `bonritme` STAAT EN ER NIET IN. `bonritme` beantwoordt één
    vraag over een venster als geheel: kwam de verandering van de klanten of
    van het mandje. Deze tabel beantwoordt geen vraag, ze toont de dagen. Dat
    zijn twee verschillende dingen, en ze samenvoegen zou van beide een
    halfslachtige versie maken.

    EEN DAG ZONDER BONNENTELLING VALT NIET WEG, hij krijgt `klanten` en
    `gemiddeld_ticket` op None. Dat is het verschil met `bonritme`, dat zulke
    dagen bewust buiten de vergelijking houdt omdat ze de ontbinding zouden
    vergiftigen. Hier is weglaten juist de slechtste optie: een dag met omzet
    die uit de tabel verdwijnt, leest als een dag waarop de zaak dicht was. De
    omzet staat er dus, met een leeg klantenvak ernaast en de reden erbij in de
    contractlaag.

    Gesorteerd op datum, oplopend: dit is een leesbare tabel en geen
    ranglijst.
    """
    tot = pd.Timestamp(tot)
    omzet_per_dag = (
        dagtotalen_df[dagtotalen_df["kanaal"] == kanaal]
        .groupby("datum")["omzet"].sum()
    )
    open_dagen = pd.DatetimeIndex(sorted(omzet_per_dag.index))
    binnen = open_dagen[open_dagen <= tot]
    if len(binnen) == 0:
        return pd.DataFrame(columns=CFO_DAGTABEL_KOLOMMEN)

    venster = binnen[-dagen:]

    # Deliveroo naast de kassa, zoals in het weekrapport van de opdrachtgever
    # (kolommen klanten, kassa, Deliveroo, totaal). De Deliveroo-omzet is
    # netto: subtotaal min commissie, zie `canoniek.orders_naar_canoniek`.
    #
    # DRIE TOESTANDEN, EN ZE ZIEN ER VERSCHILLEND UIT. Een dag mét een
    # Deliveroo-rij is een gemeten dag. Een dag zónder rij maar bínnen de
    # geladen historiek is een dag met nul bestellingen: de export heeft over
    # die dag gesproken en er stond niets in. Een dag ná de jongste export is
    # onbekend (None): daar heeft nog geen export over gesproken, en nul tonen
    # zou een gat in de aanlevering laten lezen als een dag zonder klanten.
    # Het totaal volgt de Deliveroo-kolom: onbekend plus gemeten is onbekend.
    dl_per_dag = (
        dagtotalen_df[dagtotalen_df["kanaal"] == "deliveroo"]
        .groupby("datum")["omzet"].sum()
    )
    dl_van = pd.Timestamp(dl_per_dag.index.min()) if not dl_per_dag.empty else None
    dl_tot = pd.Timestamp(dl_per_dag.index.max()) if not dl_per_dag.empty else None

    # De bonnen zijn per kassa; de som over de kassa's van één dag is het
    # aantal klanten. De som van bonnen per product-dag zou dat NIET zijn --
    # zie de docstring van `bonritme`.
    bonnen = bonnen_df.copy()
    klanten_per_dag = pd.Series(dtype="float64")
    if not bonnen.empty:
        bonnen["datum"] = pd.to_datetime(bonnen["datum"])
        klanten_per_dag = bonnen.groupby("datum")["bonnen"].sum()

    rijen = []
    for dag in venster:
        omzet = euro(float(omzet_per_dag.loc[dag]))
        aantal = klanten_per_dag.get(dag)
        klanten = int(aantal) if aantal is not None and aantal > 0 else None
        if dl_tot is not None and dl_van <= dag <= dl_tot:
            deliveroo = euro(float(dl_per_dag.get(dag, 0.0)))
        else:
            deliveroo = None
        rijen.append({
            "datum": dag,
            "klanten": klanten,
            "omzet": omzet,
            "deliveroo": deliveroo,
            "totaal": (euro(float(omzet) + float(deliveroo))
                       if deliveroo is not None else None),
            # Het gemiddelde ticket is de omzet gedeeld door de klanten van
            # diezelfde dag, en niet het gemiddelde van de dagtickets: dat
            # laatste weegt een rustige dinsdag even zwaar als een zaterdag.
            "gemiddeld_ticket": (euro(float(omzet) / klanten)
                                 if klanten else None),
        })
    tabel = pd.DataFrame(rijen, columns=CFO_DAGTABEL_KOLOMMEN)
    # `klanten` expliciet op object, anders maakt pandas van een kolom met
    # gehele getallen én None een float64-kolom en wordt die None een NaN. Dat
    # is geen cosmetisch verschil: NaN is een getal, overleeft een `is None`-
    # toets niet, en belandt als "NaN" op het scherm in plaats van als een leeg
    # vak met een reden. De twee bedragkolommen dragen Decimals en zijn daarom
    # al object; deze is de enige die het nodig heeft.
    tabel["klanten"] = pd.Series([r["klanten"] for r in rijen],
                                 dtype="object", index=tabel.index)
    return tabel


# --- periodeblokken (de kubus achter de periodekiezer) ------------------------


@dataclass(frozen=True)
class Periodeblok:
    """De samenvatting van één kalendervenster: som, telling, gemiddelde.

    Het gemiddelde is per gemeten open dag en niet per kalenderdag: een venster
    met een zomersluiting erin is geen slechte periode, het is een korte
    periode. Twee blokken vergelijken gebeurt daarom op dit gemiddelde — dat
    blijft eerlijk óók wanneer de vensters niet evenveel open dagen tellen,
    zolang beide aantallen erbij staan.
    """

    van: pd.Timestamp
    tot: pd.Timestamp
    omzet: Decimal
    open_dagen: int
    gemiddelde: Decimal | None  # per gemeten open dag; None zonder open dagen


def periodeblok(
    dagtotalen_df: pd.DataFrame, van: pd.Timestamp, tot: pd.Timestamp,
    kanaal: str = "winkel",
) -> Periodeblok:
    """Som en gemiddelde over één datumbereik (beide grenzen inbegrepen)."""
    deel = dagtotalen_df[
        (dagtotalen_df["kanaal"] == kanaal)
        & (dagtotalen_df["datum"] >= van)
        & (dagtotalen_df["datum"] <= tot)
    ]
    som = float(deel["omzet"].sum())
    open_dagen = int(deel["datum"].nunique())
    return Periodeblok(
        van=pd.Timestamp(van), tot=pd.Timestamp(tot),
        omzet=euro(som), open_dagen=open_dagen,
        gemiddelde=euro(som / open_dagen) if open_dagen else None,
    )


# --- drill-down per productgroep -------------------------------------------------


def groepen_detail(
    open_verkopen_df: pd.DataFrame,
    groepen: pd.Series,
    tot: pd.Timestamp,
    *,
    dagen: int = 30,
    kanaal: str = "winkel",
) -> pd.DataFrame:
    """Elk product met zijn groep over de laatste N kalenderdagen, klaar voor
    de drill-down groep -> product op Productmix.

    Gegroepeerd op `product_id` (naam via `_productnamen`, zie topproducten);
    een product zonder categorie valt onder "Overige" en verdwijnt niet, om
    dezelfde reden als in `omzet_per_groep`. `aandeel_in_groep_pct` weegt
    binnen de eigen groep: dat is de vraag die een drill-down beantwoordt.

    Kolommen: groep | product_id | product_naam | stuks | omzet |
    aandeel_in_groep_pct — gesorteerd op groepsomzet, dan productomzet.
    """
    van = tot - pd.Timedelta(days=dagen - 1)
    kanaaldeel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal]
    deel = kanaaldeel[
        (kanaaldeel["datum"] >= van) & (kanaaldeel["datum"] <= tot)
    ].copy()
    if deel.empty:
        return pd.DataFrame(columns=["groep", "product_id", "product_naam",
                                     "stuks", "omzet", "aandeel_in_groep_pct"])
    per = (
        deel.groupby("product_id", as_index=False, dropna=False)
        .agg(stuks=("aantal", "sum"), omzet=("omzet_excl_btw", "sum"))
    )
    per["product_naam"] = per["product_id"].map(_productnamen(kanaaldeel))
    per["groep"] = (per["product_id"].astype(str).map(groepen)
                    .fillna(tl.t("Overige", "Autres")))
    groepsomzet = per.groupby("groep")["omzet"].transform("sum")
    per["aandeel_in_groep_pct"] = (
        (100.0 * per["omzet"] / groepsomzet).where(groepsomzet > 0, 0.0)
    )
    per = per.assign(_groepsomzet=groepsomzet).sort_values(
        ["_groepsomzet", "omzet"], ascending=[False, False], kind="stable"
    )
    return per[["groep", "product_id", "product_naam", "stuks", "omzet",
                "aandeel_in_groep_pct"]].reset_index(drop=True)


# --- kanaalfinanciën -----------------------------------------------------------


@dataclass(frozen=True)
class Kanaalfinancien:
    """Bruto, commissie en netto van één kanaal over een venster.

    De canonieke omzet van een commissiekanaal zoals Deliveroo is netto (wat
    het platform inhoudt, komt nooit binnen); dit beeld maakt de wig weer
    zichtbaar: wat de klant betaalde (bruto), wat het platform inhield
    (commissie), wat overbleef (netto). Voor de winkel is de wig nul en zijn
    bruto en netto gelijk. `inhouding_pct` is commissie/bruto in procenten,
    of None zonder bruto.
    """

    kanaal: str
    netto: Decimal
    commissie: Decimal
    bruto: Decimal
    inhouding_pct: Decimal | None


def kanaalfinancien(
    dagtotalen_df: pd.DataFrame,
    kanaalkost_df: pd.DataFrame | None,
    tot: pd.Timestamp,
    *,
    dagen: int = 30,
) -> list[Kanaalfinancien]:
    """Per kanaal met omzet in de laatste N kalenderdagen: netto, commissie,
    bruto. Zonder kanaalkosttabel draagt een commissiekanaal geen commissie:
    dan ontbreekt het kanaalkostblok en hoort de reden in het contract —
    netto als bruto presenteren zou de wig verzwijgen."""
    van = tot - pd.Timedelta(days=dagen - 1)
    deel = dagtotalen_df[
        (dagtotalen_df["datum"] >= van) & (dagtotalen_df["datum"] <= tot)
    ]

    uit: list[Kanaalfinancien] = []
    for kanaal, groep in deel.groupby("kanaal"):
        netto = euro(float(groep["omzet"].sum()))
        commissie = euro(0)
        if kanaalkost_df is not None and not kanaalkost_df.empty:
            kost = kanaalkost_df[kanaalkost_df["kanaal"] == kanaal]
            if not kost.empty:
                tarieven = (kost.set_index("maand")["commissie_per_stuk"]
                            .astype(float).sort_index())
                maanden = groep["datum"].map(lambda d: f"{d.year:04d}-{d.month:02d}")
                per_rij = [
                    float(stuks) * tarief_voor(m, tarieven)
                    for stuks, m in zip(groep["stuks"], maanden)
                ]
                commissie = euro(sum(per_rij))
        bruto = euro(netto + commissie)
        inhouding = None
        if bruto > 0 and commissie > 0:
            inhouding = (commissie / bruto * 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        uit.append(Kanaalfinancien(kanaal=str(kanaal), netto=netto,
                                   commissie=commissie, bruto=bruto,
                                   inhouding_pct=inhouding))
    return uit


# --- marge -------------------------------------------------------------------


@dataclass(frozen=True)
class Margebeeld:
    """Omzet min ingevulde kostencriteria, per productgroep en opgeteld.

    De kosten komen uit het kostenmodel (bakkerij.kostenmodel), niet uit een
    bronsysteem; dit beeld zegt daarom hardop welk deel van de omzet gedekt is
    door invoer. `gewogen_pct` weegt uitsluitend over de gedekte omzet — een
    gemiddelde aandikken met groepen waarvan niemand de kosten kent, zou een
    cijfer tonen dat niemand heeft aangeleverd (harde regel 8).

    `rijen` per groep: groep | omzet | aandeel_pct | marge_pct | marge_eur |
    opbouw, waarbij marge_pct en marge_eur None zijn voor een groep zonder
    invoer en `opbouw` een lijst [{criterium, pct, eur}] is (leeg zonder
    invoer). De euro-invariant: per gedekte groep is marge_eur exact de omzet
    in centen min de som van de kostenregels in centen, en de som van de
    gevulde `marge_eur`-rijen == `marge_eur` van het geheel — elke kostregel
    is apart naar centen afgerond, er is geen tweede afronding.

    `per_criterium`: criterium | kost_eur | omzet_basis | groepen_n, in de
    volgorde van het model. `omzet_basis` is de omzet van de groepen waar dát
    criterium is ingevuld; de kost afzetten tegen méér omzet dan waar ze voor
    is opgegeven, zou het percentage kunstmatig drukken.
    """

    rijen: pd.DataFrame
    per_criterium: pd.DataFrame
    totale_omzet: Decimal
    gedekte_omzet: Decimal
    marge_eur: Decimal
    gewogen_pct: Decimal | None
    dekking_pct: Decimal
    dagen: int


def marge_per_groep(
    open_verkopen_df: pd.DataFrame,
    groepen: pd.Series,
    kosten: dict[str, dict[str, Decimal]],
    tot: pd.Timestamp,
    *,
    criteria_volgorde: tuple[str, ...] = (),
    dagen: int = 30,
    kanaal: str = "winkel",
) -> Margebeeld | None:
    """Het margebeeld over de laatste N kalenderdagen van één kanaal.

    `kosten` is groep -> criterium -> percentage van de omzet; de brutomarge
    van een groep is 100 min de som van haar ingevulde criteria. Een som boven
    de 100 geeft een negatieve marge — die wordt getoond en niet weggemoffeld,
    de contractlaag zet er een waarschuwing bij.

    Bewust alleen de winkel als standaard: de ingevulde kosten gelden voor
    winkelprijzen. Deliveroo verkoopt hetzelfde assortiment tegen een andere
    prijs en de canonieke Deliveroo-omzet is bovendien netto van commissie;
    daar dezelfde opbouw op loslaten zou een winst tonen die er niet is.
    `None` betekent:
    geen omzet in het venster, en dat toont de contractlaag als onbeschikbaar.
    """
    per_groep = omzet_per_groep(open_verkopen_df, groepen, tot,
                                dagen=dagen, kanaal=kanaal)
    if per_groep.empty or float(per_groep["omzet"].sum()) <= 0:
        return None

    totaal = euro(float(per_groep["omzet"].sum()))
    rijen = per_groep.assign(
        aandeel_pct=(per_groep["omzet"] / float(totaal) * 100).round(1),
    )

    marge_pcts: list[Decimal | None] = []
    marge_eurs: list[Decimal | None] = []
    opbouwen: list[list[dict]] = []
    for omzet, groep in zip(rijen["omzet"], rijen["groep"]):
        regels = kosten.get(str(groep)) or {}
        # De restgroep heet op het scherm "Overige"/"Autres", maar in de
        # opgeslagen kosteninvoer staat hij onder zijn Nederlandse naam (het
        # formulier bewaart wat het toont, en de invoer is één bestand voor
        # beide talen). Zonder deze terugval zou de Franse boom voor die
        # groep géén marge dragen terwijl de Nederlandse dat wél doet — en
        # de talen beloven dezelfde cijfers.
        if not regels and str(groep) == tl.t("Overige", "Autres"):
            regels = kosten.get("Overige") or {}
        if not regels:
            marge_pcts.append(None)
            marge_eurs.append(None)
            opbouwen.append([])
            continue
        omzet_c = euro(float(omzet))
        opbouw = [
            {"criterium": crit, "pct": pct,
             "eur": euro(float(omzet) * float(pct) / 100)}
            for crit, pct in sorted(
                regels.items(),
                key=lambda kv: (criteria_volgorde.index(kv[0])
                                if kv[0] in criteria_volgorde else len(criteria_volgorde)),
            )
        ]
        marge_pcts.append(Decimal(100) - sum((p["pct"] for p in opbouw),
                                             Decimal(0)))
        marge_eurs.append(omzet_c - sum((p["eur"] for p in opbouw), Decimal(0)))
        opbouwen.append(opbouw)
    rijen["marge_pct"] = marge_pcts
    rijen["marge_eur"] = marge_eurs
    rijen["opbouw"] = opbouwen

    volgorde = list(criteria_volgorde) or sorted(
        {c for regels in kosten.values() for c in regels}
    )
    criterium_rijen = []
    for crit in volgorde:
        kost = Decimal(0)
        basis = Decimal(0)
        n = 0
        for omzet, groep in zip(rijen["omzet"], rijen["groep"]):
            pct = (kosten.get(str(groep)) or {}).get(crit)
            if pct is None:
                continue
            kost += euro(float(omzet) * float(pct) / 100)
            basis += euro(float(omzet))
            n += 1
        if n:
            criterium_rijen.append({"criterium": crit, "kost_eur": kost,
                                    "omzet_basis": basis, "groepen_n": n})
    per_criterium = pd.DataFrame(
        criterium_rijen,
        columns=["criterium", "kost_eur", "omzet_basis", "groepen_n"],
    )

    gedekt = rijen[rijen["marge_pct"].notna()]
    gedekte_omzet = euro(float(gedekt["omzet"].sum())) if not gedekt.empty else euro(0)
    marge_som = sum((m for m in gedekt["marge_eur"]), Decimal(0))
    gewogen = None
    if gedekte_omzet > 0:
        gewogen = (marge_som / gedekte_omzet * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    # Meetdagen uit hetzelfde kalendervenster als de omzet zelf, niet uit een
    # "laatste N open dagen"-venster: dat zijn twee verschillende periodes.
    van = tot - pd.Timedelta(days=dagen - 1)
    meetdagen = open_verkopen_df[
        (open_verkopen_df["kanaal"] == kanaal)
        & (open_verkopen_df["datum"] >= van)
        & (open_verkopen_df["datum"] <= tot)
    ]["datum"].nunique()

    return Margebeeld(
        rijen=rijen.reset_index(drop=True),
        per_criterium=per_criterium,
        totale_omzet=totaal,
        gedekte_omzet=gedekte_omzet,
        marge_eur=euro(marge_som),
        gewogen_pct=gewogen,
        dekking_pct=(gedekte_omzet / totaal * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        ),
        dagen=int(meetdagen),
    )


def as_ticks(maximum: float, stappen: int = 5) -> list[float]:
    """Ronde tickwaarden voor een y-as, van nul tot boven het maximum.

    De as hoort bij de berekening en niet bij het scherm: als de frontend zelf
    een schaal kiest, rekent de frontend, en dat mag niet (harde regel 4).
    """
    if maximum <= 0:
        return [0.0, 1.0]
    ruw = maximum / stappen
    orde = Decimal(10) ** (len(str(int(ruw))) - 1)
    for veelvoud in (1, 2, 2.5, 5, 10):
        stap = float(orde) * veelvoud
        if stap >= ruw:
            break
    hoogste = stap
    while hoogste < maximum:
        hoogste += stap
    aantal = round(hoogste / stap)
    return [i * stap for i in range(aantal + 1)]
