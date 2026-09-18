"use client";

import { useEffect, useState } from "react";

import "./globals.css";
import { alsTaal, maakT, STANDAARDTAAL, TAAL_COOKIE, type Taal } from "@/lib/taal";

/**
 * Het laatste vangnet: een fout in de wortel-layout zelf.
 *
 * `app/error.tsx` vangt de schermen en de layout van (dash). Gaat het mis in
 * `app/layout.tsx` — het lettertype, de metadata die de taalcookie leest — dan
 * is er boven die layout niets meer, en komt dit bestand in de plaats van het
 * hele document. Vandaar de eigen `<html>` en `<body>`: dat is de vorm die
 * deze Next-versie eist (zie node_modules/next/dist/docs/01-app/03-api-reference/
 * 03-file-conventions/error.md).
 *
 * `globals.css` wordt hier expliciet geïmporteerd. Een global-error vervangt de
 * wortel-layout en krijgt de stijlen daarvan niet mee; zonder deze import zou
 * het beige een kaal wit worden. De kleuren met de hand in stijlattributen
 * zetten zou werken, maar dan staan de zes tokens uit de logogids op een tweede
 * plek in de repo — en twee tabellen die hetzelfde moeten zeggen, lopen uiteen.
 *
 * Inter Tight ontbreekt wel: dat lettertype wordt door de wortel-layout op de
 * `<html>` gezet. `font-sans` valt hier dus terug op de systeem-schreefloze, en
 * dat is juist — een foutbladzijde die op een lettertype wacht, is een
 * foutbladzijde die niet verschijnt.
 */
export default function WortelFout({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
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
    <html lang={taal === "fr" ? "fr-BE" : "nl-BE"}>
      <body className="font-sans antialiased">
        {/* `<title>` als component: een global-error is een clientcomponent en
            kent daarom geen metadata-export. */}
        <title>{t("fout.titel")}</title>
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
              {/* De digest is een machinewaarde: hij is in beide talen gelijk
                  en gaat daarom niet door het woordenboek. */}
              <code>{error.digest ?? t("fout.geenCode")}</code>
            </p>
          </section>
        </main>
      </body>
    </html>
  );
}
