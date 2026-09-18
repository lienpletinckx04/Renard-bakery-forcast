"use client";

import { useEffect, useState } from "react";

import { alsTaal, maakT, STANDAARDTAAL, TAAL_COOKIE, type Taal } from "@/lib/taal";

/**
 * De foutgrens rond de schermen.
 *
 * WAAROM DIT BESTAAT. Tot 18 augustus 2026 had het platform er geen. Elke
 * onverwachte fout — een contract dat niet gelezen kan worden, een PostgREST
 * die 500 geeft, een veld dat van vorm verandert — kwam bij de bezoeker aan
 * als de kale Next-tekst "Application error: a server-side exception has
 * occurred". `lib/laadContract.ts` werpt zorgvuldig geformuleerde
 * herstelzinnen ("draai de nachtelijke sync"), maar die haalden het scherm
 * nooit: Next vervangt de melding van een serverfout in productie door een
 * generieke tekst plus een digest, juist om te voorkomen dat interne details
 * uitlekken. Alle moeite ging dus naar het log.
 *
 * Wat een lezer wél hoort te krijgen staat hieronder: dat dit een storing is
 * en geen uitkomst (een leeg scherm is anders niet te onderscheiden van een
 * dag zonder omzet), een knop om het opnieuw te proberen, en de digest waarmee
 * een beheerder de fout in het log terugvindt.
 *
 * `error.tsx` op dít niveau en niet in (dash)/: een error-bestand omsluit de
 * pagina's en de geneste layouts ónder zich, maar niet de layout in zijn eigen
 * segment. De worp die we hier het vaakst verwachten komt uit
 * `app/(dash)/layout.tsx` zelf, en die wordt alleen door deze gevangen.
 *
 * De prop heet `retry` en niet `reset` — dat is de vorm van deze Next-versie
 * (zie node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/error.md).
 */
export default function Fout({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  // De taal komt uit de cookie en niet uit de server: een foutgrens is een
  // clientcomponent en krijgt geen props van een bladzijde mee. In een effect
  // en niet tijdens het renderen, zodat server- en clientuitkomst gelijk zijn.
  const [taal, setTaal] = useState<Taal>(STANDAARDTAAL);
  useEffect(() => {
    const rauw = document.cookie
      .split("; ")
      .find((c) => c.startsWith(`${TAAL_COOKIE}=`))
      ?.split("=")[1];
    setTaal(alsTaal(rauw));
  }, []);

  useEffect(() => {
    console.error(error);
  }, [error]);

  const t = maakT(taal);

  return (
    <main className="mx-auto max-w-prose px-6 py-16">
      <section className="rounded-klein border border-warmgrijs bg-wit p-6">
        <h1 className="text-base font-medium text-zwart">{t("fout.titel")}</h1>
        <p className="mt-3 text-sm font-light text-zwart">{t("fout.uitleg")}</p>

        <button
          type="button"
          onClick={() => retry()}
          className="mt-6 rounded-klein bg-bordeaux px-4 py-2 text-sm font-medium text-wit"
        >
          {t("fout.opnieuw")}
        </button>

        <p className="mt-6 text-xs font-light text-zwart">
          {t("fout.beheerder")}{" "}
          {/* De digest is een machinewaarde en geen tekst: hij blijft in beide
              talen hetzelfde en gaat daarom niet door het woordenboek. */}
          <code>{error.digest ?? t("fout.geenCode")}</code>
        </p>
      </section>
    </main>
  );
}
