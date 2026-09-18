"""Rolling-origin backtest, afgerekend in euro's.

Bouwen vóór het model. Zonder harnas weet je niet of een model iets doet, en
zonder baselines weet je niet of het beter is dan niets doen.

DRIE REGELS DIE NIET WIJKEN

1. *Nooit willekeurig splitsen.* Train tot dag T, voorspel de volgende open
   dagen, schuif op. Een willekeurige split lekt de toekomst en levert een
   resultaat dat in productie niet terugkomt.

2. *Alles op datum uitgelijnd, nooit op positie.* De vorige versie vergeleek
   voorspelling en werkelijkheid met `zip()`, dus op positie. Op een reeks met
   sluitingsdagen liepen die twee uiteen: gemeten op 12 augustus 2026 vielen bij
   twee van de drie origins de datums niet samen, waardoor een vrijdag-
   voorspelling tegen een maandag-werkelijkheid werd afgerekend. Een harnas dat
   stilzwijgend het verkeerde paar vergelijkt, is erger dan geen harnas: het
   levert een cijfer dat betrouwbaar lijkt. Hier komen de doeldagen daarom uit de
   werkelijkheidsindex zelf, zodat uitlijning per constructie klopt en niet per
   afspraak.

3. *Afrekenen in euro's, niet in MAPE.* MAPE straft fouten op kleine producten
   onevenredig en zegt niets over geld. In fase 1 is de maat de **afwijking in
   euro's omzet**: hoeveel euro zat de prognose ernaast, per dag en in totaal.

WAAROM NIET DE KOST VAN EEN BAKBESLISSING

Dat was de oorspronkelijke maat, en ze is in fase 1 niet te berekenen. Ze vraagt
per product een productiekost en een restwaarde, en vraag 19 stelde vast dat die
niet bestaan: Odoo berekende de kostprijs op alle 1.556.770 kassabonregels en kwam
1.556.054 keer op nul uit. Bovendien is de baklijst op 12 augustus uit de scope
gehaald. De newsvendor-afrekening blijft daarom beschikbaar via `economie=`, voor
de fase waarin de marges er wél zijn, maar ze is niet de kernmaat.

HORIZON IS IN OPEN DAGEN

Een horizon van zeven betekent "de volgende zeven dagen dat de zaak open is",
niet zeven kalenderdagen. Op een gesloten dag is er niets te voorspellen en niets
af te rekenen; die dag meetellen zou het model leren dat er in augustus geen
vraag naar brood is.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: De vaste harnasparameters van het platform. Eén thuis sinds 18 aug 2026:
#: daarvoor definieerden vier bestanden (contract_bouw, backtest_prognose,
#: backtest_rapport, backtest_diagnose) ze elk zelf, en een horizonwijziging
#: in het contract liet het rapport stil de oude meten. Wie hier iets
#: wijzigt, wijzigt de meting van álle rapporten en van het scherm tegelijk.
MIN_TRAIN = 180   # minstens een half jaar open dagen vóór de eerste voorspelling
#
# Deze drie zijn sinds 19 aug 2026 óók de standaardwaarden van elke functie
# hieronder. Daarvoor stond er twee keer een ander getal in dezelfde module:
# `origins` en `evalueer` gingen uit van 90 trainingsdagen, de vier andere van
# 180. Geen enkele aanroeper liet het argument weg, dus het verschil deed
# vandaag niets -- maar het wachtte op de eerste aanroep die dat wél doet, en
# die zou dan stil een half jaar minder historiek meten dan het contract.
STAP = 7          # rolling origin schuift per week
HORIZON = 7       # zeven open dagen vooruit (zie de kop hierboven)

from bakkerij.decide.newsvendor import Economie, kost_van_beslissing

# Een voorspeller krijgt de historiek en de exacte doeldagen, en geeft een reeks
# terug die op diezelfde dagen geïndexeerd is.
Voorspeller = Callable[[pd.Series, pd.DatetimeIndex], pd.Series]


@dataclass(frozen=True)
class Venster:
    """Eén origin: waarop getraind is, welke dagen voorspeld worden, en de waarheid."""

    train: pd.Series
    doeldagen: pd.DatetimeIndex
    werkelijk: pd.Series


@dataclass
class Resultaat:
    naam: str
    n_dagen: int
    som_werkelijk: float
    som_absolute_fout: float
    som_fout: float
    mediane_absolute_fout: float
    # Alleen gevuld als er een `economie` is meegegeven. Blijft None zolang de
    # kostprijzen niet bestaan (vraag 19), en dat is de eerlijke staat.
    kost_euro: float | None = None

    @property
    def mae_euro(self) -> float:
        """Gemiddelde afwijking per dag, in euro's."""
        return self.som_absolute_fout / max(self.n_dagen, 1)

    @property
    def wape(self) -> float:
        """Totale afwijking als aandeel van de totale werkelijke omzet.

        De relatieve maat die bij omzet hoort: één percentage dat je kan
        vergelijken over periodes met verschillende omzetniveaus, zonder de
        vertekening van MAPE op kleine dagen.
        """
        return self.som_absolute_fout / self.som_werkelijk if self.som_werkelijk else 0.0

    @property
    def bias_euro(self) -> float:
        """Systematisch te hoog (positief) of te laag (negatief), per dag.

        Even belangrijk als de afwijking zelf: een prognose die structureel
        8% te hoog zit, is bruikbaar zodra je dat weet, en misleidend zolang niet.
        """
        return self.som_fout / max(self.n_dagen, 1)

    def regel(self) -> str:
        return (
            f"  {self.naam:<22} {self.mae_euro:>9.0f} EUR/dag  "
            f"WAPE {self.wape:>6.1%}  bias {self.bias_euro:>+8.0f}  "
            f"mediaan {self.mediane_absolute_fout:>8.0f}  n={self.n_dagen}"
        )


def origins(
    reeks: pd.Series, *, min_train: int = MIN_TRAIN, stap: int = STAP, horizon: int = HORIZON
) -> Iterator[Venster]:
    """Genereer vensters over de hele historiek.

    `reeks` bevat uitsluitend gemeten open dagen, op datum gesorteerd. De
    doeldagen worden uit de index van de werkelijkheid gehaald, niet uit een
    `date_range`: daarmee is uitgesloten dat er een dag voorspeld wordt die niet
    gemeten is, of dat voorspelling en werkelijkheid uit elkaar lopen.

    Meerdere origins, verspreid over de historiek, zodat het seizoen niet uit één
    toevallige periode beoordeeld wordt.
    """
    if not isinstance(reeks.index, pd.DatetimeIndex):
        raise TypeError("De reeks moet een DatetimeIndex hebben.")
    if not reeks.index.is_monotonic_increasing:
        raise ValueError("De reeks moet op datum gesorteerd zijn.")
    if reeks.index.has_duplicates:
        raise ValueError("De reeks heeft dubbele datums; aggregeer eerst per dag.")

    n = len(reeks)
    if n < min_train + horizon:
        raise ValueError(
            f"Te weinig open dagen: {n}, minstens {min_train + horizon} nodig "
            f"(min_train={min_train} + horizon={horizon})."
        )

    for eind in range(min_train, n - horizon + 1, stap):
        werkelijk = reeks.iloc[eind : eind + horizon]
        yield Venster(
            train=reeks.iloc[:eind],
            doeldagen=werkelijk.index,
            werkelijk=werkelijk,
        )


def evalueer(
    reeks: pd.Series,
    voorspeller: Voorspeller,
    *,
    naam: str = "model",
    min_train: int = MIN_TRAIN,
    stap: int = STAP,
    horizon: int = HORIZON,
    economie: Economie | None = None,
    beslisregel: Callable[[float], int] | None = None,
    alleen_dagen: pd.DatetimeIndex | None = None,
) -> Resultaat:
    """Reken één voorspeller af over de hele historiek, in euro's afwijking.

    Geef `economie` mee om daarnaast de kost van een bakbeslissing te berekenen.
    Dat is de maat van de beslislaag en die hoort bij een latere fase, want de
    kostprijzen bestaan vandaag niet (vraag 19).

    `alleen_dagen` beperkt de AFREKENING tot die datums; getraind en voorspeld
    wordt zoals altijd. Nodig voor een correctie die maar een handvol dagen per
    jaar raakt (feestdagen): in het totaalcijfer verdrinkt zo'n effect, en dan
    zou de conclusie "voegt niets toe" een meetfout zijn, geen bevinding.
    """
    absolute, ondertekend = [], []
    som_werkelijk = 0.0
    kost = 0.0
    regel = beslisregel or (lambda x: round(max(x, 0.0)))
    afrekenset = None if alleen_dagen is None else set(alleen_dagen)

    for venster in origins(reeks, min_train=min_train, stap=stap, horizon=horizon):
        voorspeld = voorspeller(venster.train, venster.doeldagen)

        # De uitlijning die de vorige versie miste. Dit is geen defensief
        # extraatje: het is de enige reden dat het cijfer hieronder iets betekent.
        if not voorspeld.index.equals(venster.doeldagen):
            raise ValueError(
                f"'{naam}' gaf een voorspelling op andere dagen dan gevraagd. "
                f"Gevraagd: {venster.doeldagen[0].date()} t/m "
                f"{venster.doeldagen[-1].date()} ({len(venster.doeldagen)} dagen)."
            )

        if afrekenset is None:
            afgerekend, echt_af = voorspeld, venster.werkelijk
        else:
            masker = venster.doeldagen.isin(afrekenset)
            if not masker.any():
                continue
            afgerekend, echt_af = voorspeld[masker], venster.werkelijk[masker]

        fout = afgerekend.to_numpy(dtype=float) - echt_af.to_numpy(dtype=float)
        absolute.extend(np.abs(fout))
        ondertekend.extend(fout)
        som_werkelijk += float(echt_af.sum())

        if economie is not None:
            # Dezelfde afrekenset als de foutmaat, anders meten de twee maten
            # over verschillende dagen en is de vergelijking ertussen zinloos.
            for pred, echt in zip(afgerekend.to_numpy(dtype=float),
                                  echt_af.to_numpy(dtype=float),
                                  strict=True):
                kost += kost_van_beslissing(regel(pred), echt, economie)

    return Resultaat(
        naam=naam,
        n_dagen=len(absolute),
        som_werkelijk=som_werkelijk,
        som_absolute_fout=float(np.sum(absolute)),
        som_fout=float(np.sum(ondertekend)),
        mediane_absolute_fout=float(np.median(absolute)) if absolute else 0.0,
        kost_euro=kost if economie is not None else None,
    )


def per_horizon(
    reeks: pd.Series,
    voorspeller: Voorspeller,
    *,
    onder: float = 0.10,
    boven: float = 0.90,
    min_train: int = MIN_TRAIN,
    stap: int = STAP,
    horizon: int = HORIZON,
) -> pd.DataFrame:
    """De fout per horizonstap: de onzekerheid van overmorgen is niet die van morgen.

    Eén gepoolde band over h=1 t/m 7 is te breed voor morgen en te smal voor
    over een week. Hier wordt per stap (1e open dag vooruit, 2e, ...) apart
    gemeten: n, wape, mae, bias, en de relatieve residukwantielen `q_onder`
    en `q_boven` waaruit de contractlaag een band per dag kan bouwen.

    Residuen zijn relatief: (voorspeld - werkelijk) / werkelijk, alleen op
    dagen met werkelijke omzet boven nul.
    """
    per_stap: dict[int, list[tuple[float, float]]] = {h: [] for h in range(1, horizon + 1)}
    for venster in origins(reeks, min_train=min_train, stap=stap, horizon=horizon):
        voorspeld = voorspeller(venster.train, venster.doeldagen)
        for h, (p, w) in enumerate(
            zip(voorspeld.to_numpy(dtype=float),
                venster.werkelijk.to_numpy(dtype=float), strict=True),
            start=1,
        ):
            per_stap[h].append((p, w))

    rijen = []
    for h, paren in per_stap.items():
        if not paren:
            continue
        p = np.array([x for x, _ in paren])
        w = np.array([x for _, x in paren])
        fout = p - w
        relatief = pd.Series([(pi - wi) / wi for pi, wi in paren if wi > 0])
        rijen.append({
            "stap": h,
            "n": len(paren),
            "wape": float(np.abs(fout).sum() / w.sum()) if w.sum() else 0.0,
            "mae": float(np.abs(fout).mean()),
            "bias": float(fout.mean()),
            "q_onder": float(relatief.quantile(onder)) if len(relatief) else float("nan"),
            "q_boven": float(relatief.quantile(boven)) if len(relatief) else float("nan"),
        })
    return pd.DataFrame(rijen)


#: Minstens zoveel eerdere origins voordat de dekkingsmeting een band durft te
#: bouwen. Kwantielen op een handvol residuen zijn zelf ruis.
MIN_ORIGINS_VOOR_BAND = 10


def dekking(
    reeks: pd.Series,
    voorspeller: Voorspeller,
    *,
    onder: float = 0.10,
    boven: float = 0.90,
    min_train: int = MIN_TRAIN,
    stap: int = STAP,
    horizon: int = HORIZON,
) -> pd.DataFrame:
    """Hoe vaak de werkelijkheid binnen de band viel — out-of-sample.

    De valkuil van een dekkingsmeting is zelfbevestiging: wie de kwantielen op
    dezelfde residuen meet als waarop hij de dekking toetst, vindt per
    constructie ongeveer het beloofde percentage. Hier wordt de band voor
    origin k gebouwd uit de residuen van origins 1 t/m k-1, en pas geteld
    vanaf MIN_ORIGINS_VOOR_BAND eerdere origins. Een 10-90-band hoort dan
    ~80% te dekken; meet hij 92%, dan is de band te ruim en dat is een
    bevinding, geen geruststelling.

    Uit: DataFrame met per stap n, binnen_band (aandeel), beloofd (b.v. 0.8).
    """
    beloofd = boven - onder
    residuen: dict[int, list[float]] = {h: [] for h in range(1, horizon + 1)}
    treffers: dict[int, list[bool]] = {h: [] for h in range(1, horizon + 1)}
    n_origins = 0

    for venster in origins(reeks, min_train=min_train, stap=stap, horizon=horizon):
        voorspeld = voorspeller(venster.train, venster.doeldagen)
        paren = list(zip(voorspeld.to_numpy(dtype=float),
                         venster.werkelijk.to_numpy(dtype=float), strict=True))

        if n_origins >= MIN_ORIGINS_VOOR_BAND:
            for h, (p, w) in enumerate(paren, start=1):
                eerdere = pd.Series(residuen[h])
                if w <= 0 or eerdere.empty:
                    continue
                q_o, q_b = eerdere.quantile(onder), eerdere.quantile(boven)
                # Een residu van -20% betekent te laag voorspeld, dus de
                # grenzen draaien om (zelfde omrekening als band_per_stap).
                laag, hoog = p / (1 + q_b), p / (1 + q_o)
                treffers[h].append(laag <= w <= hoog)

        for h, (p, w) in enumerate(paren, start=1):
            if w > 0:
                residuen[h].append((p - w) / w)
        n_origins += 1

    rijen = [
        {
            "stap": h,
            "n": len(uitkomsten),
            "binnen_band": float(np.mean(uitkomsten)) if uitkomsten else float("nan"),
            "beloofd": beloofd,
        }
        for h, uitkomsten in treffers.items()
    ]
    return pd.DataFrame(rijen)


#: De kandidaat-kwantielparen voor de bandkalibratie, smal naar breed. De
#: nominale namen (10-90, 5-95, ...) zijn hier niet de belofte; de belofte is
#: de out-of-sample gemeten dekking, en die kiest.
KALIBRATIE_KANDIDATEN: tuple[tuple[float, float], ...] = (
    (0.10, 0.90), (0.075, 0.925), (0.05, 0.95), (0.025, 0.975),
)


@dataclass(frozen=True)
class Kalibratie:
    """De gekozen kwantielen met hun out-of-sample gemeten dekking."""

    onder: float
    boven: float
    doel: float
    gemeten: float  # gewogen gemiddelde dekking over de stappen
    dekking: pd.DataFrame  # de meting per stap, zoals dekking() ze geeft


def kalibreer_kwantielen(
    reeks: pd.Series,
    voorspeller: Voorspeller,
    *,
    doel: float = 0.80,
    tolerantie: float = 0.05,
    kandidaten: tuple[tuple[float, float], ...] = KALIBRATIE_KANDIDATEN,
    min_train: int = MIN_TRAIN,
    stap: int = STAP,
    horizon: int = HORIZON,
) -> Kalibratie:
    """Kies de smalste kwantielband die out-of-sample (bijna) het doel dekt.

    De meting van 13 augustus 2026 liet zien dat een 10-90-band uit
    in-sample-residuen out-of-sample maar 56 à 74% dekt waar 80% bedoeld is:
    kwantielen op de eigen trainingsfouten onderschatten wat er buiten de
    training gebeurt. In plaats van de band te verzinnen wordt hij hier
    gekalibreerd: elke kandidaat wordt met `dekking()` out-of-sample gemeten
    (band voor origin k uit origins 1 t/m k-1, dus geen zelfbevestiging), en
    de smalste kandidaat die minstens `doel - tolerantie` haalt wint. Haalt
    geen enkele het, dan wint de breedste — en de gemeten dekking gaat mee
    naar het contract, zodat het scherm zegt wat de band wérkelijk dekt.
    """
    if not 0 < doel < 1:
        raise ValueError("doel moet tussen 0 en 1 liggen.")
    keuze: Kalibratie | None = None
    for onder, boven in kandidaten:
        meting = dekking(reeks, voorspeller, onder=onder, boven=boven,
                         min_train=min_train, stap=stap, horizon=horizon)
        bruikbaar = meting.dropna(subset=["binnen_band"])
        bruikbaar = bruikbaar[bruikbaar["n"] > 0]
        if bruikbaar.empty:
            continue
        gewogen = float(
            (bruikbaar["binnen_band"] * bruikbaar["n"]).sum()
            / bruikbaar["n"].sum()
        )
        keuze = Kalibratie(onder=onder, boven=boven, doel=doel,
                           gemeten=gewogen, dekking=meting)
        if gewogen >= doel - tolerantie:
            return keuze
    if keuze is None:
        raise ValueError(
            "Geen enkele kandidaat leverde een meetbare dekking op; te weinig "
            f"origins (minstens {MIN_ORIGINS_VOOR_BAND} nodig)."
        )
    return keuze


def trackrecord(
    reeks: pd.Series,
    voorspeller: Voorspeller,
    *,
    dagen: int = 28,
    min_train: int = MIN_TRAIN,
    horizon: int = HORIZON,
) -> pd.DataFrame:
    """Voorspeld naast werkelijk voor de laatste gemeten open dagen.

    De vraag die een CFO over een model stelt is niet hoe het werkt maar of
    het de vorige keer klopte. Elke dag hier is voorspeld door de origin die
    vóór die dag lag (stap = horizon, dus de vensters verdelen de reeks en
    elke dag is precies één keer, out-of-sample, voorspeld — zoals productie
    hem getoond zou hebben, 1 tot `horizon` dagen vooruit).

    Uit: DataFrame datum, verwacht, werkelijk, stap (hoeveel open dagen
    vooruit die voorspelling keek).
    """
    rijen = []
    for venster in origins(reeks, min_train=min_train, stap=horizon, horizon=horizon):
        voorspeld = voorspeller(venster.train, venster.doeldagen)
        for h, (dag, p, w) in enumerate(
            zip(venster.doeldagen, voorspeld.to_numpy(dtype=float),
                venster.werkelijk.to_numpy(dtype=float), strict=True),
            start=1,
        ):
            rijen.append({"datum": dag, "verwacht": p, "werkelijk": w, "stap": h})

    df = pd.DataFrame(rijen)
    if df.empty:
        return df
    # Eén rij per datum kan dubbel bestaan als de laatste origin overlapt;
    # de jongste voorspelling (kleinste stap) wint, zoals productie ze toonde.
    df = df.sort_values(["datum", "stap"]).drop_duplicates("datum", keep="first")
    return df.tail(dagen).reset_index(drop=True)


def band_per_stap(punt: pd.Series, stappen: pd.DataFrame) -> pd.DataFrame:
    """Puntvoorspelling plus band, met de kwantielen van de eigen horizonstap.

    De eerste voorspelde dag krijgt de band van stap 1, de tweede die van
    stap 2, enzovoort: morgen is beter te voorspellen dan over een week, en
    de band hoort dat te tonen (zie `per_horizon`). Loopt het venster verder
    dan de gemeten stappen, dan draagt de rest de band van de laatste stap —
    breder wordt er niet gemeten, smaller mag niet verzonnen worden.

    Een residu van -20% betekent te laag voorspeld, dus de grenzen draaien
    om. Onder nul kan omzet niet. (Tot 18 augustus 2026 verwees dit naar
    `berekening.prognose`; dat tweede, ongebruikte prognosepad is verwijderd
    en dit is nu de enige plek waar de band om een punt wordt gelegd.)
    """
    if stappen.empty:
        raise ValueError("Geen stapkwantielen: draai eerst per_horizon.")
    op_stap = stappen.set_index("stap").sort_index()
    laatste = op_stap.index.max()
    rijen = []
    for i, (dag, verwacht) in enumerate(punt.items(), start=1):
        rij = op_stap.loc[min(i, laatste)]
        rijen.append({
            "datum": dag,
            "verwacht": float(verwacht),
            "onder": max(float(verwacht) / (1 + float(rij["q_boven"])), 0.0),
            "boven": max(float(verwacht) / (1 + float(rij["q_onder"])), 0.0),
        })
    return pd.DataFrame(rijen)


def vergelijk(resultaten: list[Resultaat]) -> str:
    """Rangschik op afwijking in euro's, en benoem of het verschil iets betekent."""
    if not resultaten:
        return "Geen resultaten."
    gesorteerd = sorted(resultaten, key=lambda r: r.som_absolute_fout)
    regels = [
        "",
        "Backtest, gerangschikt op afwijking in euro's omzet:",
        "-" * 92,
        *[r.regel() for r in gesorteerd],
    ]

    beste = gesorteerd[0]
    tweede = gesorteerd[1] if len(gesorteerd) > 1 else None
    if tweede and tweede.som_absolute_fout > 0:
        winst = (
            tweede.som_absolute_fout - beste.som_absolute_fout
        ) / tweede.som_absolute_fout
        regels += ["", f"'{beste.naam}' zit {winst:.1%} dichter dan '{tweede.naam}'."]
        if winst < 0.05:
            regels.append(
                "Onder de vijf procent. Dat is binnen de ruis van dit soort data: "
                "rapporteer het als gelijkwaardig en kies dan de eenvoudigste. "
                "Uitlegbaar wint van marginaal accurater."
            )
    return "\n".join(regels)
