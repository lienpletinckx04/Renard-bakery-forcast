import MeerInfo from "@/components/MeerInfo";
import type { Ontbinding as OntbindingData } from "@/lib/contract";
import { euro } from "@/lib/format";
import { richtingKleur } from "@/lib/signaal";

/**
 * Een gemeten verschil en de termen waarin het uiteenvalt, als leesbare brug:
 * de termen eerst, het verschil eronder achter een lijn. Zo staat het bedrag
 * dat verklaard wordt op de plek waar een optelling eindigt, en kan de lezer
 * zelf natellen — de contractlaag garandeert dat het op de cent klopt.
 *
 * Hier wordt niets opgeteld en niets berekend. Elk bedrag, elk label en elke
 * uitleg komt kant-en-klaar uit het contract; deze component maakt alleen op.
 * Elke term en het verschil dragen sinds 18 september 2026 de signaalkleur
 * van hun richting, naast pijl en teken (lib/signaal.ts). Een term zonder
 * richting blijft zwart: nul is geen oordeel.
 */
function Pijl({ richting }: { richting: "op" | "neer" | null }) {
  if (richting === null) return null;
  return <span aria-hidden="true">{richting === "neer" ? "↓ " : "↑ "}</span>;
}

/** De tekstkleur van een bedrag met richting; zwart zonder richting. */
function inkt(richting: "op" | "neer" | null): string {
  return richtingKleur(richting) || "text-zwart";
}

export default function Ontbinding({
  data,
  meerLabel,
}: {
  data: OntbindingData;
  /**
   * Het label van de uitklap onder de ontbinding. Altijd meegeven: dit
   * onderdeel kent de taal van de lezer niet, en een Nederlandse terugval zou
   * op een Frans scherm één Nederlands woord achterlaten (dezelfde reden als
   * bij Toelichting en Onbeschikbaar).
   */
  meerLabel: string;
}) {
  return (
    <div>
      <ul className="space-y-4">
        {data.termen.map((term) => (
          <li
            key={term.label}
            className="flex items-baseline justify-between gap-6"
          >
            <div className="max-w-prose">
              <span className="text-sm font-medium text-zwart">
                {term.label}
              </span>
              <p className="mt-0.5 text-xs font-light text-zwart">
                {term.uitleg}
              </p>
            </div>
            <span
              className={`shrink-0 text-sm font-medium whitespace-nowrap tabular-nums ${inkt(term.richting)}`}
            >
              <Pijl richting={term.richting} />
              {euro(term.waarde)}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-4 flex items-baseline justify-between gap-6 border-t border-warmgrijs pt-4">
        <span className="text-sm font-medium text-zwart">
          {data.verschil.label}
        </span>
        <span
          className={`shrink-0 text-base font-semibold whitespace-nowrap tabular-nums ${inkt(data.verschil.richting)}`}
        >
          <Pijl richting={data.verschil.richting} />
          {euro(data.verschil.waarde)}
        </span>
      </div>

      {/* De vensteruitleg ("dertig dagen naast even veel dagen ervoor, telt op
          de cent op") lees je één keer; de bedragen erboven lees je elke dag.
          Vandaar achter een uitklap en niet weg: hij verklaart wélke twee
          periodes vergeleken worden, en zonder dat is het verschil erboven een
          getal zonder noemer. */}
      <MeerInfo label={meerLabel}>
        <p>{data.toelichting}</p>
      </MeerInfo>
    </div>
  );
}
