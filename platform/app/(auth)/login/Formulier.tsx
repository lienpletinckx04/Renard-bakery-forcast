"use client";

import { useActionState } from "react";

import { maakT, type Taal } from "@/lib/taal";
import { aanmelden, type Uitkomst } from "./acties";

const LEEG: Uitkomst = {};

const VELD =
  "w-full border-0 border-b-2 border-warmgrijs bg-transparent px-0 py-2 text-base " +
  "text-zwart outline-none transition-colors focus:border-bordeaux placeholder:text-zwart/45";

/**
 * Alleen het formulier; de compositie eromheen staat in page.tsx. Een wit
 * paneel met een dunne rand houdt de velden leesbaar op het lijnpatroon.
 * Bordeaux zit op de knop en op de focusstaat: merkaccent en actieve staat,
 * nergens betekenis.
 */
export default function Formulier({
  terug,
  taal,
}: {
  terug: string;
  taal: Taal;
}) {
  const [uitkomst, actie, bezig] = useActionState(aanmelden, LEEG);
  const t = maakT(taal);

  return (
    <div className="w-full max-w-sm rounded-klein border border-warmgrijs bg-wit p-8 sm:p-10">
      <h1 className="kapitaal-kop text-zwart">{t("login.titel")}</h1>
      <p className="mt-1 text-sm font-light text-zwart">
        {t("login.ondertitel")}
      </p>

      <form action={actie} className="mt-8 space-y-6">
        <input type="hidden" name="terug" value={terug} />

        <label className="block">
          <span className="kapitaal-label mb-1 block text-zwart">
            {t("login.gebruiker")}
          </span>
          <input
            type="text"
            name="gebruiker"
            autoComplete="username"
            autoFocus
            spellCheck={false}
            autoCapitalize="none"
            className={VELD}
          />
        </label>

        <label className="block">
          <span className="kapitaal-label mb-1 block text-zwart">
            {t("login.wachtwoord")}
          </span>
          <input
            type="password"
            name="wachtwoord"
            autoComplete="current-password"
            className={VELD}
          />
        </label>

        <button
          type="submit"
          disabled={bezig}
          className="mt-2 w-full rounded-klein bg-bordeaux px-4 py-3 text-sm font-semibold uppercase tracking-[0.14em] text-wit transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {bezig ? t("login.bezig") : t("login.knop")}
        </button>

        {/* Vaste hoogte, zodat het formulier niet verspringt bij een fout. */}
        <p aria-live="polite" className="min-h-[1.25rem] text-xs font-light text-zwart">
          {uitkomst.fout ? t(uitkomst.fout) : null}
        </p>
      </form>
    </div>
  );
}
