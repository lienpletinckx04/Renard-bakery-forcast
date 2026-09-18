#!/usr/bin/env node
/**
 * Visuele steekproef: schermafbeeldingen van élk scherm, in beide talen.
 *
 * Dit script start niets zelf. Het verwacht een draaiende dev-server
 * (`make dev`, standaard http://localhost:3000) en maakt daar met Playwright
 * schermafbeeldingen van, als aangemelde beheerder, in het Nederlands én het
 * Frans. De afbeeldingen zijn voor ménselijke ogen: het script beoordeelt
 * niets, het legt alleen vast.
 *
 *   node scripts/visuele_steekproef.mjs <uitvoermap> [basis-url]
 *
 * Aanmelden gebeurt niet via het formulier maar met een zelf getekende
 * sessiecookie, precies zoals platform/lib/auth.ts hem tekent: payload is
 * base64url van de sessie-JSON, handtekening is HMAC-SHA256 over die payload
 * met als sleutel de base64url-gedecodeerde PLATFORM_SESSIE_SLEUTEL uit
 * platform/.env.local. De gebruikersnaam komt uit PLATFORM_GEBRUIKERS in
 * datzelfde bestand — de leeslaag eist dat de naam daar bestaat. Sleutel en
 * wachtwoordafdrukken verschijnen nergens in de uitvoer, en dat blijft zo.
 *
 * De taal wisselt zoals de app het doet: de cookie `renard_taal` (zie
 * platform/lib/taal.ts en taal-acties.ts), met "nl" of "fr" erin.
 *
 * De schermen worden niet hier opgesomd maar gelezen uit platform/app/(dash)/:
 * elke map met een page.tsx is een scherm. Een nieuw scherm doet dus vanzelf
 * mee. Per scherm en taal komt er één PNG van de volledige pagina; staat er
 * ingeklapte uitleg op (<details>), dan volgt een tweede PNG met alles open,
 * want ook ingeklapte tekst moet ooit door ogen zijn gezien.
 *
 * Playwright hoort niet bij het platform (het staat bewust niet in
 * package.json); het script zoekt het pakket vanaf zijn eigen map en vanaf de
 * werkmap. Installeer het buiten de repo en draai vanuit die map, bv.:
 *
 *   cd /tmp/steekproef && npm i playwright
 *   node <repo>/scripts/visuele_steekproef.mjs ./schermen
 *
 * `channel: "chrome"` gebruikt de Chrome die op de machine staat; er wordt
 * geen browser gedownload.
 */
import { createHmac } from "node:crypto";
import { readdirSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HIER = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.dirname(HIER);
const PLATFORM = path.join(REPO, "platform");

const SESSIE_COOKIE = "renard_sessie"; // platform/lib/auth.ts
const TAAL_COOKIE = "renard_taal"; //    platform/lib/taal.ts
const TALEN = ["nl", "fr"];
const BREEDTE = 1440;
const HOOGTE = 900;

const faal = (bericht) => {
  console.error(`Fout: ${bericht}`);
  process.exit(1);
};

// --- argumenten ---------------------------------------------------------------

const [uitvoermap, basisArg] = process.argv.slice(2);
if (!uitvoermap) {
  console.error("Gebruik: node scripts/visuele_steekproef.mjs <uitvoermap> [basis-url]");
  process.exit(1);
}
const BASIS = (basisArg ?? "http://localhost:3000").replace(/\/$/, "");

// --- Playwright opsporen --------------------------------------------------------

async function laadPlaywright() {
  for (const anker of [path.join(HIER, "x.js"), path.join(process.cwd(), "x.js")]) {
    try {
      const pad = createRequire(anker).resolve("playwright");
      const mod = await import(pathToFileURL(pad).href);
      // Playwright is een CommonJS-pakket: bij een dynamische import kunnen de
      // named exports onder `default` zitten. Beide vormen aanvaarden.
      return mod.chromium ? mod : mod.default;
    } catch {
      /* volgende anker */
    }
  }
  faal(
    "het pakket `playwright` is niet vindbaar vanaf de scriptmap of de werkmap.\n" +
      "Installeer het buiten de repo en draai vanuit die map:\n" +
      "  mkdir -p /tmp/steekproef && cd /tmp/steekproef && npm i playwright\n" +
      "  node <repo>/scripts/visuele_steekproef.mjs <uitvoermap>",
  );
}

// --- .env.local lezen (zonder er ooit iets uit te tonen) ------------------------

function leesEnvLocal() {
  const pad = path.join(PLATFORM, ".env.local");
  if (!existsSync(pad)) faal(`platform/.env.local bestaat niet (gezocht: ${pad}).`);
  const env = {};
  for (const regel of readFileSync(pad, "utf8").split("\n")) {
    const m = regel.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!m) continue;
    env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return env;
}

/** Eerste beheerder uit PLATFORM_GEBRUIKERS; alleen de náám, nooit de afdruk. */
function kiesGebruiker(env) {
  const ruw = env.PLATFORM_GEBRUIKERS;
  if (!ruw) faal("PLATFORM_GEBRUIKERS ontbreekt in platform/.env.local.");
  const regels = ruw.split(",").map((r) => r.trim()).filter(Boolean);
  const beheerder = regels.map((r) => r.split(":")).find(([, rol]) => rol === "beheerder");
  if (!beheerder) faal("geen gebruiker met rol `beheerder` in PLATFORM_GEBRUIKERS.");
  return beheerder[0];
}

// --- de sessiecookie, getekend zoals platform/lib/auth.ts dat doet --------------

function tekenSessie(env, gebruiker) {
  const geheim = env.PLATFORM_SESSIE_SLEUTEL;
  if (!geheim) faal("PLATFORM_SESSIE_SLEUTEL ontbreekt in platform/.env.local.");
  const sessie = {
    gebruiker,
    rol: "beheerder",
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
  const payload = Buffer.from(JSON.stringify(sessie)).toString("base64url");
  const sig = createHmac("sha256", Buffer.from(geheim, "base64url")).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

// --- de schermen, gelezen uit de routemap ----------------------------------------

function vindSchermen() {
  const dash = path.join(PLATFORM, "app", "(dash)");
  if (!existsSync(dash)) faal(`routemap ontbreekt: ${dash}`);
  const schermen = [{ route: "/", naam: "overzicht" }];
  for (const item of readdirSync(dash, { withFileTypes: true })) {
    if (item.isDirectory() && existsSync(path.join(dash, item.name, "page.tsx"))) {
      schermen.push({ route: `/${item.name}`, naam: item.name });
    }
  }
  return schermen;
}

// --- en dan kijken ----------------------------------------------------------------

const { chromium } = await laadPlaywright();
const env = leesEnvLocal();
const gebruiker = kiesGebruiker(env);
const cookie = tekenSessie(env, gebruiker);
const schermen = vindSchermen();

try {
  const antwoord = await fetch(BASIS, { redirect: "manual" });
  void antwoord;
} catch {
  faal(`geen server op ${BASIS}. Start hem eerst met \`make dev\`.`);
}

mkdirSync(uitvoermap, { recursive: true });

const browser = await chromium
  .launch({ channel: "chrome" })
  .catch(() => faal("Chrome niet gevonden. `channel: \"chrome\"` vereist een geïnstalleerde Google Chrome."));

const url = new URL(BASIS);
let aantal = 0;

for (const taal of TALEN) {
  const context = await browser.newContext({ viewport: { width: BREEDTE, height: HOOGTE } });
  await context.addCookies([
    { name: SESSIE_COOKIE, value: cookie, domain: url.hostname, path: "/", httpOnly: true, sameSite: "Lax" },
    { name: TAAL_COOKIE, value: taal, domain: url.hostname, path: "/", httpOnly: true, sameSite: "Lax" },
  ]);
  const pagina = await context.newPage();

  for (const scherm of schermen) {
    // Niet op `networkidle` wachten: de dev-server houdt HMR-verbindingen open
    // en dan komt "idle" soms nooit. `load` plus een vaste rusttijd volstaat;
    // één herkansing voor een pagina die de dev-server nog moet compileren.
    try {
      await pagina.goto(`${BASIS}${scherm.route}`, { waitUntil: "load", timeout: 60_000 });
    } catch {
      await pagina.goto(`${BASIS}${scherm.route}`, { waitUntil: "load", timeout: 60_000 });
    }
    if (!pagina.url().startsWith(`${BASIS}${scherm.route === "/" ? "" : scherm.route}`)) {
      faal(`${scherm.route} (${taal}) leidde om naar ${pagina.url()} — sessiecookie niet aanvaard?`);
    }
    await pagina.waitForTimeout(800); // lettertypes en late hydratie

    const dicht = path.join(uitvoermap, `${scherm.naam}-${taal}.png`);
    await pagina.screenshot({ path: dicht, fullPage: true });
    aantal += 1;
    console.log(`  ${dicht}`);

    // Ingeklapte uitleg (MeerInfo is een native <details>) ook eenmaal open
    // vastleggen: tekst die niemand ooit opengeklapt zag, is niet gecontroleerd.
    const details = await pagina.evaluate(() => {
      const alle = Array.from(document.querySelectorAll("details:not([open])"));
      for (const d of alle) d.setAttribute("open", "");
      return alle.length;
    });
    if (details > 0) {
      await pagina.waitForTimeout(150);
      const open = path.join(uitvoermap, `${scherm.naam}-${taal}-open.png`);
      await pagina.screenshot({ path: open, fullPage: true });
      aantal += 1;
      console.log(`  ${open}`);
    }
  }
  await context.close();
}

await browser.close();
console.log(`Klaar: ${aantal} schermafbeeldingen in ${path.resolve(uitvoermap)} (gebruiker: ${gebruiker}).`);
