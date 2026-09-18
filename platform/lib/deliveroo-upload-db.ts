/**
 * Een bronbestand bewaren en de bewaarde bestanden teruglezen, van de gehoste
 * omgeving uit.
 *
 * SCHRIJVEN gaat via de functie `bewaar_bron_upload` uit migratie 015 — één
 * PostgREST-verzoek is één transactie, en de rol achter de secret key houdt
 * géén insert-recht op de tabel zelf. Zelfde patroon en zelfde argumenten als
 * lib/kostenmodel-db.ts (009) en lib/sluitingsdagen-db.ts (012); dit is de
 * vierde toepassing van die keten.
 *
 * LEZEN gaat rechtstreeks uit bron_upload, en dat is dezelfde bewuste
 * uitzondering op "alles komt uit het contract" als bij de sluitingskalender
 * en de syncstand: het contract wordt nachtelijk herbouwd, en een beheerder
 * die net een bestand opgeladen heeft moet het meteen in de lijst zien staan,
 * niet morgenvroeg. Er wordt hier niets gewogen of geteld (harde regel 4); de
 * rijen gaan onbewerkt naar het scherm.
 *
 * DE KOLOM `inhoud` GAAT NOOIT MEE. Dat is het bestand zelf — tot tien
 * megabyte per rij. Op het scherm heeft hij niets te zoeken, en hem toch
 * meevragen zou de lijst van tien bestanden een honderd megabyte kostende
 * lezing maken. De select hieronder noemt daarom elke kolom bij naam in plaats
 * van `*`, en de test legt vast dat `inhoud` er niet bij staat.
 *
 * Een mislukte lezing geeft null, geen lege lijst: leeg is de gewone
 * beginstand ("er is nog niets opgeladen") en onbereikbaar is iets anders. Het
 * scherm zegt welk van de twee (harde regel 8).
 */

import { contractBron, dbToegang } from "./contract-bron";

/** De functie uit migratie 015. Enige schrijfroute vanaf de gehoste omgeving. */
export const RPC = "bewaar_bron_upload";

/** De tabel, alleen gelezen. */
export const TABEL = "bron_upload";

/**
 * Hoeveel rijen de lijst hoogstens toont. Het scherm is een controlelijst en
 * geen archief: wie honderd bestanden terug moet kijken, kijkt in de database.
 * Zonder grens groeit de lezing elke week mee tot ze op een dag traag is
 * zonder dat iemand iets veranderd heeft.
 */
export const LIMIET = 50;

/** De twee waarden die de inlaadlaag in `verwerkt_status` schrijft. */
export type VerwerktStatus = "gelukt" | "mislukt";

/** Eén rij uit bron_upload, zonder de inhoud. */
export type Upload = {
  upload_id: number;
  bron: string;
  bestandsnaam: string;
  mediatype: string;
  bytes: number;
  sha256: string;
  geladen_door: string;
  geladen_op: string;
  verwerkt_op: string | null;
  verwerkt_status: VerwerktStatus | null;
  verwerkt_reden: string;
};

/** Wat de rpc als upload verwacht: het bestand plus zijn kenmerken. */
export type NieuweUpload = {
  bron: string;
  bestandsnaam: string;
  mediatype: string;
  sha256: string;
  inhoud_base64: string;
};

/**
 * Geen fout, wel geen nieuwe rij: de rpc gaf 0 terug omdat dit bestand er al
 * stond (zelfde sha256). Een aparte waarde en geen losse tekenreeks, zodat de
 * aanroeper erop kan vergelijken zonder een zin te kennen.
 *
 * WAAROM DIT DOOR HETZELFDE KANAAL GAAT als een echte weigering: de
 * teruggave van `bewaarUploadInDatabase` is "wat er te melden valt", met null
 * voor "niets te melden, de rij staat er". Dit is de enige melding die géén
 * storing is, en daarom staat ze hier bij naam in plaats van tussen de
 * statusregels van Postgres.
 */
export const AL_GELADEN = "al-geladen";

/**
 * Het PostgREST-verzoek, als pure functie zodat een test de vorm kan
 * vastleggen zonder netwerk. De body-sleutels zijn de parameternamen van de
 * SQL-functie (`upload`, `door`) — de PostgREST-conventie, zoals bij
 * bewaar_kostenmodel en bewaar_sluitingskalender.
 */
export function bewaarUploadVerzoek(
  upload: NieuweUpload,
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
    body: JSON.stringify({ upload, door }),
  };
}

/**
 * Bewaart één bronbestand. Geeft `null` bij een nieuwe rij, `AL_GELADEN`
 * wanneer datzelfde bestand er al stond, en anders een reden voor de LOG —
 * niet voor het scherm. Zelfde onderscheid als bij het kostenmodel en de
 * sluitingskalender: een afwijzing van Postgres kan de gegevens van de
 * mislukte rij dragen, en die tekst hoort in het logboek van de server; de
 * aanroeper geeft een woordenboeksleutel aan de gebruiker.
 */
export async function bewaarUploadInDatabase(
  upload: NieuweUpload,
  door: string,
  omgeving: Record<string, string | undefined> = process.env,
): Promise<string | null> {
  const { url, headers, body } = bewaarUploadVerzoek(upload, door, omgeving);
  const antwoord = await fetch(url, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  });
  if (!antwoord.ok) {
    const tekst = await antwoord.text().catch(() => "");
    return `${antwoord.status} ${antwoord.statusText} ${tekst}`.slice(0, 1000);
  }
  // De rpc geeft het aantal nieuwe rijen terug: 1 of 0. Een antwoord dat geen
  // getal is, wordt niet als "al geladen" gelezen — dan is er wél bewaard en
  // is alleen de teruggave onverwacht, en dat mag geen melding worden die de
  // beheerder laat denken dat er niets gebeurd is.
  const uitslag = await antwoord.json().catch(() => null);
  return uitslag === 0 ? AL_GELADEN : null;
}

const STATUSSEN: readonly string[] = ["gelukt", "mislukt"];

/**
 * De bewaarde bronbestanden, jongste eerst, of null wanneer de vraag niet
 * bestaat (bestandsroute) of de database niet antwoordt.
 */
export async function laadUploads(
  omgeving: Record<string, string | undefined> = process.env,
): Promise<Upload[] | null> {
  if (contractBron(omgeving) !== "db") return null;

  try {
    const { basis, headers } = dbToegang(omgeving);
    const antwoord = await fetch(
      `${basis}/rest/v1/${TABEL}` +
        `?select=upload_id,bron,bestandsnaam,mediatype,bytes,sha256,` +
        `geladen_door,geladen_op,verwerkt_op,verwerkt_status,verwerkt_reden` +
        `&order=geladen_op.desc&limit=${LIMIET}`,
      { headers, cache: "no-store" },
    );
    if (!antwoord.ok) return null;

    const ruw = (await antwoord.json()) as Record<string, unknown>[];
    if (!Array.isArray(ruw)) return null;

    const uploads: Upload[] = [];
    for (const rij of ruw) {
      // Een rij die het schema van 015 niet kan dragen, bestaat niet; komt ze
      // toch binnen, dan is de route kapot en is zwijgen (null) eerlijker dan
      // een halve lijst tonen waarin een opgeladen bestand ontbreekt.
      const status = rij.verwerkt_status;
      const statusGeldig =
        status === null ||
        status === undefined ||
        (typeof status === "string" && STATUSSEN.includes(status));
      if (
        typeof rij.upload_id !== "number" ||
        typeof rij.bestandsnaam !== "string" ||
        typeof rij.bytes !== "number" ||
        typeof rij.geladen_op !== "string" ||
        !statusGeldig
      ) {
        return null;
      }
      uploads.push({
        upload_id: rij.upload_id,
        bron: typeof rij.bron === "string" ? rij.bron : "",
        bestandsnaam: rij.bestandsnaam,
        mediatype: typeof rij.mediatype === "string" ? rij.mediatype : "",
        bytes: rij.bytes,
        sha256: typeof rij.sha256 === "string" ? rij.sha256 : "",
        geladen_door:
          typeof rij.geladen_door === "string" ? rij.geladen_door : "",
        geladen_op: rij.geladen_op,
        verwerkt_op: typeof rij.verwerkt_op === "string" ? rij.verwerkt_op : null,
        verwerkt_status:
          typeof status === "string" ? (status as VerwerktStatus) : null,
        verwerkt_reden:
          typeof rij.verwerkt_reden === "string" ? rij.verwerkt_reden : "",
      });
    }
    return uploads;
  } catch {
    return null;
  }
}
