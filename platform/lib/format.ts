import type { Taal } from "./taal";

/**
 * Getallen en datums in Belgisch Nederlands en Belgisch Frans. Alles hier is stringbewerking:
 * er wordt nergens gerekend, afgerond of geconverteerd naar floating point.
 * Bedragen komen als string met punt-decimaal binnen ("1234.56") en gaan
 * als "€ 1.234,56" naar buiten.
 */

/**
 * De maandafkortingen per taal. De groepering van getallen blijft in beide
 * talen gelijk ("€ 1.234,56") — zie de noot in `taal.ts`; alleen de namen
 * verschillen, en die staan hier.
 */
const MAANDEN: Record<Taal, readonly string[]> = {
  nl: ["jan", "feb", "mrt", "apr", "mei", "jun",
       "jul", "aug", "sep", "okt", "nov", "dec"],
  fr: ["janv", "févr", "mars", "avr", "mai", "juin",
       "juil", "août", "sept", "oct", "nov", "déc"],
};

const MINUS = "−"; // echte minus, geen koppelteken

/**
 * De kastlijn (U+2014) voor een cel of tooltip zonder waarde. Eén constante,
 * geen los teken per scherm: een koppelteken of minus die zich ertussen
 * mengt is met het blote oog niet te zien, maar wel een ander teken voor
 * wie kopieert of laat voorlezen (18 aug 2026).
 */
export const KASTLIJN = "—";

/** "1234.56" -> "1.234,56" — puur lexicaal, geen enkele bewerking op de waarde. */
function belgisch(waarde: string): string {
  const negatief = waarde.startsWith("-") || waarde.startsWith(MINUS);
  const kaal = negatief ? waarde.slice(1) : waarde;
  const [heel, decimalen] = kaal.split(".");
  const gegroepeerd = heel.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const romp = decimalen !== undefined ? `${gegroepeerd},${decimalen}` : gegroepeerd;
  return negatief ? `${MINUS}${romp}` : romp;
}

/** "1234.56" -> "€ 1.234,56" */
export function euro(waarde: string): string {
  return `€ ${belgisch(waarde)}`;
}

/** "12.3" -> "12,3 %" ; "-4.2" -> "−4,2 %" */
export function procent(waarde: string): string {
  return `${belgisch(waarde)} %`;
}

/** "1234" -> "1.234" */
export function aantal(waarde: string): string {
  return belgisch(waarde);
}

/**
 * 1234 -> "1.234". Voor de weinige gehele getallen die als `number` in het
 * contract staan (aantal dagen, aantal meetdagen): geen geldwaarden, geen
 * afronding, alleen dezelfde groepering als de rest van het scherm. Zo staat
 * ook dit soort getal in Belgisch Nederlands en niet via een losse toString.
 */
export function geheelGetal(waarde: number): string {
  return belgisch(String(waarde));
}

/**
 * 2481.5 -> "€ 2.481,50". Voor de tooltip op een grafiekpunt: de y-waarde is
 * plotgeometrie (al door de berekeningslaag op twee decimalen gezet) en dit
 * is haar enige weg naar leesbare tekst. Twee decimalen vast, zodat een punt
 * op een hele euro niet ineens korter oogt dan zijn buren; verder dezelfde
 * lexicale opmaak als elk ander bedrag.
 */
export function euroBedrag(waarde: number): string {
  return euro(waarde.toFixed(2));
}

/**
 * "1.042" -> "× 1,042". Voor de opbouw van een prognosedag. Alle decimalen
 * blijven staan zoals de berekeningslaag ze leverde: hier afkappen zou een
 * ander getal tonen dan waarmee gerekend is.
 */
export function factor(waarde: string): string {
  return `× ${belgisch(waarde)}`;
}

/**
 * "30.5" -> "30,5". De machinewaarde uit het contract als invoertekst voor een
 * formulierveld: decimale komma, geen groepering en geen eenheid, zodat de
 * gebruiker terugleest wat hij intikte. Ook dit is stringbewerking en hoort
 * hier, niet los in een component — getalopmaak heeft één adres.
 */
export function invoerWaarde(waarde: string): string {
  return waarde.replace(".", ",");
}

/** "3.1" -> "+3,1 %" ; "-4.2" -> "−4,2 %" — voor verschillen t.o.v. vorig jaar. */
export function verschilProcent(waarde: string): string {
  const negatief = waarde.startsWith("-");
  return negatief ? procent(waarde) : `+${procent(waarde)}`;
}

/**
 * "2026-08-12T04:00:00+02:00" -> "12 aug 2026". Een waarde die geen
 * ISO-datum is, komt onvervormd terug: rauw op het scherm is zichtbaar en
 * dus herstelbaar; een crash op `.replace` van undefined legt het hele
 * scherm plat om één kapot veld.
 */
export function datumKort(iso: string, taal: Taal = "nl"): string {
  const delen = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!delen) return iso;
  const [, jaar, maand, dag] = delen;
  const maandNaam = MAANDEN[taal][Number(maand) - 1];
  if (maandNaam === undefined) return iso;
  // Het Frans schrijft alleen de eerste van de maand als rangtelwoord:
  // "1er janv", maar "2 janv". Dezelfde regel als taal.py `dagnummer`.
  const dagTekst =
    taal === "fr" && Number(dag) === 1 ? "1er" : dag.replace(/^0/, "");
  return `${dagTekst} ${maandNaam} ${jaar}`;
}

/** "2026-08-12T04:00:00+02:00" -> "12 aug 2026, 04:00" */
export function datumMetTijd(iso: string, taal: Taal = "nl"): string {
  const kort = datumKort(iso, taal);
  const tijd = /^.{10}T(\d{2}:\d{2})/.exec(iso);
  return tijd ? `${kort}, ${tijd[1]}` : kort;
}
