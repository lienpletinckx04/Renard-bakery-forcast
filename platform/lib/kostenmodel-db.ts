/**
 * Het kostenmodel naar de database schrijven, van de gehoste omgeving uit.
 *
 * HET GAT DAT DIT DICHT. Met CONTRACT_BRON=db leest het platform het contract
 * uit Postgres, en tot 18 augustus 2026 (avond) weigerde het kostenformulier op
 * Instellingen daar met zoveel woorden: het kon alleen een lokaal bestand
 * schrijven, en dat leest op de gehoste omgeving niemand. Eerlijk, maar het
 * gevolg was dat de beheerder de kostencriteria daar nooit kón invullen — en
 * zonder criteria blijft het margescherm leeg. Alles omzet, geen marge.
 *
 * WAAROM ÉÉN RPC EN NIET TWEE TABELVERZOEKEN. Over PostgREST is één verzoek één
 * transactie. Het kostenmodel bewaren raakt twee tabellen (het menu van criteria
 * en de waarden per groep) en moet alles-of-niets zijn, net als de ETL in
 * bakkerij/db/laden.py. Twee losse verzoeken kunnen een halve staat achterlaten:
 * criteria weg, waarden nog niet geschreven. Daarom schrijft dit naar de functie
 * `bewaar_kostenmodel` uit migratie 009 — één verzoek, één transactie, en de rol
 * achter de secret key houdt géén insert-recht op de tabellen zelf.
 *
 * WAAROM HIER GEEN POSTGRES-VERBINDING STAAT. Dezelfde reden als bij het lezen
 * (zie contract-bron.ts): SUPABASE_DB_URL — het databasewachtwoord — blijft weg
 * van Vercel. De secret key blijft op de server; deze module wordt alleen door
 * een server-actie geïmporteerd en draagt geen NEXT_PUBLIC_-voorvoegsel.
 *
 * DIT REKENT NIET. De brutomarge is 100 min de som van de criteria, en die som
 * staat in de berekeningslaag (harde regel 4). Hier gaat invoer naar de database
 * en niets meer. Het scherm ziet het gevolg pas na de volgende contractbouw, en
 * het formulier zegt dat ook — een opslag die belooft dat de cijfers nú kloppen,
 * zou liegen.
 */

import { dbToegang } from "./contract-bron";

/** De functie uit migratie 009. Enige schrijfroute vanaf de gehoste omgeving. */
export const RPC = "bewaar_kostenmodel";

export type CriteriumRij = { naam: string; omschrijving: string };

/** groep -> criterium -> percentage als string met punt ("30.5"). */
export type WaardenBoom = Record<string, Record<string, string>>;

/**
 * Het PostgREST-verzoek, als pure functie zodat een test de vorm kan vastleggen
 * zonder netwerk — dezelfde opzet als dbVerzoek.
 *
 * De body is bewust exact de vorm die bakkerij/kostenmodel.py in het bestand
 * schrijft (`versie`, `criteria`, `waarden`): dan leest de contractbouw uit de
 * database precies wat hij uit een bestand zou lezen, en is er één vorm in
 * plaats van twee. Percentages blijven strings — een JSON-getal zou onderweg
 * door een float gaan, en 30,5 % is dan op het scherm een keer 30,499...
 */
export function bewaarVerzoek(
  criteria: CriteriumRij[],
  waarden: WaardenBoom,
  door: string,
  omgeving: Record<string, string | undefined>,
): { url: string; headers: Record<string, string>; body: string } {
  const { basis, headers } = dbToegang(omgeving);
  return {
    url: `${basis}/rest/v1/rpc/${RPC}`,
    headers: {
      ...headers,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      model: { versie: 2, criteria, waarden },
      door,
    }),
  };
}

/**
 * Bewaart het model, en geeft `null` terug bij succes of anders een reden voor
 * de LOG — niet voor het scherm.
 *
 * Dat onderscheid is opzet. Een afwijzing van PostgREST draagt de melding van
 * Postgres, en die kan de gegevens van de mislukte rij bevatten (de
 * check-clausule van migratie 005 zet de hele rij in zijn DETAIL). Zulke tekst
 * hoort in het logboek van de server en niet op een scherm dat ook een lezer
 * opent; de aanroeper geeft een woordenboeksleutel aan de gebruiker.
 */
export async function bewaarInDatabase(
  criteria: CriteriumRij[],
  waarden: WaardenBoom,
  door: string,
  omgeving: Record<string, string | undefined> = process.env,
): Promise<string | null> {
  const { url, headers, body } = bewaarVerzoek(
    criteria,
    waarden,
    door,
    omgeving,
  );
  const antwoord = await fetch(url, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  });
  if (antwoord.ok) return null;
  const tekst = await antwoord.text().catch(() => "");
  return `${antwoord.status} ${antwoord.statusText} ${tekst}`.slice(0, 1000);
}
