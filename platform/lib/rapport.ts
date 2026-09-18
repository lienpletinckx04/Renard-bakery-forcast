/**
 * De onderdelen van het CFO-rapport: één lijst, gelezen door het keuzemenu en
 * door de rapportweergave.
 *
 * WAAROM ÉÉN LIJST. Zou het menu zijn eigen vinkjes opsommen en het rapport zijn
 * eigen blokken, dan bestaat er een stand waarin je iets kunt aanvinken dat niet
 * gebouwd wordt, of iets meekrijgt dat je niet vroeg. Dezelfde les als
 * `SCHERMEN` in bakkerij/db/contract_rijen.py: de opsomming staat op één plek en
 * elke consument leest haar daar.
 *
 * WAAROM DEZE ZES. Ze volgen de schermen van het platform, want dat is de
 * indeling die de lezer al kent uit de navigatie. Het rapport is dus geen
 * tweede product met een eigen inhoudsopgave; het is een selectie van wat er op
 * de schermen staat, in de vaste volgorde van de navigatie.
 */

import type { Sleutel } from "./taal";

/**
 * De vaste volgorde van het rapport. Een rapport heeft een canonieke ordening:
 * de volgorde waarin de vinkjes of de URL-parameters staan, verandert er niets
 * aan. Zo levert dezelfde keuze altijd hetzelfde document.
 */
export const RAPPORT_DELEN = [
  "overzicht",
  "kanalen",
  "producten",
  "marge",
  "prognose",
  "stand",
] as const;

export type RapportDeel = (typeof RAPPORT_DELEN)[number];

/** De naam van het vinkje en van de kop in de inhoudsopgave. */
export const DEEL_NAAM: Record<RapportDeel, Sleutel> = {
  overzicht: "nav.dagoverzicht",
  kanalen: "nav.kanalen",
  producten: "nav.producten",
  marge: "nav.marge",
  prognose: "nav.prognose",
  // Niet "nav.instellingen": van dat scherm gaat alleen de stand van het
  // platform mee (bronnen en wachters), niet het kostenformulier of het
  // gebruikersbeheer. Zie `data-buiten-rapport` in het instellingenscherm.
  stand: "rapport.deelStand",
};

/** De naam van de URL-parameter en van de vinkjes in het formulier. */
export const DEEL_PARAM = "deel";

/**
 * Welke onderdelen gevraagd zijn. Twee vormen worden aanvaard: herhaalde
 * parameters (`?deel=kanalen&deel=prognose`, wat een formulier met vinkjes
 * oplevert) en één kommalijst (`?deel=kanalen,prognose`, wat iemand met de hand
 * typt of doorstuurt).
 *
 * Drie regels, en alle drie om dezelfde reden — een rapport mag nooit stil iets
 * anders zijn dan je vroeg:
 *   1. Onbekende waarden worden genegeerd, niet gehonoreerd. De waarde wordt
 *      nergens een pad of een bestandsnaam, maar een tikfout hoort geen leeg
 *      document op te leveren.
 *   2. Niets gevraagd (of alleen onzin gevraagd) betekent het hele rapport.
 *      Dat is de veilige kant: liever te veel dan een document waarvan de lezer
 *      niet weet wat eruit weggelaten is.
 *   3. De uitkomst staat altijd in de vaste volgorde van RAPPORT_DELEN.
 */
export function kiesDelen(ruw: string | string[] | undefined): RapportDeel[] {
  const ruwe = Array.isArray(ruw) ? ruw : ruw === undefined ? [] : [ruw];
  const gevraagd = new Set(
    ruwe
      .flatMap((waarde) => waarde.split(","))
      .map((waarde) => waarde.trim())
      .filter((waarde) => waarde !== ""),
  );
  const gekozen = RAPPORT_DELEN.filter((deel) => gevraagd.has(deel));
  return gekozen.length > 0 ? [...gekozen] : [...RAPPORT_DELEN];
}
