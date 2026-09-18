"use client";

import { useTransition } from "react";

import { kiesWinkel } from "@/app/(dash)/winkel-acties";
import { maakT, type Taal } from "@/lib/taal";

/**
 * De winkelkiezer in de paginakop. Verschijnt alleen wanneer de contractbouw
 * meer dan één winkel kent; met één geheel is er niets te kiezen. "Alle
 * winkels" is het totaal — inclusief filialen die (nog) aan geen winkel zijn
 * toegewezen, dus de som van de winkels kan kleiner zijn dan het totaal.
 */
export default function WinkelKiezer({
  winkels,
  actief,
  taal,
}: {
  winkels: { naam: string; slug: string }[];
  /** Slug van de gekozen winkel, of "" voor het totaal. */
  actief: string;
  taal: Taal;
}) {
  const [bezig, start] = useTransition();
  const t = maakT(taal);
  if (winkels.length < 2) return null;

  return (
    <label className="flex items-center gap-2 text-sm text-zwart">
      <span className="font-light">{t("winkel.label")}</span>
      <select
        value={actief}
        disabled={bezig}
        onChange={(e) => start(() => kiesWinkel(e.target.value))}
        className="rounded-klein border border-warmgrijs bg-wit px-2 py-1 text-sm text-zwart outline-none focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart disabled:opacity-50"
        aria-label={t("winkel.kies")}
      >
        <option value="">{t("winkel.alle")}</option>
        {winkels.map((w) => (
          <option key={w.slug} value={w.slug}>
            {w.naam}
          </option>
        ))}
      </select>
    </label>
  );
}
