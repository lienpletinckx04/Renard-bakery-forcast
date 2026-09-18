"use client";

import { useTransition } from "react";

import { kiesTaal } from "@/app/(dash)/taal-acties";
import { TALEN, type Taal } from "@/lib/taal";

/**
 * De taalknop: vast linksonder, op elk scherm, klein.
 *
 * WAAROM VAST EN NIET IN DE VOETTEKST. De voettekst staat onderaan de
 * inhoudskolom, en die kolom begint op een breed scherm rechts van het bordeaux
 * zijvlak — "linksonder" zou daar dus niet linksonder zijn. Vast gepositioneerd
 * is het op elk formaat dezelfde plek.
 *
 * WAAROM EEN BEIGE DRAGER. Het element zweeft over twee heel verschillende
 * ondergronden: het beige paginavlak en het bordeaux zijvlak. Zwarte tekst op
 * bordeaux is onleesbaar, beige tekst op beige ook. Een beige drager maakt de
 * ondergrond irrelevant, en beige is de grondkleur van het merk — geen kader
 * dat erbij komt, maar hetzelfde vlak dat er al is.
 *
 * HUISSTIJL. Geen kleur die betekenis draagt: de actieve taal is zwaarder
 * gezet, niet gekleurd. Dat is dezelfde regel als bij de cijfers — richting en
 * staat komen uit vorm, niet uit kleur.
 */
export default function TaalKiezer({
  actief,
  label,
}: {
  actief: Taal;
  /** Voorgelezen naam van de groep, in de taal die nu geldt. */
  label: string;
}) {
  const [bezig, start] = useTransition();

  return (
    <div
      className="niet-afdrukken fixed bottom-3 left-3 z-40 flex items-center gap-1 rounded-klein bg-beige/95 px-2 py-1"
      role="group"
      aria-label={label}
    >
      {TALEN.map((taal) => {
        const isActief = taal === actief;
        return (
          <button
            key={taal}
            type="button"
            lang={taal}
            disabled={bezig || isActief}
            aria-current={isActief ? "true" : undefined}
            onClick={() => start(() => kiesTaal(taal))}
            className={
              "rounded-klein px-1.5 py-0.5 text-[0.6875rem] uppercase tracking-[0.08em] text-zwart outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart " +
              (isActief
                ? "font-semibold"
                : "font-light underline-offset-2 hover:underline disabled:opacity-50")
            }
          >
            {taal}
          </button>
        );
      })}
    </div>
  );
}
