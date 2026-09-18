/**
 * De dodemansknop: leeft de nachtelijke synchronisatie nog?
 *
 * WAAROM DIT NIET UIT HET CONTRACT KOMT
 *
 * Elk ander cijfer op dit platform komt uit het contract, en dat hoort zo. Dit
 * ene niet, en de reden staat voluit in db/migraties/010_syncstand.sql: het
 * contract wordt gebouwd dóór de nachtelijke sync. Op het moment van bouwen
 * staat de eigen run op 'bezig', dus zou een contractveld voor eeuwig "de sync
 * loopt nu" zeggen — ook drie nachten nadat er niets meer gedraaid heeft. Een
 * oordeel over versheid dat zelf bevriest, is geen dodemansknop.
 *
 * Het oordeel valt daarom op het moment van kijken. Niet hier: in de database,
 * in de view `public.sync_stand`. Deze module haalt het op en geeft het door.
 * Er wordt hier niets gewogen, geteld of vergeleken — harde regel 4 geldt
 * onverkort, en de drempels (36 uur, drie dagen) staan één keer, in SQL.
 *
 * ZONDER DATABASE BESTAAT DEZE VRAAG NIET
 *
 * Op de bestandsroute (CONTRACT_BRON niet op `db`) is er geen etl_run en geen
 * nachtelijke sync: iemand draait `make contract` met de hand. Dan geeft deze
 * module null en toont het platform er niets over. Dat is geen verzwijgen maar
 * de waarheid — er is niets om over te waken.
 */

import { contractBron, dbToegang } from "./contract-bron";

/** De machinereden waarom de stand is wat hij is; de UI zoekt er zijn zin bij. */
export type SyncGeval =
  | "nooit"
  | "vers"
  | "achter"
  | "oud"
  | "gefaald"
  | "loopt"
  | "gestrand";

export type SyncStand = {
  geval: SyncGeval;
  /** 'goed' | 'let_op' | 'fout' — dezelfde drie woorden als de wachters. */
  oordeel: string;
  /** Start van de jongste geslaagde run, of null als er nooit één was. */
  geslaagd_gestart_op: string | null;
  /** Foutmelding van de jongste run, zonder data (zie migratie 003). */
  laatste_melding: string | null;
};

const GEVALLEN: readonly string[] = [
  "nooit", "vers", "achter", "oud", "gefaald", "loopt", "gestrand",
];

/**
 * De stand van de nachtelijke sync, of null wanneer de vraag niet bestaat
 * (bestandsroute) of het antwoord onbruikbaar is.
 *
 * Deze lezer werpt bewust NIET, anders dan `laadContract`. Het verschil is het
 * gewicht: valt het contract weg, dan staat er geen cijfer op het scherm en
 * moet dat luid falen. Valt déze vraag weg, dan blijven alle cijfers staan en
 * ontbreekt alleen het toezicht erop. Een heel scherm laten omvallen omdat de
 * bewaker even niet bereikbaar was, is het middel erger dan de kwaal — het
 * ontbreken zelf is zichtbaar op Instellingen, waar de stand hoort te staan.
 */
export async function laadSyncStand(
  omgeving: Record<string, string | undefined> = process.env,
): Promise<SyncStand | null> {
  if (contractBron(omgeving) !== "db") return null;

  try {
    const { basis, headers } = dbToegang(omgeving);
    const antwoord = await fetch(
      `${basis}/rest/v1/sync_stand?select=geval,oordeel,geslaagd_gestart_op,laatste_melding`,
      {
        headers: { ...headers, Accept: "application/vnd.pgrst.object+json" },
        cache: "no-store",
      },
    );
    if (!antwoord.ok) return null;
    const rij = (await antwoord.json()) as Partial<SyncStand>;
    // De view geeft altijd precies één rij met een geldig geval; komt er iets
    // anders terug, dan is dat een nieuwe versie of een kapotte route, en dan
    // is zwijgen beter dan een woord tonen dat het woordenboek niet kent.
    if (typeof rij.geval !== "string" || !GEVALLEN.includes(rij.geval)) {
      return null;
    }
    return {
      geval: rij.geval as SyncGeval,
      oordeel: typeof rij.oordeel === "string" ? rij.oordeel : "fout",
      geslaagd_gestart_op:
        typeof rij.geslaagd_gestart_op === "string"
          ? rij.geslaagd_gestart_op
          : null,
      laatste_melding:
        typeof rij.laatste_melding === "string" ? rij.laatste_melding : null,
    };
  } catch {
    return null;
  }
}

/**
 * Hoort deze stand in de voettekst van elk scherm te staan?
 *
 * Alleen wanneer er iets aan de hand is. Bij 'goed' staat er niets — dezelfde
 * regel als bij `datakwaliteitVoettekst`: een melding die er altijd staat,
 * wordt niet meer gelezen op de dag dat ze ertoe doet.
 */
export function syncInVoettekst(stand: SyncStand | null): boolean {
  return stand !== null && stand.oordeel !== "goed";
}
