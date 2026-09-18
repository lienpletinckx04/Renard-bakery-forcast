/**
 * De sluitingskalender lezen en schrijven, van de gehoste omgeving uit.
 *
 * SCHRIJVEN gaat via de functie `bewaar_sluitingskalender` uit migratie 012 —
 * één PostgREST-verzoek is één transactie, en de rol achter de secret key
 * houdt géén insert-recht op de tabellen zelf. Zelfde patroon en zelfde
 * argumenten als lib/kostenmodel-db.ts (migratie 009); dit is de derde
 * toepassing van die keten.
 *
 * LEZEN gaat rechtstreeks uit de tabellen van migratie 011, en dat is hier
 * een bewuste uitzondering op "alles komt uit het contract" — dezelfde
 * uitzondering als lib/syncstand.ts, met dezelfde reden: het contract wordt
 * nachtelijk herbouwd, en een beheerder die net een feestdag bevestigd heeft
 * moet zijn eigen uitspraak meteen terugzien, niet morgenvroeg. Er wordt
 * hier niets gewogen of geteld (harde regel 4); de rijen gaan onbewerkt naar
 * het scherm.
 *
 * ANDERS DAN DE SYNCSTAND geeft een mislukte lezing hier GEEN stille null
 * met doorwerken: de server-actie voegt het formulier samen met wat er al
 * staat, en samenvoegen met een onbekende basis zou bewaarde uitspraken
 * wissen. De lezer onderscheidt daarom "leeg" (een gewone beginstand) van
 * "onbereikbaar" (null — en dan weigert de actie te bewaren).
 */

import { contractBron, dbToegang } from "./contract-bron";
import type { DagRij, RegelRij } from "./sluitingsdagen";

/** De functie uit migratie 012. Enige schrijfroute vanaf de gehoste omgeving. */
export const RPC = "bewaar_sluitingskalender";

export type BewaardeDag = DagRij & { bewaard_door: string; bewaard_op: string };

export type SluitingenStand = {
  dagen: BewaardeDag[];
  regels: RegelRij[];
};

/**
 * Het PostgREST-verzoek, als pure functie zodat een test de vorm kan
 * vastleggen zonder netwerk. De body-sleutels zijn de parameternamen van de
 * SQL-functie (`kalender`, `door`) — de PostgREST-conventie, zoals bij
 * bewaar_kostenmodel.
 */
export function bewaarVerzoek(
  dagen: DagRij[],
  regels: RegelRij[],
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
      kalender: { dagen, regels },
      door,
    }),
  };
}

/**
 * Bewaart de volledige kalender, en geeft `null` terug bij succes of anders
 * een reden voor de LOG — niet voor het scherm. Zelfde onderscheid als bij
 * het kostenmodel: een afwijzing van Postgres kan de mislukte rij dragen, en
 * die tekst hoort in het logboek van de server; de aanroeper geeft een
 * woordenboeksleutel aan de gebruiker.
 */
export async function bewaarInDatabase(
  dagen: DagRij[],
  regels: RegelRij[],
  door: string,
  omgeving: Record<string, string | undefined> = process.env,
): Promise<string | null> {
  const { url, headers, body } = bewaarVerzoek(dagen, regels, door, omgeving);
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

const TOESTANDEN: readonly string[] = ["open", "dicht"];
const BRONNEN: readonly string[] = ["feestdag", "periode", "bestand"];

/**
 * De bewaarde uitspraken en regels, of null wanneer de vraag niet bestaat
 * (bestandsroute) of de database niet antwoordt. Leeg is géén null: twee
 * lege lijsten zijn de gewone beginstand.
 */
export async function laadSluitingen(
  omgeving: Record<string, string | undefined> = process.env,
): Promise<SluitingenStand | null> {
  if (contractBron(omgeving) !== "db") return null;

  try {
    const { basis, headers } = dbToegang(omgeving);
    const opties = { headers, cache: "no-store" as const };
    const [dagenAntwoord, regelsAntwoord] = await Promise.all([
      fetch(
        `${basis}/rest/v1/sluitingsdag` +
          `?select=datum,toestand,reden,bron,bewaard_door,bewaard_op` +
          `&order=datum`,
        opties,
      ),
      fetch(
        `${basis}/rest/v1/sluitingsregel` +
          `?select=weekdag,vanaf,tot,reden&order=weekdag,vanaf`,
        opties,
      ),
    ]);
    if (!dagenAntwoord.ok || !regelsAntwoord.ok) return null;

    const dagenRuw = (await dagenAntwoord.json()) as Record<string, unknown>[];
    const regelsRuw = (await regelsAntwoord.json()) as Record<
      string,
      unknown
    >[];
    if (!Array.isArray(dagenRuw) || !Array.isArray(regelsRuw)) return null;

    const dagen: BewaardeDag[] = [];
    for (const rij of dagenRuw) {
      // Een rij die het schema van 011 niet kan dragen, bestaat niet; komt
      // ze toch binnen, dan is de route kapot en is zwijgen (null) eerlijker
      // dan een halve kalender tonen waar een opslag op voortbouwt.
      if (
        typeof rij.datum !== "string" ||
        typeof rij.toestand !== "string" ||
        !TOESTANDEN.includes(rij.toestand) ||
        typeof rij.bron !== "string" ||
        !BRONNEN.includes(rij.bron)
      ) {
        return null;
      }
      dagen.push({
        datum: rij.datum,
        toestand: rij.toestand as BewaardeDag["toestand"],
        reden: typeof rij.reden === "string" ? rij.reden : "",
        bron: rij.bron as BewaardeDag["bron"],
        bewaard_door:
          typeof rij.bewaard_door === "string" ? rij.bewaard_door : "",
        bewaard_op: typeof rij.bewaard_op === "string" ? rij.bewaard_op : "",
      });
    }
    const regels: RegelRij[] = [];
    for (const rij of regelsRuw) {
      if (typeof rij.weekdag !== "number" || typeof rij.vanaf !== "string") {
        return null;
      }
      regels.push({
        weekdag: rij.weekdag,
        vanaf: rij.vanaf,
        tot: typeof rij.tot === "string" ? rij.tot : null,
        reden: typeof rij.reden === "string" ? rij.reden : "",
      });
    }
    return { dagen, regels };
  } catch {
    return null;
  }
}
