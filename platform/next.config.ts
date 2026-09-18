import type { NextConfig } from "next";

/**
 * DE BOUW WEIGERT OP VERCEL ZONDER CONTRACT_BRON=db.
 *
 * Het contract staat als bestanden in `platform/contract/`, en die map is
 * gitignored (het zijn geaggregeerde omzetcijfers van de eindklant). Een
 * Vercel-build kloont de repo, dus daar bestaat die map niet. Alle routes zijn
 * dynamisch, waardoor de build het contract nooit aanraakt en niets merkt: de
 * deploy wordt groen en élk scherm valt daarna om met ENOENT. Gemeten op
 * 18 aug 2026 — `npm run build` slaagt in 791 ms zonder één contractbestand.
 *
 * Dat is de gevaarlijkste faalvorm die dit platform kent: niet een fout, maar
 * een geslaagde deploy die niet werkt. Wie hem vindt, vindt hem op de dag dat
 * er een URL gedeeld wordt.
 *
 * Deze wacht zet dat om in een bouwfout met de reden erbij. Alleen op Vercel
 * (`process.env.VERCEL`), zodat een lokale build en `next dev` op de
 * bestandsroute blijven werken zoals altijd.
 */
if (process.env.VERCEL && process.env.CONTRACT_BRON !== "db") {
  throw new Error(
    "CONTRACT_BRON staat niet op 'db'. Op Vercel bestaat platform/contract/ " +
      "niet (gitignored), dus de bestandsroute levert een deploy op die " +
      "slaagt en daarna op elk scherm faalt. Zet CONTRACT_BRON=db in de " +
      "Vercel-omgeving, samen met NEXT_PUBLIC_SUPABASE_URL en " +
      "SUPABASE_SECRET_KEY, en laad het contract met `make db-contract`.",
  );
}

/**
 * Vrijwel leeg, en dat is een keuze: de standaardinstellingen van Next
 * volstaan in fase 1, en elke regel die hier bijkomt moet zijn bestaansrecht
 * uitschrijven. De eerste uitzondering: de `x-powered-by`-header gaat uit —
 * die verraadt de stack aan iedereen die de headers leest, en niemand aan
 * de goede kant heeft hem nodig (18 aug 2026).
 */
const nextConfig: NextConfig = {
  poweredByHeader: false,

  /**
   * De tweede uitzondering, en de reden staat hier omdat elke regel in dit
   * bestand er een moet dragen.
   *
   * Een server-actie mag standaard één megabyte aan invoer krijgen. Het scherm
   * Deliveroo-import stuurt een export als bytes door een server-actie, en de
   * poort daar (lib/deliveroo-upload.ts) laat tien megabyte toe. Zonder deze
   * regel weigert het framework zo'n bestand vóór de actie ook maar begint —
   * met zijn eigen foutmelding, in zijn eigen taal, buiten het woordenboek om,
   * en de beheerder leest dat als "het platform is stuk".
   *
   * Twaalf en niet tien: nét boven de eigen grens. Zo is het altijd de eigen
   * poort die het te grote bestand afwijst, met een zin die zegt hoe groot het
   * wél mag zijn — en dekt de marge tegelijk de omhaal van de verzending
   * (base64 en de formuliergrenzen maken de verzonden bytes groter dan het
   * bestand zelf). Een grens die precies op tien stond, zou een bestand van
   * negen en een halve megabyte alsnog door het framework laten weigeren.
   */
  experimental: {
    serverActions: {
      bodySizeLimit: "12mb",
    },
  },
};

export default nextConfig;
