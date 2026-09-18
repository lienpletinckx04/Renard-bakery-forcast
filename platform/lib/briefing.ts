/**
 * De twee lexicale keuzes van de briefing, apart van de component.
 *
 * Waarom apart: de testrunner is `node --experimental-strip-types` en die kan
 * geen `.tsx` laden — JSX is geen type dat je wegstript. Bleef dit in
 * `components/Briefing.tsx` staan, dan kon de volgorde en de bedragopmaak
 * alleen met een regex over de bron getoetst worden, en een regex over de bron
 * bewijst dat er iets geschreven staat, niet dat het werkt.
 *
 * Hier wordt niets gerekend en niets geoordeeld. De berekeningslaag bepaalt
 * wat een punt is en welke status het draagt; dit bestand bepaalt alleen in
 * welke volgorde ze op het scherm komen en hoe een bedrag eruitziet.
 */

import type { BriefingPunt } from "./contract";
import { aantal, euro, verschilProcent } from "./format";

/**
 * De volgorde van de statussen. Geen weging en geen oordeel — dat heeft de
 * berekeningslaag al gedaan — maar het houdt de belofte overeind dat een actie
 * bovenaan staat, ook als het contract de punten ooit anders levert.
 */
export const RANG: Record<BriefingPunt["status"], number> = {
  actie: 0,
  let_op: 1,
  goed: 2,
};

/**
 * Een status die hier nog niet bestaat, komt uit een nieuwere berekeningslaag.
 * Die krijgt de middelste behandeling: niet vooraan, niet achteraan, en zeker
 * niet stilletjes van het scherm.
 */
export const ONBEKEND: BriefingPunt["status"] = "let_op";

function rang(status: BriefingPunt["status"]): number {
  return RANG[status] ?? RANG[ONBEKEND];
}

/**
 * Acties eerst, dan wat aandacht vraagt, dan wat goed gaat. `sort` is stabiel,
 * dus de volgorde die het contract binnen één status koos, blijft staan. De
 * invoer wordt niet gemuteerd.
 */
export function opVolgorde(punten: readonly BriefingPunt[]): BriefingPunt[] {
  return [...punten].sort((a, b) => rang(a.status) - rang(b.status));
}

/**
 * Draagt deze briefing uitsluitend punten die op elk scherm hetzelfde zijn?
 *
 * Alleen voor het rapport. Daar verbergt CSS de gedeelde punten in elk
 * onderdeel behalve het eerste (zie globals.css); zonder dit antwoord zou een
 * scherm dat níéts eigens te melden heeft, daar een kop overhouden met een lege
 * lijst eronder — en een kop zonder inhoud leest als een blok dat stukgelopen
 * is.
 *
 * Dit oordeelt niet en rekent niet: het contract heeft per punt al gezegd of
 * het gedeeld is. Hier wordt alleen geteld of er nog iets overblijft.
 *
 * Een lege briefing is niet "alles gedeeld": daar toont de component al de
 * leeg-zin, en die hoort in het rapport gewoon te blijven staan.
 */
export function allesGedeeld(punten: readonly BriefingPunt[]): boolean {
  return punten.length > 0 && punten.every((p) => p.gedeeld === true);
}

/**
 * Het bedrag in de opmaak van het scherm. Puur lexicaal: `format.ts` groepeert
 * en zet komma's, en rekent niet.
 *
 * Een bedrag zonder soort krijgt de kale groepering, zonder eenheid: er staat
 * dan wel een getal, maar er wordt geen euroteken bij verzonnen dat het
 * contract niet gegeven heeft. Weglaten zou erger zijn — dan verdwijnt een
 * cijfer zonder dat iemand het merkt (harde regel 8).
 */
export function bedragTekst(
  bedrag: string,
  soort: BriefingPunt["soort"],
): string {
  switch (soort) {
    case "euro":
      return euro(bedrag);
    case "verschil":
      return verschilProcent(bedrag);
    default:
      return aantal(bedrag);
  }
}
