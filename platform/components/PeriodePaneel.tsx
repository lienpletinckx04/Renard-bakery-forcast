"use client";

import { useId, useState } from "react";

import Lijngrafiek from "@/components/Lijngrafiek";
import Microcontext from "@/components/Microcontext";
import Staafgrafiek from "@/components/Staafgrafiek";
import type {
  Lijndata,
  Onbeschikbaar,
  PeriodeVenster,
  Staafdata,
} from "@/lib/contract";
import { reden } from "@/lib/toelichting";

/**
 * De periodekiezer met het bijbehorende venster. Interactief, maar dom:
 * de keuze bepaalt alleen wélk voorgebakken blok uit de periodekubus getoond
 * wordt — elke reeks, as en vergelijking is door de berekeningslaag al
 * gerekend (harde regel 4).
 *
 * Huisstijl: de actieve knop draagt bordeaux als identiteitskleur van de
 * actieve staat (zoals de navigatie), nooit als betekenis. Alle cijfers in
 * het venster blijven zwart.
 */
export default function PeriodePaneel({
  vensters,
  label,
  meetdagenTitel,
  geenMetingTitel,
  geenMetingTekst,
  meetdagenTekst,
  bandLabel,
  redenen,
}: {
  vensters: PeriodeVenster[];
  /** Voorgelezen naam van de tabgroep, in de taal van de lezer. */
  label: string;
  /** Doorgegeven aan de staafgrafiek; zie Staafgrafiek voor de vorm. */
  meetdagenTitel?: string;
  geenMetingTitel?: string;
  geenMetingTekst?: string;
  meetdagenTekst?: string;
  /** Doorgegeven aan de lijngrafiek; zie Lijngrafiek voor de vorm. */
  bandLabel?: string;
  /**
   * De onbeschikbaar-regels van het scherm. Een venster zonder grafiek zoekt
   * hier zijn reden op (veld "periodes.<sleutel>") in plaats van een leegte
   * te laten — de vondst van open-punten.md die de audit van 15 aug herhaalde.
   */
  redenen?: Onbeschikbaar[];
}) {
  // Het contract wijst het openingsvenster aan; draagt geen enkel venster de
  // vlag, dan het eerste — het gedrag van vóór dit veld. De knopvolgorde loopt
  // van kort naar lang en zegt dus niets over wat opent.
  const opening = vensters.find((v) => v.standaard) ?? vensters[0];
  const [actief, zetActief] = useState(opening?.sleutel ?? "");
  // Voor het tab/tabpanel-koppel hieronder: de kiezer kan vaker dan één keer
  // op een bladzijde staan, dus de ids moeten per exemplaar uniek zijn.
  const basisId = useId();
  const venster = vensters.find((v) => v.sleutel === actief) ?? vensters[0];
  if (!venster) return null;

  // Levert het contract geen reden, dan blijft het stil zoals voorheen: een
  // lege alinea met marges zou zelf een gat zijn, en een zin verzinnen mag
  // niet (harde regel 4).
  const grafiekReden =
    venster.grafiek === null
      ? reden(redenen ?? [], `periodes.${venster.sleutel}`)
      : null;

  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        className="flex flex-wrap gap-x-5 gap-y-1 border-b border-warmgrijs pb-2"
      >
        {vensters.map((v) => {
          const isActief = v.sleutel === venster.sleutel;
          return (
            <button
              key={v.sleutel}
              // Zonder type is een knop in een form een submitknop: één klik
              // op een periode zou dan het omringende formulier versturen.
              type="button"
              role="tab"
              id={`${basisId}-tab-${v.sleutel}`}
              aria-selected={isActief}
              aria-controls={`${basisId}-paneel`}
              onClick={() => zetActief(v.sleutel)}
              className={`kapitaal-label -mb-[calc(0.5rem+1px)] border-b-2 pb-2 transition-colors ${
                isActief
                  ? "border-bordeaux text-bordeaux"
                  : "border-transparent text-zwart hover:border-warmgrijs"
              }`}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      <div
        className="pt-4"
        role="tabpanel"
        id={`${basisId}-paneel`}
        aria-labelledby={`${basisId}-tab-${venster.sleutel}`}
      >
        {venster.grafiek === null ? (
          grafiekReden ? (
            <p className="max-w-prose text-sm font-light text-zwart">
              {grafiekReden}
            </p>
          ) : null
        ) : venster.soort === "lijn" ? (
          <Lijngrafiek data={venster.grafiek as Lijndata} bandLabel={bandLabel} />
        ) : (
          <Staafgrafiek
            data={venster.grafiek as Staafdata}
            meetdagenTitel={meetdagenTitel}
            geenMetingTitel={geenMetingTitel}
            geenMetingTekst={geenMetingTekst}
            meetdagenTekst={meetdagenTekst}
          />
        )}
        <Microcontext items={venster.context} />
        <p className="mt-3 max-w-prose text-sm font-light text-zwart">
          {venster.toelichting}
        </p>
      </div>
    </div>
  );
}
