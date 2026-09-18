/**
 * Kolomuitlijning voor tabellen, op één adres.
 *
 * Tot 18 augustus 2026 schreef elk scherm de literal opnieuw uit, met een
 * `as ("links" | "rechts")[]`-cast erachter omdat TypeScript de losse array
 * anders als `string[]` leest. Acht kopieën van dezelfde cast zijn acht
 * plaatsen waar een typefout ("recht") pas op het scherm opvalt. Deze twee
 * helpers dragen het type zelf, zodat de cast nergens meer hoeft.
 */

export type Uitlijning = "links" | "rechts";

/**
 * De gangbare tabelvorm: de eerste kolom (labels) links, alle cijferkolommen
 * rechts. Vrijwel elke tabel op de schermen heeft deze vorm.
 */
export function eersteLinks(aantalKolommen: number): Uitlijning[] {
  return Array.from({ length: aantalKolommen }, (_, i) =>
    i === 0 ? "links" : "rechts",
  );
}

/** Voor tabellen die van de gangbare vorm afwijken: zelfde waarden, mét type. */
export function uitlijning(...kolommen: Uitlijning[]): Uitlijning[] {
  return kolommen;
}
