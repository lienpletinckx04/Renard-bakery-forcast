import type { Onbeschikbaar } from "./contract";

/**
 * Waar een voorbehoud op het prognosescherm terechtkomt.
 *
 * Tot nu toe stonden alle redenen onderaan in één blok. Het gevolg: het meest
 * prominente cijfer van het scherm (het weektotaal) droeg zijn enige
 * kwalificatie drie schermlengtes lager, en de nauwkeurigheid uit de backtest —
 * de enige reden dat er überhaupt een voorspelling mag staan (harde regel 7) —
 * stond onder een kopje "wat hier niet staat".
 *
 * Deze functie verdeelt de regels over de plaatsen waar ze horen. Twee
 * eigenschappen zijn belangrijker dan de indeling zelf:
 *  - Geen regel verdwijnt. Een veld dat hier niet bij naam bekend is (een
 *    nieuwe reden uit de berekeningslaag, bijvoorbeeld prognose.meetgat als die
 *    naam verandert) valt altijd in `overig` en komt dus op het scherm.
 *  - De ordening is vast en niet afhankelijk van de volgorde in de JSON.
 */

/** Bovenaan: hoe dit scherm gelezen moet worden, vóór het eerste cijfer. */
const KOP = [
  "prognose.nauwkeurigheid",
  "prognose.meetgat",
  "prognose.startpunt",
] as const;

/** Naast de tegel met het weektotaal. */
const TEGEL = ["prognose.weektotaal"] as const;

/** Onder de dagtabel: welke dagen er wel en niet in staan. */
const DAGEN = ["prognose.sluitingsdagen"] as const;

/** Bij het trackrecord-vak: waarom er nog geen trackrecord staat. */
const TRACKRECORD = ["prognose.trackrecord"] as const;

export type Verdeling = {
  kop: Onbeschikbaar[];
  tegel: Onbeschikbaar[];
  dagen: Onbeschikbaar[];
  trackrecord: Onbeschikbaar[];
  overig: Onbeschikbaar[];
};

function pak(regels: Onbeschikbaar[], velden: readonly string[]): Onbeschikbaar[] {
  return velden
    .map((veld) => regels.find((r) => r.veld === veld))
    .filter((r): r is Onbeschikbaar => r !== undefined);
}

export function verdeelPrognoseRegels(regels: Onbeschikbaar[]): Verdeling {
  const geplaatst = new Set<string>([...KOP, ...TEGEL, ...DAGEN, ...TRACKRECORD]);
  return {
    kop: pak(regels, KOP),
    tegel: pak(regels, TEGEL),
    dagen: pak(regels, DAGEN),
    trackrecord: pak(regels, TRACKRECORD),
    overig: regels.filter((r) => !geplaatst.has(r.veld)),
  };
}

/** De reden bij één veld, of null als het contract er geen geeft. */
export function reden(regels: Onbeschikbaar[], veld: string): string | null {
  return regels.find((r) => r.veld === veld)?.reden ?? null;
}

/**
 * Van contractsleutel naar leesbaar label (O12).
 *
 * `onbeschikbaar[].veld` is een technische sleutel: "prognose.startpunt",
 * "bonritme.ontbinding". Die hoort in het contract thuis — hij is stabiel, hij
 * overleeft een hertaling en de app van fase 2 herkent hem — maar hij hoort
 * niet op een scherm. Een klant die "prognose.startpunt" leest, leest een
 * variabelenaam.
 *
 * De omzetting gebeurt daarom hier, in de presentatielaag, en niet door een
 * `label` aan het contract toe te voegen: een label is tekst en geen cijfer,
 * en het contract draagt cijfers.
 *
 * Drie stappen, in deze volgorde:
 *  1. een sleutel die hier bij naam bekend is, krijgt zijn eigen label;
 *  2. een sleutel met een bekend voorvoegsel krijgt "Voorvoegsel: rest". Dat
 *     vangt de sleutels waarvan de staart uit de data komt en dus niet vooraf
 *     op te schrijven is ("kanaal.<een nieuw kanaal>", "product.<naam>");
 *  3. wat overblijft wordt leesbaar gemaakt in plaats van weggelaten. Een
 *     nieuwe reden uit de berekeningslaag verschijnt dus altijd op het scherm,
 *     desnoods met een onhandig label — verzwijgen is erger dan onhandig.
 *
 * De eigenschap die stap 2 en 3 samen moeten waarmaken: geen enkel label draagt
 * nog een punt of een liggend streepje. Ook de staart van stap 2 gaat daarom
 * door hetzelfde vangnet — anders lekt "kanaal.nieuw_kanaal" alsnog een
 * variabelenaam op het scherm.
 */
export type LabelTaal = "nl" | "fr";

/** [Nederlands, Frans] — dezelfde vorm als het woordenboek in lib/taal.ts,
 * zodat een ontbrekende vertaling een typefout is en geen schermgat. */
const LABELS: Record<string, [string, string]> = {
  afwijkende_dagen: ["Opvallende dagen", "Jours remarquables"],
  bonritme: ["Klanten of mandje", "Clients ou panier"],
  "bonritme.ontbinding": [
    "Klanten of mandje, ontbinding",
    "Clients ou panier, décomposition",
  ],
  "bonritme.dagen_zonder_bonnen": [
    "Dagen zonder bonnentelling",
    "Jours sans comptage de tickets",
  ],
  concentratie: ["Waar de omzet op leunt", "Ce qui porte le chiffre d'affaires"],
  jaarvergelijking: ["Jaar-op-jaar", "Année après année"],
  kanaal: ["Kanaal", "Canal"],
  // De drie kanaalnamen staan er voluit in: het voorvoegselvangnet zou
  // "Kanaal: deliveroo" opleveren, en een merknaam met een kleine letter is
  // net zo goed een variabelenaam die ontsnapt is.
  "kanaal.winkel": ["Kanaal Winkel", "Canal Magasin"],
  "kanaal.tgtg": ["Kanaal Too Good To Go", "Canal Too Good To Go"],
  "kanaal.tgtg.kost": [
    "Kanaalkost Too Good To Go",
    "Coût du canal Too Good To Go",
  ],
  "kanaal.tgtg.aandeel": [
    "Aandeel Too Good To Go",
    "Part de Too Good To Go",
  ],
  "kanaal.deliveroo": ["Kanaal Deliveroo", "Canal Deliveroo"],
  "kanaal.deliveroo.kost": ["Kanaalkost Deliveroo", "Coût du canal Deliveroo"],
  kerncijfer: ["Kerncijfer", "Chiffre clé"],
  // De vier kerncijfers staan er voluit in, sinds 19 aug 2026. Tot dan was de
  // sleutel het lábel ("kerncijfer.Omzet laatste 7 open dagen") en deed het
  // voorvoegselvangnet hierboven het werk — maar dat label is tweetalig, en een
  // sleutel die met de taal meebeweegt breekt de belofte die hier vier alinea's
  // hoger staat. De sleutel is nu een machinenaam (`berekening.Kerncijfer`), en
  // een machinenaam heeft een label nodig: zonder deze vier regels zou er
  // "Kerncijfer: Omzet 7" op het scherm komen.
  "kerncijfer.omzet_7": [
    "Omzet laatste 7 open dagen",
    "Chiffre d'affaires, 7 derniers jours d'ouverture",
  ],
  "kerncijfer.omzet_30": [
    "Omzet laatste 30 open dagen",
    "Chiffre d'affaires, 30 derniers jours d'ouverture",
  ],
  "kerncijfer.stuks_7": [
    "Stuks laatste 7 open dagen",
    "Unités, 7 derniers jours d'ouverture",
  ],
  "kerncijfer.gemiddelde_dagomzet": [
    "Gemiddelde dagomzet",
    "Chiffre d'affaires moyen par jour",
  ],
  maandritme: [
    "Omzet per open dag, per maand",
    "Chiffre d'affaires par jour d'ouverture, par mois",
  ],
  "maandritme.lege_maanden": ["Maanden zonder meting", "Mois sans mesure"],
  marge_per_groep: ["Marge per productgroep", "Marge par groupe de produits"],
  marge_per_kanaal: ["Marge per kanaal", "Marge par canal"],
  marge: ["Marge", "Marge"],
  "marge.tgtg": ["Marge Too Good To Go", "Marge Too Good To Go"],
  "marge.deliveroo": ["Marge Deliveroo", "Marge Deliveroo"],
  "marge.ontbrekende_groepen": [
    "Groepen zonder ingevulde kosten",
    "Groupes sans coûts saisis",
  ],
  "marge.invoer": ["Ingevulde kosten", "Coûts saisis"],
  "marge.negatief": [
    "Groepen met negatieve marge",
    "Groupes à marge négative",
  ],
  "omzetverloop.vergelijking": [
    "Vergelijking met de vorige periode",
    "Comparaison avec la période précédente",
  ],
  prijs_volume: [
    "Meer stuks, of een andere prijs",
    "Plus d'unités, ou un autre prix",
  ],
  prognose: ["Prognose", "Prévision"],
  "prognose.categorieen": ["Prognose per categorie", "Prévision par catégorie"],
  "prognose.geplande_sluiting": ["Geplande sluiting", "Fermeture prévue"],
  "prognose.gesloten_dagen": [
    "Overgeslagen sluitingsdagen",
    "Jours de fermeture ignorés",
  ],
  "prognose.kalenderbereik": ["Bereik van de kalender", "Portée du calendrier"],
  "prognose.meetgat": [
    "Gat tussen meting en vandaag",
    "Écart entre la mesure et aujourd'hui",
  ],
  "prognose.nauwkeurigheid": [
    "Nauwkeurigheid van de prognose",
    "Précision de la prévision",
  ],
  "prognose.sluitingsdagen": ["Sluitingsdagen", "Jours de fermeture"],
  "prognose.startpunt": [
    "Startpunt van de prognose",
    "Point de départ de la prévision",
  ],
  "prognose.trackrecord": ["Trackrecord", "Historique de performance"],
  "prognose.weektotaal": ["Verwacht totaal", "Total attendu"],
  "periodes.w13": ["Venster van 13 weken", "Fenêtre de 13 semaines"],
  "periodes.weken_zonder_meting": [
    "Weken zonder meting",
    "Semaines sans mesure",
  ],
  verschuiving: ["Wat beweegt er", "Ce qui bouge"],
  weekdagmix: ["Aandeel per weekdag", "Part par jour de la semaine"],
  "weekdagmix.ontbrekende_dagen": [
    "Weekdagen zonder meting",
    "Jours de la semaine sans mesure",
  ],
  weekdagprofiel: ["Weekdagprofiel", "Profil par jour de la semaine"],
  weken: ["De laatste volledige weken", "Les dernières semaines complètes"],
  "weken.gesloten": ["Weken zonder meting", "Semaines sans mesure"],
  "weken.open_dagen": [
    "Ongelijk aantal open dagen",
    "Nombre inégal de jours d'ouverture",
  ],

  // De wachters uit `stand.json` dragen dezelfde vorm als een contractsleutel
  // en gaan dus door dezelfde vertaling. Deze zeven staan hier voor een net
  // label — "drempelrand" zegt een CFO niets. Het vangnet hieronder dekt elke
  // wachter die er later bijkomt, zonder wijziging aan deze tabel.
  drempelrand: ["Dagen dicht bij de drempel", "Jours proches du seuil"],
  dubbele_sleutels: ["Dubbele sleutels", "Clés en double"],
  gat_in_de_reeks: [
    "Gat in de reeks open dagen",
    "Trou dans la série des jours d'ouverture",
  ],
  kalenderdekking: ["Dekking van de kalender", "Couverture du calendrier"],
  negatieve_waarden: [
    "Negatieve omzet of aantallen",
    "Chiffre d'affaires ou quantités négatifs",
  ],
  bonnen_omzetdekking: [
    "Bonnen en omzet dekken elkaar",
    "Tickets et chiffre d'affaires se recouvrent",
  ],
  censureringsdrempel: ["Censureringsdrempel", "Seuil de censure"],

  // De bronnen uit `stand.json` (bronstanden[].bron) en uit de envelope
  // (`bron[]`, in de voettekst). Ook machinesleutels, net als de wachters.
  // Merknamen blijven in beide talen gelijk; een bron die er later
  // bijkomt, valt op het vangnet en verschijnt leesbaar in plaats van ruw.
  "odoo-kassa": ["Odoo-kassa's", "Caisses Odoo"],
  tgtg: ["Too Good To Go", "Too Good To Go"],
  deliveroo: ["Deliveroo", "Deliveroo"],
  // De envelope-bron "winkel" en de bronstand "odoo-kassa" zijn dezelfde
  // bron. Eén bron draagt één naam: de voettekst zegt hetzelfde als
  // Instellingen. ("Winkel"/"Magasin" als kanaalnaam loopt niet langs hier —
  // kanalen dragen hun vertaalde naam in het contract zelf.)
  winkel: ["Odoo-kassa's", "Caisses Odoo"],
};

/**
 * Punten en liggende streepjes eruit, dubbele spaties samengetrokken.
 * Hier leunt de hele eigenschap op: wat hier door is, is machinevrij.
 */
function ontdaan(sleutel: string): string {
  return sleutel.replace(/[._]+/g, " ").replace(/\s+/g, " ").trim();
}

/** "prognose_startpunt" -> "Prognose startpunt". Het vangnet, niet de regel. */
function leesbaar(sleutel: string): string {
  const tekst = ontdaan(sleutel);
  return tekst.charAt(0).toUpperCase() + tekst.slice(1);
}

export function veldLabel(veld: string, taal: LabelTaal): string {
  const i = taal === "fr" ? 1 : 0;
  const bekend = LABELS[veld];
  if (bekend !== undefined) return bekend[i];

  const punt = veld.indexOf(".");
  if (punt > 0) {
    const voorvoegsel = LABELS[veld.slice(0, punt)];
    // De staart komt uit de data en gaat door hetzelfde vangnet als een
    // onbekende sleutel: een staart met een streepje erin is even goed een
    // variabelenaam die ontsnapt is.
    const staart = ontdaan(veld.slice(punt + 1));
    if (voorvoegsel !== undefined && staart.length > 0) {
      // Franse typografie zet een spatie vóór de dubbele punt.
      return taal === "fr"
        ? `${voorvoegsel[i]} : ${staart}`
        : `${voorvoegsel[i]}: ${staart}`;
    }
  }
  return leesbaar(veld);
}
