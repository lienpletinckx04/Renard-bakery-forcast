/**
 * Aanmelden zonder database.
 *
 * Poort G7 (Supabase) blokkeert de gehoste database, niet het afschermen van
 * het platform. Deze laag doet daarom hetzelfde als de berekeningslaag: ze
 * werkt vandaag zonder database, in precies de vorm die Supabase Auth later
 * overneemt. Wat per bron wisselt is `verifieer()`, plus één stap in `lees()`
 * (de herbevestiging tegen de omgevingslijst hoort alleen bij de
 * omgevingslaag); de sessie, de cookie en de bewaking in `proxy.ts` blijven
 * zoals ze zijn.
 *
 * Wat hier bewust NIET gebeurt:
 *   * geen wachtwoord in de code, in een commit of in een chatbericht.
 *     De gebruikers staan in `PLATFORM_GEBRUIKERS`, en daar staat een
 *     PBKDF2-afdruk in, geen wachtwoord.
 *   * geen eigen cryptografie. PBKDF2-SHA256 en HMAC-SHA256 komen uit
 *     Web Crypto, dat in zowel de Edge- als de Node-runtime bestaat.
 *   * geen vergelijking die op het eerste verschil stopt. Zowel de afdruk
 *     als de handtekening worden in constante tijd getoetst.
 */

/** OWASP-richtlijn voor PBKDF2-SHA256 (2023). */
const ITERATIES = 210_000;
const SLEUTELLENGTE = 32;

/** Hoe lang een sessie meegaat. Een werkdag plus wat lucht. */
export const SESSIEDUUR_SECONDEN = 12 * 60 * 60;

export const COOKIE = "renard_sessie";

// "lezer", niet "bekijker": scope D6 en vraag 57 (de gebruikerslijst die bij
// de klant ligt) zeggen lezer, en de code droeg tot 18 aug 2026 een eigen
// woord. Eén woord door alles heen, vóór S13 binnenkomt — daarna zou de
// hernoeming bestaande accounts raken.
export type Rol = "beheerder" | "lezer";

export type Sessie = {
  gebruiker: string;
  rol: Rol;
  /** Unix-seconden. */
  exp: number;
};

// --- codering ---------------------------------------------------------------

function naarB64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function vanB64url(tekst: string): Uint8Array {
  const s = tekst.replace(/-/g, "+").replace(/_/g, "/");
  const ruw = atob(s + "=".repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(ruw, (c) => c.charCodeAt(0));
}

/** Vergelijking in constante tijd. Stopt niet bij het eerste verschil. */
function gelijk(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let verschil = 0;
  for (let i = 0; i < a.length; i++) verschil |= a[i] ^ b[i];
  return verschil === 0;
}

// --- wachtwoorden -----------------------------------------------------------

async function afdruk(wachtwoord: string, zout: Uint8Array): Promise<Uint8Array> {
  const sleutel = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(wachtwoord),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: zout as BufferSource, iterations: ITERATIES, hash: "SHA-256" },
    sleutel,
    SLEUTELLENGTE * 8,
  );
  return new Uint8Array(bits);
}

/**
 * Vorm: `<zout>.<afdruk>`, beide base64url. Dit is wat in de omgeving staat.
 *
 * De punt als scheidingsteken is geen smaak maar een les: het was eerst een
 * `$`, en de env-loader van Next doet variabele-expansie op `.env`-bestanden,
 * waardoor alles vanaf de `$` stilletjes wegviel en niemand meer kon
 * aanmelden. Een punt komt niet voor in base64url en betekent in geen enkele
 * env-loader iets.
 */
export async function maakAfdruk(wachtwoord: string): Promise<string> {
  const zout = crypto.getRandomValues(new Uint8Array(16));
  return `${naarB64url(zout)}.${naarB64url(await afdruk(wachtwoord, zout))}`;
}

export async function klopt(wachtwoord: string, opgeslagen: string): Promise<boolean> {
  const [zoutB64, afdrukB64] = opgeslagen.split(".");
  if (!zoutB64 || !afdrukB64) return false;
  const berekend = await afdruk(wachtwoord, vanB64url(zoutB64));
  return gelijk(berekend, vanB64url(afdrukB64));
}

// --- gebruikers uit de omgeving ---------------------------------------------

type Gebruiker = { naam: string; rol: Rol; afdruk: string };

/**
 * `PLATFORM_GEBRUIKERS` = `naam:rol:<zout>$<afdruk>` per gebruiker, komma's
 * ertussen. Ontbreekt de variabele, dan is er geen enkele gebruiker en komt
 * niemand binnen — dat is het veilige antwoord, geen achterdeur.
 */
/** Elke kapotte regel één keer melden, niet bij elk verzoek opnieuw. */
const gemeld = new Set<string>();

function gebruikers(): Gebruiker[] {
  const ruw = process.env.PLATFORM_GEBRUIKERS ?? "";
  return ruw
    .split(",")
    .map((deel) => deel.trim())
    .filter(Boolean)
    .map((deel) => {
      const [naam, rol, afdruk] = deel.split(":");
      // "bekijker" is de rolnaam van vóór 18 aug 2026; bestaande lokale
      // PLATFORM_GEBRUIKERS-regels dragen hem nog en blijven geldig.
      const genormaliseerd = rol === "bekijker" ? "lezer" : rol;
      return { naam: naam?.toLowerCase(), rol: genormaliseerd as Rol, afdruk };
    })
    .filter((g) => {
      const geldig =
        g.naam &&
        g.afdruk?.includes(".") &&
        (g.rol === "beheerder" || g.rol === "lezer");
      if (!geldig && !gemeld.has(g.naam ?? "?")) {
        // Een stil weggefilterde regel kostte ooit een avond zoeken: de fout
        // was "wachtwoord klopt niet" terwijl de regel zelf kapot was. Dus:
        // hardop melden, zonder de afdruk zelf te tonen.
        gemeld.add(g.naam ?? "?");
        console.warn(
          `PLATFORM_GEBRUIKERS: regel voor "${g.naam ?? "?"}" is ongeldig ` +
            `(vorm is naam:rol:<zout>.<afdruk>) en wordt overgeslagen.`,
        );
      }
      return geldig;
    });
}

export function erZijnGebruikers(): boolean {
  // Op Supabase Auth staan de gebruikers bij Supabase, niet in de omgeving;
  // de melding "geen gebruikers geconfigureerd" zou daar altijd en onterecht
  // verschijnen.
  if (authBron() === "supabase") return true;
  return gebruikers().length > 0;
}

/**
 * Welke laag het wachtwoord toetst. "omgeving" is de standaard en het
 * bestaande gedrag; "supabase" is blok 12 en vergt S12 (zelfregistratie uit)
 * en S13 (de gebruikerslijst met rollen in app_metadata) voordat er iemand
 * binnenkomt. Elke andere waarde is een typefout en valt hardop terug op de
 * omgeving — stil een onbedoelde laag kiezen is hier het gevaar.
 */
function authBron(): "omgeving" | "supabase" {
  const bron = process.env.AUTH_BRON ?? "omgeving";
  if (bron === "supabase") return "supabase";
  if (bron !== "omgeving") {
    console.warn(
      `AUTH_BRON=${bron} is onbekend (keuze: omgeving, supabase); ` +
        "de omgevingslaag blijft actief.",
    );
  }
  return "omgeving";
}

/**
 * Toetst naam en wachtwoord, bij de laag die AUTH_BRON aanwijst. De sessie
 * die eruit komt is in beide gevallen dezelfde: van ons, ondertekend, en
 * hieronder bij elk verzoek getoetst — `lees()` verandert niet mee.
 */
export async function verifieer(naam: string, wachtwoord: string): Promise<Sessie | null> {
  if (authBron() === "supabase") {
    // Dynamisch geïmporteerd: auth-supabase leest SESSIEDUUR uit dit bestand,
    // en een statische kring tussen die twee is een bouwfout die zich pas in
    // productie toont.
    const { verifieerSupabase } = await import("./auth-supabase");
    return verifieerSupabase(naam, wachtwoord);
  }
  return verifieerOmgeving(naam, wachtwoord);
}

/**
 * De omgevingslaag: toetst tegen PLATFORM_GEBRUIKERS. Bij een onbekende naam
 * wordt er toch een afdruk berekend, zodat de duur van het antwoord niet
 * verraadt welke namen bestaan.
 */
export async function verifieerOmgeving(naam: string, wachtwoord: string): Promise<Sessie | null> {
  const gezocht = naam.trim().toLowerCase();
  const gevonden = gebruikers().find((g) => g.naam === gezocht);
  const teToetsen =
    gevonden?.afdruk ?? `${naarB64url(new Uint8Array(16))}.${naarB64url(new Uint8Array(32))}`;

  const goed = await klopt(wachtwoord, teToetsen);
  if (!gevonden || !goed) return null;

  return {
    gebruiker: gevonden.naam,
    rol: gevonden.rol,
    exp: Math.floor(Date.now() / 1000) + SESSIEDUUR_SECONDEN,
  };
}

// --- de sessie zelf ---------------------------------------------------------

async function hmacSleutel(): Promise<CryptoKey> {
  const geheim = process.env.PLATFORM_SESSIE_SLEUTEL;
  if (!geheim) throw new Error("PLATFORM_SESSIE_SLEUTEL ontbreekt");
  return crypto.subtle.importKey(
    "raw",
    vanB64url(geheim) as BufferSource,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
}

/** Vorm: `<payload>.<handtekening>`. Ondertekend, niet versleuteld. */
export async function teken(sessie: Sessie): Promise<string> {
  const payload = naarB64url(new TextEncoder().encode(JSON.stringify(sessie)));
  const sig = await crypto.subtle.sign("HMAC", await hmacSleutel(), new TextEncoder().encode(payload));
  return `${payload}.${naarB64url(new Uint8Array(sig))}`;
}

export async function lees(token: string | undefined): Promise<Sessie | null> {
  if (!token) return null;
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;

  let verwacht: ArrayBuffer;
  try {
    verwacht = await crypto.subtle.sign("HMAC", await hmacSleutel(), new TextEncoder().encode(payload));
  } catch {
    return null;
  }
  if (!gelijk(new Uint8Array(verwacht), vanB64url(sig))) return null;

  try {
    const sessie = JSON.parse(new TextDecoder().decode(vanB64url(payload))) as Sessie;
    if (typeof sessie.exp !== "number" || sessie.exp * 1000 < Date.now()) return null;

    // Op Supabase Auth staan de gebruikers bij Supabase, niet in de omgeving:
    // PLATFORM_GEBRUIKERS is daar leeg, en de herbevestiging hieronder zou
    // elke geldige sessie verwerpen — een oneindige inloglus, het platform
    // onbereikbaar. De handtekening en de vervaltijd zijn hierboven al
    // getoetst, dus de sessie uit de cookie is hier het antwoord. De prijs,
    // expliciet: op Supabase werkt een ingetrokken rol of een geschrapte
    // gebruiker pas door na afloop van de cookie (hooguit 12 uur), omdat er
    // per verzoek niet bij Supabase wordt nagevraagd.
    if (authBron() === "supabase") return sessie;

    // De cookie is ondertekend maar tot 12 uur oud. Wie er nú in de omgeving
    // staat en met welke rol, is de waarheid: een geschrapte gebruiker is
    // meteen buiten, en een ingetrokken beheerdersrol werkt meteen — niet pas
    // wanneer de cookie verloopt.
    const actueel = gebruikers().find((g) => g.naam === sessie.gebruiker);
    if (!actueel) return null;
    return { gebruiker: actueel.naam, rol: actueel.rol, exp: sessie.exp };
  } catch {
    return null;
  }
}
