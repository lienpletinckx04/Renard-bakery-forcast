#!/usr/bin/env node
/**
 * Maakt één regel voor `PLATFORM_GEBRUIKERS`.
 *
 * Het wachtwoord komt van standaardinvoer, niet van de opdrachtregel: een
 * argument belandt in de geschiedenis van de shell en in de procestabel, en
 * een wachtwoord hoort op geen van beide plaatsen.
 *
 *   node scripts/maak_gebruiker.mjs <naam> <beheerder|lezer>
 *
 * Uitvoer is één regel `naam:rol:<zout>.<afdruk>`. Zet die achter
 * PLATFORM_GEBRUIKERS in platform/.env.local (komma's tussen gebruikers).
 * Dat bestand is gitignored en hoort dat te blijven.
 *
 * De parameters staan gelijk aan platform/lib/auth.ts. Wijken ze uiteen, dan
 * komt niemand meer binnen.
 */
import { pbkdf2Sync, randomBytes } from "node:crypto";

const ITERATIES = 210_000;
const LENGTE = 32;

const b64url = (buf) => buf.toString("base64url");

const [naam, rol] = process.argv.slice(2);
if (!naam || !["beheerder", "lezer"].includes(rol ?? "")) {
  console.error("Gebruik: node scripts/maak_gebruiker.mjs <naam> <beheerder|lezer>");
  process.exit(1);
}

let invoer = "";
for await (const stuk of process.stdin) invoer += stuk;
const wachtwoord = invoer.replace(/\r?\n$/, "");

if (wachtwoord.length < 6) {
  console.error("Wachtwoord is leeg of te kort (minstens 6 tekens).");
  process.exit(1);
}

const zout = randomBytes(16);
const afdruk = pbkdf2Sync(wachtwoord, zout, ITERATIES, LENGTE, "sha256");

// Scheidingsteken is een punt, geen `$`: env-loaders doen variabele-expansie
// op `$…` en slopen de afdruk dan stilletjes. Zie platform/lib/auth.ts.
console.log(`${naam.toLowerCase()}:${rol}:${b64url(zout)}.${b64url(afdruk)}`);
