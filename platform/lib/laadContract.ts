/**
 * De contractlezer: elk scherm haalt zijn antwoord hier, per verzoek en van
 * schijf, niet als statische import in de bundel.
 *
 * Twee redenen, allebei gemeten op 14 augustus:
 *   1. Een statisch geïmporteerd contract zit in de build; na "marges
 *      opslaan → contract herrekend" zou een productiebuild het oude antwoord
 *      blijven tonen. Van schijf lezen maakt het scherm zo vers als het
 *      contract, en de contractbouw schrijft atomair (tmp + rename), dus een
 *      halve JSON bestaat niet.
 *   2. De winkelkiezer: met een winkelindeling (config/winkels.json)
 *      staat er naast het totaal een contractmap per winkel. De keuze leeft in
 *      een cookie, maar de cookie wordt nooit als pad vertrouwd — alleen een
 *      slug die de contractbouw zelf in winkels.json heeft gezet, wordt een
 *      mapnaam. Al het andere valt terug op het totaal.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

// Met expliciete extensie, en de eigen modules relatief in plaats van via de
// @/-alias: dit bestand draait ook onder de kale node-testloper
// (tests/laadcontract.test.ts), die de Next-alias niet kent en "next/headers"
// zonder extensie niet vindt. Zelfde afweging als in contract-bron.ts.
import { cookies } from "next/headers.js";

import { contractBron, contractPad, dbVerzoek } from "./contract-bron";
import type { Antwoord } from "./contract";
import { alsTaal, STANDAARDTAAL, TAAL_COOKIE, type Taal } from "./taal";

const CONTRACT_DIR = path.join(process.cwd(), "contract");

/**
 * Eén antwoord uit de gekozen bron, als geparste JSON. De bestandsroute is
 * de route van altijd; de databaseroute (CONTRACT_BRON=db, O13) haalt
 * dezelfde JSON uit contract_antwoord via PostgREST — zie contract-bron.ts
 * voor waarom dat niet over een databasewachtwoord loopt. cache: "no-store",
 * om dezelfde reden als het van-schijf-lezen hierboven: het scherm hoort zo
 * vers te zijn als het contract, niet als de build.
 */
async function leesAntwoord(
  scherm: string,
  taal: Taal,
  winkelSlug: string | null,
): Promise<unknown> {
  if (contractBron(process.env) === "db") {
    const { url, headers } = dbVerzoek(scherm, taal, winkelSlug, process.env);
    const antwoord = await fetch(url, { headers, cache: "no-store" });
    if (!antwoord.ok) {
      throw new Error(
        `contract_antwoord gaf ${antwoord.status} voor "${scherm}" (${taal}` +
          `${winkelSlug ? `, winkel ${winkelSlug}` : ""}). Bij 406 bestaat de ` +
          "rij niet: draai de nachtelijke sync (of make db-contract).",
      );
    }
    return ((await antwoord.json()) as { antwoord: unknown }).antwoord;
  }
  return JSON.parse(
    await readFile(contractPad(CONTRACT_DIR, scherm, taal, winkelSlug), "utf-8"),
  );
}

export const WINKEL_COOKIE = "winkel";

/**
 * De gekozen taal. Een onbekende cookiewaarde wordt nooit vertrouwd: `alsTaal`
 * geeft dan de standaardtaal terug. Dat is niet alleen netjes maar nodig — de
 * taal wordt hieronder een mapnaam, en een cookie die een pad mag kiezen is
 * een cookie die overal mag kijken.
 */
export async function huidigeTaal(): Promise<Taal> {
  return alsTaal((await cookies()).get(TAAL_COOKIE)?.value);
}

export type Scherm =
  | "overzicht"
  | "kanalen"
  | "producten"
  | "marge"
  | "prognose"
  | "stand"
  | "sluitingsdagen";

export type WinkelIndex = {
  winkels: { naam: string; slug: string }[];
  /** Filialen mét data die in geen enkele winkel staan; tellen alleen in het totaal. */
  niet_toegewezen: string[];
  /** Reden waarom een aanwezig winkels.json genegeerd is, anders null. */
  melding: string | null;
  /**
   * Winkels uit de config waarvoor de contractbouw geen schermen kon maken,
   * elk met de reden. Zonder deze lijst verdween zo'n winkel spoorloos uit
   * de kiezer en leek de terugval op het totaal een keuze (audit 15 aug).
   */
  overgeslagen: { naam: string; reden: string }[];
};

const LEEG: WinkelIndex = {
  winkels: [],
  niet_toegewezen: [],
  melding: null,
  overgeslagen: [],
};

/** De winkelindex zoals de contractbouw hem schreef; leeg vóór de eerste bouw.
 *  Uit dezelfde bron als de antwoorden: de index reist in de database mee als
 *  sleutel "winkels" (zie bakkerij/db/contract_rijen.py), altijd onder de
 *  standaardtaal — precies zoals de bestandsroute altijd de wortel las.
 *
 *  Alleen op de bestandsroute, en alleen bij ENOENT, is een lege index het
 *  juiste antwoord: dat is de normale beginstand vóór de eerste contractbouw
 *  met winkelconfig, en dan is er alleen het totaal en geen kiezer. Elke
 *  andere fout — en élke fout op de databaseroute (verkeerde sleutel, netwerk
 *  weg, sync niet gedraaid) — werpt. Een gesmoorde fout liet de kiezer stil
 *  verdwijnen, waarna elk scherm het totaal toonde onder de naam van een
 *  gekozen winkel: precies wat het doc-commentaar bij laadContract verbiedt. */
export async function laadWinkels(): Promise<WinkelIndex> {
  try {
    const ruw = (await leesAntwoord(
      "winkels",
      STANDAARDTAAL,
      null,
    )) as Partial<WinkelIndex>;
    return {
      winkels: Array.isArray(ruw.winkels) ? ruw.winkels : [],
      niet_toegewezen: Array.isArray(ruw.niet_toegewezen)
        ? ruw.niet_toegewezen
        : [],
      melding: typeof ruw.melding === "string" ? ruw.melding : null,
      overgeslagen: Array.isArray(ruw.overgeslagen) ? ruw.overgeslagen : [],
    };
  } catch (fout) {
    const bron = contractBron(process.env);
    if (bron === "bestand" && (fout as NodeJS.ErrnoException).code === "ENOENT") {
      // Geen index is de normale beginstand (vóór de eerste contractbouw met
      // winkelconfig); dan is er alleen het totaal en geen kiezer.
      return LEEG;
    }
    // Dezelfde boodschapstijl als laadContract hieronder: één leesbare fout
    // die zegt wat er moet gebeuren, in plaats van een scherm dat klopt op
    // het oog.
    throw new Error(
      'De winkelindex ("winkels") ontbreekt of is onleesbaar. ' +
        (bron === "db"
          ? "Draai de nachtelijke sync (of `make db-contract`) en herlaad."
          : "Draai `make contract` en herlaad."),
      { cause: fout },
    );
  }
}

/**
 * De gekozen winkel, of null voor het totaal. De cookie is een wens, de
 * index is de waarheid: een slug die de contractbouw niet kent, is het totaal.
 */
export async function actieveWinkel(): Promise<{
  naam: string;
  slug: string;
} | null> {
  const index = await laadWinkels();
  if (index.winkels.length === 0) return null;
  const keuze = (await cookies()).get(WINKEL_COOKIE)?.value;
  return index.winkels.find((w) => w.slug === keuze) ?? null;
}

/**
 * Eén contractantwoord, voor het totaal of voor de gekozen winkel. Een winkel
 * die in de index staat maar geen leesbaar bestand heeft, is een fout met een
 * reden — stil terugvallen op het totaal zou cijfers van het geheel tonen
 * onder de naam van één winkel.
 */
export async function laadContract<T>(
  scherm: Scherm,
  opties: { totaal?: boolean } = {},
): Promise<Antwoord<T>> {
  const [winkel, taal] = await Promise.all([
    opties.totaal ? Promise.resolve(null) : actieveWinkel(),
    huidigeTaal(),
  ]);
  try {
    return (await leesAntwoord(scherm, taal, winkel?.slug ?? null)) as Antwoord<T>;
  } catch (fout) {
    // Geen stille terugval op het Nederlands: dan zou een half gebouwd
    // contract zich voordoen als een vertaald contract. Eén leesbare fout die
    // zegt wat er moet gebeuren, is beter dan een scherm dat klopt op het oog.
    throw new Error(
      `Het contractantwoord "${scherm}" (${taal})` +
        `${winkel ? ` voor winkel "${winkel.naam}"` : ""} ` +
        "ontbreekt of is onleesbaar. " +
        (contractBron(process.env) === "db"
          ? "Draai de nachtelijke sync (of `make db-contract`) en herlaad."
          : "Draai `make contract` en herlaad."),
      { cause: fout },
    );
  }
}
