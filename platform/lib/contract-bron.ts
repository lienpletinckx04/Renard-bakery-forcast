/**
 * Waar het contract vandaan komt: bestanden (standaard) of de database.
 *
 * Dit is de wissel van O13, naar het model van AUTH_BRON in auth.ts: één
 * omgevingsvariabele, en alleen de leesplek wisselt. Zonder CONTRACT_BRON
 * verandert er níéts — de bestandsroute blijft bit voor bit dezelfde, en de
 * test op deze module legt dat vast. Dat is de garantie waarop alle
 * voorbereiding tot S11 rust.
 *
 * De databaseroute leest via PostgREST met de server-only secret key, niet
 * via een rechtstreekse Postgres-verbinding. Bewust: de secretstabel in
 * stack.md houdt SUPABASE_DB_URL (het databasewachtwoord) weg van Vercel, en
 * PostgREST's bezwaren uit datzelfde document (geen COPY, geen transacties,
 * chunking) gaan over de ETL die tienduizenden rijen schrijft — hier lezen we
 * één rij van hooguit een paar tientallen kilobytes. De sleutel blijft op de
 * server: dit bestand wordt alleen door servercomponenten geïmporteerd, en
 * SUPABASE_SECRET_KEY draagt geen NEXT_PUBLIC_-voorvoegsel en kan dus niet in
 * de bundel belanden.
 *
 * Alles hier is puur en testbaar zonder next/headers en zonder netwerk; het
 * fetchen zelf gebeurt in laadContract.ts.
 */

import path from "node:path";

// Relatief en niet via de @/-alias: deze module draait ook onder de kale
// node-testloper (tests/ts-resolve.mjs), die de Next-alias niet kent.
import { STANDAARDTAAL, type Taal } from "./taal";

export type ContractBron = "bestand" | "db";

/** Welke bron de omgeving aanwijst. Een onbekende waarde is een
 *  configuratiefout en werpt — stil terugvallen op de bestanden zou een
 *  verkeerd gezette vlag verzwijgen als een werkende deploy. */
export function contractBron(
  omgeving: Record<string, string | undefined>,
): ContractBron {
  const bron = omgeving.CONTRACT_BRON ?? "bestand";
  if (bron !== "bestand" && bron !== "db") {
    throw new Error(
      `CONTRACT_BRON=${bron} is onbekend (keuze: bestand, db); ` +
        "zonder de variabele leest het platform de bestanden.",
    );
  }
  return bron;
}

/**
 * Het bestandspad van één antwoord, zoals het sinds dag één ligt: Nederlands
 * in de wortel, elke andere taal in een submap, winkels in winkels/<slug>/.
 * Deze functie bestaat zodat de test kan vastleggen dat de standaardroute
 * niet verschuift wanneer er aan de databaseroute gewerkt wordt.
 */
export function contractPad(
  wortel: string,
  scherm: string,
  taal: Taal,
  winkelSlug: string | null,
): string {
  const taalWortel = taal === STANDAARDTAAL ? wortel : path.join(wortel, taal);
  return winkelSlug
    ? path.join(taalWortel, "winkels", winkelSlug, `${scherm}.json`)
    : path.join(taalWortel, `${scherm}.json`);
}

/**
 * De twee servervariabelen waarmee het platform bij PostgREST binnenkomt, plus
 * de kant-en-klare headers. Eén plaats, omdat er sinds 18 augustus 2026 twee
 * routes zijn: het contract LEZEN (dbVerzoek hieronder) en het kostenmodel
 * SCHRIJVEN (lib/kostenmodel-db.ts). Zouden die twee elk hun eigen controle
 * dragen, dan kan er één achterblijven bij een naamswijziging — en dan faalt de
 * ene route leesbaar en de andere met een kale 401.
 *
 * De sleutel blijft op de server: deze module wordt alleen door
 * servercomponenten en server-acties geïmporteerd, en SUPABASE_SECRET_KEY
 * draagt geen NEXT_PUBLIC_-voorvoegsel en kan dus niet in de bundel belanden.
 */
export function dbToegang(omgeving: Record<string, string | undefined>): {
  basis: string;
  headers: Record<string, string>;
} {
  const basis = omgeving.NEXT_PUBLIC_SUPABASE_URL;
  const sleutel = omgeving.SUPABASE_SECRET_KEY;
  if (!basis || !sleutel) {
    const mist = [
      !basis && "NEXT_PUBLIC_SUPABASE_URL",
      !sleutel && "SUPABASE_SECRET_KEY",
    ]
      .filter(Boolean)
      .join(" en ");
    throw new Error(
      `CONTRACT_BRON=db vergt ${mist} in de serveromgeving. ` +
        "Zonder die variabelen kan het contract niet uit de database komen.",
    );
  }
  return {
    basis: basis.replace(/\/$/, ""),
    headers: { apikey: sleutel, Authorization: `Bearer ${sleutel}` },
  };
}

/**
 * Het PostgREST-verzoek voor één antwoord uit contract_antwoord (migratie
 * 006). De sleutel is scherm × taal × winkel, met '' voor het totaal —
 * dezelfde afspraak als bakkerij/db/contract_rijen.py. De Accept-header
 * vraagt één object in plaats van een lijst; nul rijen wordt dan een 406 en
 * geen lege array die stil als antwoord zou doorgaan.
 */
export function dbVerzoek(
  scherm: string,
  taal: Taal,
  winkelSlug: string | null,
  omgeving: Record<string, string | undefined>,
): { url: string; headers: Record<string, string> } {
  const { basis, headers } = dbToegang(omgeving);
  const vraag = new URLSearchParams({
    select: "antwoord",
    scherm: `eq.${scherm}`,
    taal: `eq.${taal}`,
    winkel: `eq.${winkelSlug ?? ""}`,
  });
  return {
    url: `${basis}/rest/v1/contract_antwoord?${vraag}`,
    headers: { ...headers, Accept: "application/vnd.pgrst.object+json" },
  };
}
