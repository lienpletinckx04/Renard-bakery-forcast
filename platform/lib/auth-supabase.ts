import type { Rol, Sessie } from "./auth";
import { SESSIEDUUR_SECONDEN } from "./auth";

/**
 * Aanmelden tegen Supabase Auth (blok 12), achter dezelfde gevel als de
 * omgevingsgebaseerde laag.
 *
 * Wat hier bewust NIET verandert: de sessie, de cookie en de bewaking in
 * `proxy.ts`. `lib/auth.ts` beloofde vanaf dag één dat alleen `verifieer()`
 * zou wisselen, en dit bestand is die wissel. Supabase toetst het wachtwoord
 * en levert de rol; daarna is de sessie weer de onze — ondertekend met
 * PLATFORM_SESSIE_SLEUTEL, twaalf uur geldig, en bij elk verzoek getoetst.
 *
 * WAAROM DE PASSWORD-GRANT EN NIET @supabase/ssr. De ssr-bibliotheek beheert
 * Supabase-sessies in eigen cookies met refresh-logica — een tweede
 * sessiemechanisme naast het onze, precies wat we niet willen zolang de rest
 * van het platform niets van Supabase hoeft te weten. De token-endpoint met
 * `grant_type=password` is de kleinste koppeling die het wachtwoord echt
 * toetst. Het teruggegeven access token gooien we weg: wij hoeven niets
 * namens de gebruiker bij Supabase te doen.
 *
 * WAT ER MOET GEBEUREN VOORDAT DIT AAN KAN (zie todo S12/S13):
 *   1. zelfregistratie uit (Administrator, Sign In / Providers);
 *   2. de gebruikers aangemaakt via uitnodiging, elk met `rol` in
 *      app_metadata: "beheerder" of "lezer" (S13, de gebruikerslijst);
 *   3. AUTH_BRON=supabase in de omgeving van de deploy.
 * Zonder die drie blijft de omgevingslaag gewoon werken.
 */

/** De vorm die we van de token-endpoint nodig hebben; de rest negeren we. */
type SupabaseGebruiker = {
  email?: string;
  app_metadata?: Record<string, unknown>;
};

/**
 * De rol komt uit `app_metadata` en nergens anders. `user_metadata` is door
 * de gebruiker zelf te schrijven via de Auth-API — wie de rol daar zou
 * lezen, laat een lezer zichzelf tot beheerder benoemen.
 */
export function rolUit(gebruiker: SupabaseGebruiker): Rol | null {
  const rol = gebruiker.app_metadata?.rol;
  if (rol === "beheerder" || rol === "lezer") return rol;
  return null;
}

/**
 * Van Supabase-antwoord naar onze sessie. Zonder geldige rol komt er geen
 * sessie: een gebruiker zonder rol is een configuratiefout, en de veilige
 * lezing daarvan is "geen toegang", niet "dan maar lezer".
 */
export function sessieUitSupabase(
  gebruiker: SupabaseGebruiker,
  nuSeconden: number,
): Sessie | null {
  const rol = rolUit(gebruiker);
  const naam = gebruiker.email?.trim().toLowerCase();
  if (!rol || !naam) return null;
  return { gebruiker: naam, rol, exp: nuSeconden + SESSIEDUUR_SECONDEN };
}

/**
 * Toetst e-mail en wachtwoord bij Supabase Auth. Fouten van de endpoint
 * (verkeerd wachtwoord, onbekende gebruiker, uitgeschakeld account) zijn
 * allemaal hetzelfde antwoord: null. De aanroeper toont één neutrale melding,
 * net als bij de omgevingslaag — welke van de drie het was, is precies wat
 * een aanmeldscherm niet hoort te verklappen.
 */
export async function verifieerSupabase(
  naam: string,
  wachtwoord: string,
): Promise<Sessie | null> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const sleutel = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !sleutel) {
    // Configuratiefout, geen aanmeldfout: hardop in het serverlog, stil naar
    // de gebruiker. De sleutelwaarden zelf horen in geen enkele melding.
    console.error(
      "AUTH_BRON=supabase maar NEXT_PUBLIC_SUPABASE_URL of " +
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ontbreekt.",
    );
    return null;
  }

  let antwoord: Response;
  try {
    antwoord = await fetch(`${url}/auth/v1/token?grant_type=password`, {
      method: "POST",
      headers: { apikey: sleutel, "Content-Type": "application/json" },
      body: JSON.stringify({ email: naam.trim(), password: wachtwoord }),
      cache: "no-store",
    });
  } catch {
    console.error("Supabase Auth is niet bereikbaar.");
    return null;
  }
  if (!antwoord.ok) return null;

  const inhoud = (await antwoord.json()) as { user?: SupabaseGebruiker };
  if (!inhoud.user) return null;
  const sessie = sessieUitSupabase(inhoud.user, Math.floor(Date.now() / 1000));
  if (!sessie) {
    // De enige onderscheiden log: aangemeld bij Supabase maar zonder rol.
    // Dat is een S13-configuratiefout die iemand moet oplossen, geen
    // wachtwoordprobleem dat vanzelf overgaat.
    console.warn(
      `Supabase-gebruiker zonder geldige rol in app_metadata geweigerd.`,
    );
  }
  return sessie;
}
