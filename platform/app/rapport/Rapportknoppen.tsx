"use client";

import { useEffect } from "react";

/**
 * De afdrukknop van het rapport, en het openzetten van wat ingeklapt staat.
 *
 * WAAROM EEN KNOP EN NIET "GEBRUIK CTRL+P". Het rapport is de plek waar een
 * lezer een PDF verwacht; de weg ernaartoe hoort niet in een instructie te
 * staan. De knop opent het afdrukvenster van de browser, en daar zit "Opslaan
 * als PDF" in. Dat is dezelfde tekening als op het scherm — geen tweede
 * opmaaklaag die kan gaan afwijken.
 *
 * WAAROM DE UITKLAPPERS OPEN. De schermen zetten langere toelichting achter een
 * `<details>` (zie MeerInfo). Op een scherm is dat rust; in een document is het
 * verlies — wat dichtklapt, staat niet in de PDF. CSS kan een `<details>` niet
 * openen, dus doet dit hier één regel JavaScript, en alleen binnen het rapport.
 */
export default function Rapportknoppen({
  label,
  omschrijving,
}: {
  /** Wat er op de knop staat, kort. */
  label: string;
  /** Wat een schermlezer voorleest en wat bij aanwijzen verschijnt, voluit. */
  omschrijving: string;
}) {
  useEffect(() => {
    // Alleen binnen #rapport: de knoppenrij zelf en het keuzemenu zijn ook
    // <details>, en die horen dicht te blijven staan.
    for (const uitklap of document.querySelectorAll<HTMLDetailsElement>(
      "#rapport details",
    )) {
      uitklap.open = true;
    }
  }, []);

  return (
    <button
      type="button"
      title={omschrijving}
      aria-label={omschrijving}
      onClick={() => window.print()}
      className="kapitaal-label rounded-klein bg-bordeaux px-3 py-1.5 text-beige focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
    >
      {label}
    </button>
  );
}
