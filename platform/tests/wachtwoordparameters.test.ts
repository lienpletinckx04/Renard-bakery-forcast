/**
 * De wacht op de wachtwoordparameters.
 *
 * `scripts/maak_gebruiker.mjs` (in de wortel van de repo) maakt de afdruk die
 * in PLATFORM_GEBRUIKERS belandt; `platform/lib/auth.ts` rekent bij het
 * aanmelden dezelfde afdruk opnieuw uit en vergelijkt. Dat werkt alleen zolang
 * beide met exact dezelfde parameters rekenen: iteraties, sleutellengte en
 * digest. Lopen ze uiteen, dan keurt auth.ts elke nieuwe afdruk af en komt er
 * niemand meer binnen — zonder foutmelding die de oorzaak verraadt, want
 * "wachtwoord klopt niet" is dan letterlijk wat het systeem denkt.
 *
 * De kop van het script zégt dat de parameters gelijk moeten blijven, maar tot
 * 18 augustus 2026 toetste niets dat. Deze test leest daarom beide bronnen en
 * houdt de waarden tegen elkaar. Bewust via de brontekst en niet via import:
 * auth.ts leunt op Web Crypto en het script op node:crypto, en de constanten
 * zijn in geen van beide geëxporteerd — exporteren alleen voor een test zou
 * een tweede waarheid maken naast de tekst die de runtime werkelijk gebruikt.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const AUTH = path.join(import.meta.dirname, "..", "lib", "auth.ts");
const SCRIPT = path.join(
  import.meta.dirname,
  "..",
  "..",
  "scripts",
  "maak_gebruiker.mjs",
);

/** "210_000" -> 210000: de numerieke onderstrepingen zijn leeshulp, geen waarde. */
function getal(bron: string, patroon: RegExp, waar: string): number {
  const m = patroon.exec(bron);
  assert.ok(m, `${waar}: patroon ${patroon} niet gevonden — is de constante hernoemd?`);
  return Number(m[1]!.replace(/_/g, ""));
}

function tekst(bron: string, patroon: RegExp, waar: string): string {
  const m = patroon.exec(bron);
  assert.ok(m, `${waar}: patroon ${patroon} niet gevonden — is de aanroep herschreven?`);
  return m[1]!;
}

test("auth.ts en maak_gebruiker.mjs rekenen met dezelfde wachtwoordparameters", () => {
  const auth = readFileSync(AUTH, "utf-8");
  const script = readFileSync(SCRIPT, "utf-8");

  const authIteraties = getal(auth, /const ITERATIES = ([\d_]+);/, "lib/auth.ts");
  const authLengte = getal(auth, /const SLEUTELLENGTE = ([\d_]+);/, "lib/auth.ts");
  // De digest van de PBKDF2-afleiding, niet die van de sessie-HMAC verderop.
  const authDigest = tekst(
    auth,
    /name:\s*"PBKDF2"[^}]*hash:\s*"([^"]+)"/,
    "lib/auth.ts",
  );

  const scriptIteraties = getal(script, /const ITERATIES = ([\d_]+);/, "scripts/maak_gebruiker.mjs");
  const scriptLengte = getal(script, /const LENGTE = ([\d_]+);/, "scripts/maak_gebruiker.mjs");
  const scriptDigest = tekst(
    script,
    /pbkdf2Sync\([^)]*"([^"]+)"\)/,
    "scripts/maak_gebruiker.mjs",
  );

  const uitleg =
    "auth.ts en maak_gebruiker.mjs rekenen dan verschillende afdrukken uit " +
    "van hetzelfde wachtwoord: elke gebruiker die met het script wordt " +
    "aangemaakt, wordt bij het aanmelden afgekeurd en niemand komt meer binnen.";

  assert.equal(
    scriptIteraties,
    authIteraties,
    `Het aantal PBKDF2-iteraties verschilt (script ${scriptIteraties}, auth ${authIteraties}). ${uitleg}`,
  );
  assert.equal(
    scriptLengte,
    authLengte,
    `De sleutellengte verschilt (script ${scriptLengte}, auth ${authLengte}). ${uitleg}`,
  );
  // Web Crypto schrijft "SHA-256", node:crypto "sha256": zelfde algoritme,
  // andere spelling. Vergelijk genormaliseerd.
  const normaal = (d: string) => d.toLowerCase().replace(/-/g, "");
  assert.equal(
    normaal(scriptDigest),
    normaal(authDigest),
    `De digest verschilt (script "${scriptDigest}", auth "${authDigest}"). ${uitleg}`,
  );
});
