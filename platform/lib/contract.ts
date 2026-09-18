/**
 * Het gebonden contract. De contractbouw (scripts/contract_bouw.py) schrijft
 * exact deze vorm naar platform/contract/, en de echte API van fase 2 geeft
 * haar straks ongewijzigd terug; lib/laadContract.ts is de enige lezer.
 *
 * Twee soorten waarden:
 *  - Bedragen, aantallen en percentages zijn STRINGS met punt-decimaal
 *    ("1234.56", "-4.2"). De frontend rekent er nooit mee; ze gaan door
 *    lib/format.ts en worden getoond. Nooit floating point in het contract.
 *  - `number` komt uitsluitend voor als plotgeometrie in grafiekreeksen:
 *    de frontend schaalt die naar pixels, meer niet. Elk label dat een mens
 *    leest, staat kant-en-klaar in de data.
 */

export type Onbeschikbaar = {
  veld: string;
  reden: string;
};

/**
 * De envelope draagt twee tijdstippen, en het verschil ertussen is geen detail:
 *  - `bijgewerkt_op` is wanneer dit antwoord gebouwd is (verwerkingsmoment).
 *  - `gemeten_tot` is de jongste gemeten open winkeldag: tot daar lopen de
 *    cijfers. Die twee kunnen dagen uiteenlopen wanneer een synchronisatie
 *    achterloopt, en dan is `bijgewerkt_op` alleen géén uitspraak over de
 *    versheid van de cijfers.
 * `gemeten_tot` is null wanneer er geen gemeten open winkeldag is; de
 * voettekst zegt dat dan met zoveel woorden (harde regel 8), zie lib/versheid.ts.
 */
export type Antwoord<T> = {
  versie: number;
  bijgewerkt_op: string; // ISO 8601, verwerkingsmoment
  gemeten_tot: string | null; // ISO-datum van de jongste gemeten open winkeldag
  bron: string[];
  onbeschikbaar: Onbeschikbaar[];
  /**
   * De briefing bovenaan het scherm. Ze hoort bij de envelope en niet bij
   * `data`, want het is een uitspraak óver dit scherm — net als
   * `onbeschikbaar` — en geen cijfer dat erop staat. Altijd aanwezig; een
   * scherm zonder signalen draagt een lege puntenlijst.
   */
  briefing: Briefing;
  data: T;
};

/** Kerncijfer: groot zwart getal met een verschil t.o.v. vorig jaar. */
export type KerncijferData = {
  label: string;
  waarde: string; // machinewaarde, bv. "12480.50"
  soort: "euro" | "aantal";
  verschil: string | null; // percentage als machinewaarde, bv. "-4.2"
  richting: "op" | "neer" | null;
};

/** Eén punt in een grafiek: y is plotgeometrie, x is het aslabel. */
export type Punt = {
  x: string;
  y: number;
  /**
   * Het aantal gemeten dagen achter dit punt. Staat alleen op punten die een
   * gemiddelde over dagen zijn (het weekdagprofiel), en is daar verplicht —
   * zie `MeetPunt`. Een gemiddelde over twee dagen leest anders dan een
   * gemiddelde over dertig, en dat mag het scherm niet verzwijgen.
   */
  meetdagen?: number;
};

/** Een punt waarvan het aantal meetdagen vaststaat. */
export type MeetPunt = Punt & { meetdagen: number };

export type As = {
  ticks: { y: number; label: string }[]; // aslabels kant-en-klaar aangeleverd
};

export type Reeks = {
  naam: string;
  kleur: "bordeaux" | "warmgrijs" | "geel";
  punten: Punt[];
};

export type Lijndata = {
  reeksen: Reeks[];
  y_as: As;
  band?: { x: string; onder: number; boven: number }[]; // prognose
};

export type Staafdata = {
  reeksen: Reeks[];
  y_as: As;
};

/** Staafdata waarvan elk punt zijn aantal meetdagen meebrengt. */
export type MeetStaafdata = {
  reeksen: (Omit<Reeks, "punten"> & { punten: MeetPunt[] })[];
  y_as: As;
};

export type Tabeldata = {
  kolommen: string[];
  rijen: string[][]; // cellen al opgemaakt door de pagina, via lib/format.ts
  uitlijning: ("links" | "rechts")[];
};

/**
 * Eén regel microcontext onder een grafiek: "Beste dag, 26 jul  € 2.481,00".
 * Het label is kant-en-klaar; de waarde is een machinewaarde die door
 * lib/format.ts gaat, met `soort` als de te kiezen opmaak. Bij "verschil"
 * hoort een richting, en die komt uit teken en pijl, nooit uit kleur.
 */
export type ContextItem = {
  label: string;
  waarde: string;
  soort: "euro" | "aantal" | "verschil";
  richting: "op" | "neer" | null;
};

/* ---- de briefing -------------------------------------------------------- */

/**
 * Eén punt uit de briefing bovenaan een scherm: wat er opvalt, waarom, en wat
 * er nodig is van wie. Signalering, geen advies — en elk woord komt uit de
 * berekeningslaag. De component toont het punt en verzint er niets bij: geen
 * zin, geen drempel, geen oordeel (harde regel 4).
 *
 * `bedrag` is een machinewaarde zoals overal elders ("1234.56"), en gaat door
 * lib/format.ts; `soort` zegt welke opmaak. `richting` komt uit teken en pijl,
 * nooit uit kleur.
 *
 * De status komt twee keer: `status` is de machinesleutel waarop gesorteerd
 * wordt, `statuswoord` is het woord dat de mens leest. Dat woord is het
 * volledige onderscheid op het scherm — de huisstijl kent geen betekeniskleur,
 * dus er is geen rood voor "actie" en geen groen voor "goed". Omdat het woord
 * uit het contract komt en niet uit de component, staat het meteen in de taal
 * van de lezer (zie platform/contract/<taal>/).
 */
export type BriefingPunt = {
  kop: string;
  waarom: string;
  nodig: string | null; // null = niets nodig
  bedrag: string | null; // machinewaarde, bv. "1234.56"; null = geen bedrag
  soort: "euro" | "aantal" | "verschil" | null;
  eenheid: string | null; // alleen bij soort "aantal": wat er geteld wordt ("dagen")
  richting: "op" | "neer" | null;
  status: "goed" | "let_op" | "actie"; // machinesleutel, voor sortering
  statuswoord: string; // het woord dat de mens leest
  /**
   * Dit punt gaat over de aanvoer en niet over dít scherm, en staat daarom
   * woord voor woord op elk scherm: de sluiting, de achterstand, een bron die
   * stilvalt. Op een scherm verandert dat niets — daar hoort zo'n punt te
   * staan, want wie op Productmix binnenkomt moet óók weten dat de zaak dicht
   * is. In het rapport, dat de schermen achter elkaar zet, staat het één keer:
   * zie de regel voor `data-gedeeld` in globals.css.
   *
   * Optioneel: een contract van vóór 19 augustus 2026 draagt het veld niet, en
   * "niet gemerkt" is daar hetzelfde als "niet gedeeld".
   */
  gedeeld?: boolean;
};

/**
 * De briefing van één scherm. `leeg` is geen bijzaak: een scherm zonder
 * signalen is de normale, goede toestand, en die toestand hoort uitgeschreven
 * te worden in plaats van als stilte te blijven hangen — anders is "alles in
 * orde" niet te onderscheiden van "de briefing is stukgelopen".
 */
export type Briefing = {
  punten: BriefingPunt[];
  leeg: string; // de zin die getoond wordt als er geen punten zijn
};

/* ---- de CFO-metrieken --------------------------------------------------- */

/**
 * Eén term in een ontbinding van een gemeten verschil.
 *
 * `uitleg` staat in het contract en niet in de component, omdat het scherm geen
 * woorden bij een cijfer mag verzinnen — net zomin als het cijfers bij woorden
 * mag verzinnen. Richting komt uit het teken en de pijl, nooit uit kleur.
 */
export type OntbindingsTerm = {
  label: string;
  waarde: string; // machinewaarde in euro, met teken
  uitleg: string;
  richting: "op" | "neer" | null;
};

/**
 * Een gemeten verschil en de termen waarin het uiteenvalt. De belofte van deze
 * vorm: de termen tellen exact op tot `verschil`, op de cent. De contractlaag
 * rekent dat na vóór ze het antwoord bouwt, dus de component mag optellen tonen
 * zonder zelf te rekenen.
 */
export type Ontbinding = {
  verschil: { label: string; waarde: string; richting: "op" | "neer" | null };
  termen: OntbindingsTerm[];
  toelichting: string;
};

/**
 * Omzet = klanten × mandje. Eén bon is één klant, ook als er drie broden op
 * staan; die telling komt uit een aparte extractie en kan ontbreken, en dan is
 * dit hele blok null met de reden in `onbeschikbaar`.
 */
export type BonritmeData = {
  kengetallen: ContextItem[];
  /** Null wanneer de twee vensters niet even veel meetdagen tellen. */
  ontbinding: Ontbinding | null;
  toelichting: string;
};

/** Het aandeel van één weekdag in de omzet van het venster. */
export type WeekdagAandeel = {
  weekdag: string; // "za"
  naam: string; // "zaterdag"
  aandeel: string; // percentage als machinewaarde
  meetdagen: number;
};

export type WeekdagmixData = {
  rijen: WeekdagAandeel[];
  toelichting: string;
};

/**
 * Eén volledige kalenderweek. `omzet` is null wanneer er in die week geen open
 * winkeldag gemeten is — een sluiting is geen week met nul omzet. `open_dagen`
 * staat erbij omdat een korte week geen slechte week is.
 */
export type WeekRij = {
  label: string; // "14 jul – 20 jul"
  van: string; // ISO-datum van de maandag
  omzet: string | null;
  omzet_per_dag: string | null;
  open_dagen: number;
};

export type WekenData = {
  rijen: WeekRij[];
  toelichting: string;
};

/** Omzet per gemeten open dag per maand. Een maand zonder meting krijgt geen
 * staaf (meetdagen 0), en de reden staat in `onbeschikbaar`. */
export type MaandritmeData = {
  grafiek: MeetStaafdata;
  toelichting: string;
};

/** Eén dag die hard afwijkt van wat op diezelfde weekdag gebruikelijk is. */
export type AfwijkendeDag = {
  datum: string; // ISO-datum
  label: string; // "zaterdag 12 jul"
  omzet: string;
  gebruikelijk: string; // de mediaan van die weekdag
  verschil: string; // met teken
  richting: "op" | "neer" | null;
};

export type AfwijkendeDagenData = {
  rijen: AfwijkendeDag[];
  toelichting: string;
};

/** Hoe zwaar de omzet op de kop van het assortiment leunt (Pareto). */
export type ConcentratieData = {
  /** De drie kolomkoppen, vertaald door de contractbouw (harde regel 4:
   * de UI plakt geen eigen tekst achter contractwaarden). */
  kolommen: string[];
  rijen: {
    drempel: string; // "80 % van de omzet"
    producten: string;
    label: string; // "29 producten" / "29 produits", uit de contractbouw
    aandeel_assortiment: string; // percentage als machinewaarde
  }[];
  totaal_producten: string;
  /** Omzet van alles buiten de 95%-kop, en hoeveel producten dat zijn. */
  staart_omzet: string;
  staart_producten: string;
  toelichting: string;
};

/**
 * Eén voorgebakken venster uit de periodekubus. De periodekiezer op het
 * scherm doet niets anders dan kiezen welk venster getoond wordt: elke reeks,
 * elke as en elke vergelijking is hier al gerekend (harde regel 4).
 */
export type PeriodeVenster = {
  sleutel: string; // "d7" | "d30" | "w13" | "m12" | "jaar" — nieuwe mogen erbij
  label: string; // knoptekst, kant-en-klaar
  soort: "lijn" | "staaf";
  grafiek: Lijndata | Staafdata | null;
  context: ContextItem[];
  toelichting: string;
  /**
   * Het venster dat de kiezer opent. Staat hier en niet in de volgorde van de
   * lijst: die loopt van kort naar lang, terwijl het openingsvenster 30 dagen
   * blijft. Ontbreekt de vlag overal — een contract van vóór dit veld — dan
   * valt de kiezer terug op het eerste venster, het gedrag van voorheen.
   */
  standaard?: boolean;
};

/* ---- per scherm ------------------------------------------------------- */

export type OverzichtData = {
  kerncijfers: KerncijferData[];
  omzetverloop: Lijndata;
  omzetverloop_context: ContextItem[];
  /** De periodekubus achter de periodekiezer; d30 spiegelt omzetverloop. */
  periodes: PeriodeVenster[];
  weekdagprofiel: {
    grafiek: MeetStaafdata;
    toelichting: string;
  };
  jaarvergelijking: Staafdata;
  /**
   * De vier metrieken die over de zaak als geheel gaan. Elk mag null zijn; de
   * reden staat dan in `onbeschikbaar` onder het gelijknamige veld, en het
   * scherm toont een onbeschikbaar-vak in plaats van een leeg vlak.
   */
  bonritme: BonritmeData | null;
  weekdagmix: WeekdagmixData | null;
  weken: WekenData | null;
  maandritme: MaandritmeData | null;
  afwijkende_dagen: AfwijkendeDagenData | null;
};

export type KanaalBlok = {
  kanaal: "winkel" | "deliveroo";
  naam: string;
  omzet_30d: string | null; // machinewaarde
  aandeel: string | null; // percentage als machinewaarde
  stuks_30d: string | null;
  gem_dagomzet: string | null; // per gemeten dag van dit kanaal
  meetdagen: string | null;
  verloop: Lijndata | null;
  /**
   * De financiële wig: wat de klant betaalde (bruto), wat het platform
   * inhield (commissie), wat er overbleef (netto). Voor de winkel is de wig
   * nul (bruto == netto, commissie "0.00"); null wanneer de wig niet te
   * berekenen is — de reden staat dan in `onbeschikbaar` (kanaal.<kanaal>.kost).
   */
  bruto_30d: string | null;
  commissie_30d: string | null;
  netto_30d: string | null;
  inhouding_pct: string | null; // commissie/bruto, alleen bij een echte wig
};

export type KanalenData = {
  kanalen: KanaalBlok[];
};

/** Eén rij in de verschuivingstabel: dit product tegenover de periode ervoor. */
export type VerschuivingRij = {
  naam: string;
  omzet_nu: string;
  omzet_vorig: string;
  verschil: string; // in euro, met teken
  verschil_pct: string | null; // null bij een product zonder vorige omzet
  nieuw: boolean;
};

/** Eén groep in de drill-down: de dragende producten plus een rest-regel,
 * zodat de som van de zichtbare rijen de groepsomzet blijft. */
export type GroepDetail = {
  groep: string;
  omzet_30d: string;
  aandeel: string | null; // aandeel van de groep in de kanaalomzet
  producten: {
    naam: string;
    stuks: string;
    omzet: string;
    aandeel_in_groep: string;
  }[];
  /** `label` komt vertaald uit de contractbouw ("overige 23 producten" /
   * "23 autres produits"); `producten` blijft de machinewaarde. */
  rest: { label: string; producten: string; omzet_30d: string } | null;
};

export type ProductenData = {
  top: {
    naam: string;
    groep: string;
    stuks: string;
    omzet: string;
    aandeel: string;
  }[];
  groepen: Staafdata;
  /** De drill-down groep -> product; volgorde = zwaarste groep eerst. */
  groepen_detail: GroepDetail[];
  verschuiving: {
    stijgers: VerschuivingRij[];
    dalers: VerschuivingRij[];
    toelichting: string;
  };
  /**
   * De twee metrieken die per product gerekend worden: waar de omzet op leunt,
   * en of een verandering uit stuks of uit prijs komt. Null met een reden in
   * `onbeschikbaar` wanneer er niets te verdelen of niets te vergelijken valt.
   */
  concentratie: ConcentratieData | null;
  prijs_volume: Ontbinding | null;
};

/** Eén kostregel in de opbouw van een groep: welk criterium hoeveel wegneemt. */
export type MargeKostRegel = {
  criterium: string;
  pct: string; // percentage als machinewaarde
  kost_30d: string; // machinewaarde in euro
};

/** Eén productgroep op het margescherm én in het invoerformulier. De rij
 * bestaat ook zonder ingevulde kosten: het formulier op Instellingen leest
 * hieruit welke groepen er zijn en hoeveel omzet erachter zit. */
export type MargeGroepRij = {
  groep: string;
  omzet_30d: string; // machinewaarde
  aandeel: string; // percentage als machinewaarde
  marge_pct: string | null; // null zolang niemand deze groep invulde
  marge_30d: string | null;
  /** De opbouw achter marge_pct; leeg zolang de groep geen invoer heeft. */
  kosten: MargeKostRegel[];
};

/** Eén criterium uit het menu dat de beheerder zelf samenstelt. */
export type MargeCriterium = { naam: string; omschrijving: string };

/**
 * De kostenopbouw over de gedekte omzet: omzet min elk criterium is de
 * brutomarge, sluitend op de cent. `pct_gewogen` weegt per criterium alleen
 * over de omzet van de groepen waar dat criterium is ingevuld.
 */
export type MargeKostenopbouw = {
  omzet_30d: string;
  kosten_30d: string;
  marge_30d: string;
  per_criterium: {
    criterium: string;
    kost_30d: string;
    pct_gewogen: string;
    groepen_n: number;
  }[];
  toelichting: string;
};

export type MargeKern = {
  gewogen_pct: string;
  marge_30d: string;
  gedekte_omzet_30d: string;
  dekking_pct: string;
  meetdagen: number;
  toelichting: string;
};

/**
 * `kern` en `staaf` zijn null zolang er geen enkele marge is ingevuld; de
 * reden staat dan in `onbeschikbaar` onder `marge_per_groep`. Het lege object
 * is de vorm van vóór de invoerroute en blijft geldig voor een antwoord
 * zonder verkoopdata.
 */
export type MargeData =
  | {
      kern: MargeKern | null;
      per_groep: MargeGroepRij[];
      staaf: Staafdata | null;
      /** Het criteriamenu: ingevuld door de beheerder, of de suggesties. */
      criteria: MargeCriterium[];
      criteria_bron: "ingevuld" | "suggestie";
      kostenopbouw: MargeKostenopbouw | null;
    }
  | Record<string, never>;

/**
 * Het trackrecord van de prognose: wat het model voorspelde tegenover wat er
 * gemeten is, over de afgelopen dagen. De twee reeksen delen één x-as; de
 * afwijking (wape) is al berekend en komt als string met één decimaal binnen.
 * Bewust geen "geel" in de reekskleuren: dit zijn twee lijnen, gemeten in
 * warmgrijs en voorspeld in bordeaux, zonder onzekerheidsband.
 */
export type TrackrecordReeks = Omit<Reeks, "kleur"> & {
  kleur: "warmgrijs" | "bordeaux";
};

export type Trackrecord = {
  grafiek: {
    reeksen: TrackrecordReeks[];
    y_as: As;
  };
  /** Aantal dagen waarover voorspelling en meting vergeleken zijn. */
  dagen: number;
  /**
   * Gemiddelde afwijking als machinewaarde, bv. "10.0". Null wanneer de
   * berekeningslaag geen afwijking meelevert; het scherm zegt dat dan met
   * zoveel woorden en verzint er geen (harde regel 8).
   */
  wape: string | null;
  van: string; // ISO-datum, eerste vergeleken dag
  tot: string; // ISO-datum, laatste vergeleken dag
};

export type PrognoseData = {
  grafiek: Lijndata;
  dagen: {
    datum: string; // ISO-datum
    verwacht: string; // machinewaarde in euro
    onder: string;
    boven: string;
    /**
     * Waar het getal vandaan komt: basis (weekdagmediaan, euro) × niveau ×
     * kalenderfactor. De berekeningslaag garandeert per test dat het product
     * van deze kolommen de voorspelling zélf is — dit is dus uitleg, geen
     * tweede model. `kalenderfactor` is null wanneer er geen correctie op
     * deze dag werkt; `kenmerk` noemt de actieve correctie ("schoolvakantie").
     */
    opbouw?: {
      basis: string; // euro, machinewaarde
      niveau: string; // factor, machinewaarde ("1.042")
      kalenderfactor: string | null;
      kenmerk: string | null;
    } | null;
  }[];
  /**
   * De verantwoording van het model in één blok: methode, backtestvenster,
   * WAPE, systematische afwijking, banddekking en kalenderdekking — alles
   * gemeten, voorgeformatteerd door de berekeningslaag. Null op een contract
   * van vóór dit veld.
   */
  modelkaart?: {
    rijen: { label: string; waarde: string }[];
    toelichting: string;
  } | null;
  /**
   * Som van de puntvoorspellingen. Bewust zonder band, zie onbeschikbaar.
   * Null wanneer er geen som te maken is; het scherm toont dan een
   * onbeschikbaar-vak met de reden uit het contract, geen nul.
   */
  weektotaal: string | null;
  /**
   * Het aantal dagen dat in `weektotaal` zit. Het venster slaat dagen over
   * waarvan de kalender zegt dat de winkel dicht is, dus dit is niet
   * noodzakelijk zeven. Het scherm schrijft dit getal uit in plaats van er
   * een aantal bij te verzinnen.
   */
  weektotaal_dagen: number;
  /**
   * Hoe goed het model tot nu toe voorspelde. Null wanneer er nog geen
   * trackrecord is; de reden staat dan in `onbeschikbaar` onder het veld
   * "prognose.trackrecord".
   */
  trackrecord: Trackrecord | null;
  /**
   * Per categorie een eigen prognose met een eigen gemeten afwijking. De
   * blokken tellen bewust niet exact op tot `weektotaal` (dat komt uit de
   * directe dagprognose, die de backtest beter doorstond); de toelichting
   * zegt dat hardop. Null zolang er geen categoriebacktest gedraaid is.
   */
  categorieen: {
    blokken: {
      categorie: string;
      aandeel: string; // percentage van de kanaalomzet
      wape: string; // gemeten afwijking, percentage
      weektotaal: string;
      dagen: { datum: string; verwacht: string; onder: string; boven: string }[];
    }[];
    toelichting: string;
  } | null;
};

/**
 * De stand van het platform zelf: leeft het, en klopt wat het toont?
 * Alle oordelen ("vers", "achter", "let_op") komen uit de berekeningslaag;
 * het scherm geeft ze alleen weer en spreekt er zelf geen uit.
 */
export type BronStatus =
  | "vers"
  | "achter"
  | "stil"
  | "gesloten"
  | "ontbreekt"
  /**
   * Een bron die niet meer aangevuld wordt: de periodieke aanlevering is
   * stopgezet, dus de historiek staat stil en mag niet tegen de klok gemeten
   * worden. Zie `kwaliteit.BEVROREN` — daar staat waarom dit geen 'achter' is
   * en wat er moet gebeuren als er ooit tóch weer aanvoer komt.
   */
  | "bevroren";

export type BronStand = {
  bron: string;
  /** Jongste meetdag van deze bron, of null als er niets gemeten is. */
  laatste_meetdag: string | null; // ISO-datum
  rijen: number;
  status: BronStatus;
  toelichting: string;
};

export type WachterUitkomst = "goed" | "let_op" | "fout";

export type Wachter = {
  naam: string;
  uitkomst: WachterUitkomst;
  toelichting: string;
};

export type StandData = {
  bronnen: BronStand[];
  wachters: Wachter[];
  /** De ergste uitkomst over alles heen; de voettekst van elk scherm draagt die. */
  ergste: WachterUitkomst;
};

/**
 * Het antwoord voor het scherm Sluitingsdagen: de bevestigingslijst van
 * feestdagen, twaalf maanden vooruit. De uitspraken zelf (open/dicht) leest
 * het scherm rechtstreeks uit de database (lib/sluitingsdagen-db.ts), want
 * dit contract wordt nachtelijk herbouwd en een beheerder moet zijn eigen
 * invoer meteen terugzien. Spoort met contract.sluitingsdagen in
 * bakkerij/contract.py; de test DATASLEUTELS pint de velden.
 */
export type SluitingsdagenData = {
  kandidaten: {
    /** ISO-datum, machinewaarde. */
    datum: string;
    /** "vr 25 december 2026", al in de taal van het contract. */
    datum_tekst: string;
    /** De feestdagnaam uit de holidays-bibliotheek, in de taal van het contract. */
    naam: string;
  }[];
  /** Tot waar de oude bestandslijst (config/sluitingsdagen.json) reikt. */
  bestandsdekking_tot: string | null;
  bestandsdekking_tekst: string;
};
