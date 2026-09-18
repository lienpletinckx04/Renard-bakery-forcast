/**
 * Validatie van het kostenmodel-formulier, los van Next zodat het testbaar is
 * met de kale node-testrunner (zoals lib/auth.ts en lib/marges.ts eerder).
 *
 * De vorm volgt bakkerij/kostenmodel.py, dat het bestand aan de andere kant
 * weer inleest en zíjn eigen controles doet: dit is de eerste poort, niet de
 * enige. Een leeg veld betekent "geen kost ingevuld" en is geen nul — het
 * paar (groep, criterium) verdwijnt dan uit het bestand.
 *
 * Fouten zijn SLEUTELS uit het woordenboek plus invulwaarden, geen zinnen:
 * deze module draait in een server-actie, en die kent de taal van de lezer
 * niet — dat weet het formulier, dat bij het tonen vertaalt (zelfde patroon
 * als login/acties.ts).
 */

import type { Sleutel } from "./taal";

export const MAX_CRITERIA = 12;
export const NAAM_MAX = 60;

export type CriteriumInvoer = { naam: string; omschrijving: string };

/** Eén validatiefout: de woordenboeksleutel en haar invulwaarden. */
export type KostenFout = { sleutel: Sleutel; waarden: Record<string, string> };

export type KostenValidatie = {
  criteria: { naam: string; omschrijving: string }[];
  /** groep -> criterium -> percentage als string met punt, klaar voor het bestand. */
  waarden: Record<string, Record<string, string>>;
  fouten: KostenFout[];
};

/** "30,5" en "30.5" zijn allebei geldig; opgeslagen wordt "30.5". */
export function valideerKostenmodel(
  criteriaInvoer: CriteriumInvoer[],
  kostenInvoer: { groep: string; criterium: string; waarde: string }[],
): KostenValidatie {
  const fouten: KostenFout[] = [];
  const criteria: { naam: string; omschrijving: string }[] = [];
  const gezien = new Set<string>();

  for (const c of criteriaInvoer) {
    const naam = c.naam.replace(/\s+/g, " ").trim();
    if (naam === "") continue; // een leeggelaten naamveld is geen criterium
    if (naam.length > NAAM_MAX) {
      fouten.push({
        sleutel: "kosten.naamTeLang",
        waarden: { naam: naam.slice(0, 20), max: String(NAAM_MAX) },
      });
      continue;
    }
    if (gezien.has(naam.toLowerCase())) {
      fouten.push({ sleutel: "kosten.dubbelCriterium", waarden: { naam } });
      continue;
    }
    gezien.add(naam.toLowerCase());
    criteria.push({ naam, omschrijving: c.omschrijving.trim() });
  }
  if (criteria.length > MAX_CRITERIA) {
    fouten.push({
      sleutel: "kosten.teVeelCriteria",
      waarden: { aantal: String(criteria.length), max: String(MAX_CRITERIA) },
    });
  }

  const bekend = new Map(criteria.map((c) => [c.naam.toLowerCase(), c.naam]));
  const waarden: Record<string, Record<string, string>> = {};
  for (const { groep, criterium, waarde } of kostenInvoer) {
    const g = groep.trim();
    const naam = bekend.get(criterium.replace(/\s+/g, " ").trim().toLowerCase());
    const tekst = waarde.trim().replace(",", ".");
    if (g === "" || tekst === "") continue;
    if (naam === undefined) {
      // Een waarde voor een net geschrapt criterium: bewust stil weglaten —
      // schrappen ís de bedoeling van de gebruiker, geen invoerfout.
      continue;
    }
    if (!/^\d{1,3}(\.\d{1,2})?$/.test(tekst)) {
      fouten.push({
        sleutel: "kosten.geenPercentage",
        waarden: { criterium: naam, groep: g, waarde: waarde.trim() },
      });
      continue;
    }
    if (Number(tekst) > 100) {
      fouten.push({
        sleutel: "kosten.buitenBereik",
        waarden: { criterium: naam, groep: g },
      });
      continue;
    }
    (waarden[g] ??= {})[naam] = tekst;
  }

  return { criteria, waarden, fouten };
}
