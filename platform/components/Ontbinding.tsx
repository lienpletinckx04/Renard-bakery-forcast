import MeerInfo from "@/components/MeerInfo";
import type { Ontbinding as OntbindingData } from "@/lib/contract";
import { euro, procent } from "@/lib/format";
import { richtingKleur, richtingStatus, STATUSLIJN, STATUSVLAK } from "@/lib/signaal";

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

/** De tekstkleur van een bedrag met richting; zwart zonder richting. Vet
    in beide gevallen: dit zijn de bedragen die de lezer natelt. */
function inkt(richting: "op" | "neer" | null): string {
  // Geen template literal met tekst vooraan: de tekstwacht in
  // geen-harde-tekst.test.ts leest "font-bold " dan als schermtekst.
  return ["font-bold", richtingKleur(richting) || "text-zwart"].join(" ");
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
  const status = richtingStatus(data.verschil.richting);
  return (
    <div>
      {/* Eerst de zin, dan de cijfers. De conclusie komt uit het contract,
          uit de data; hier staat ze groot en in de kleur van de richting,
          zodat wie geen tijd heeft na één regel weet wat er gebeurde. */}
      {data.conclusie ? (
        <p
          className={`mb-5 rounded-klein border-l-4 py-2 pl-3 pr-3 text-base font-bold text-zwart ${STATUSLIJN[status]} ${STATUSVLAK[status]}`}
        >
          {data.conclusie}
        </p>
      ) : null}
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
              {/* Het aandeel in het verschil, klein erachter: zo leest
                  "vooral van klanten" als 80 % en niet als een gevoel. */}
              {term.aandeel ? (
                <span className="ml-2 text-xs font-light text-zwart">
                  {procent(term.aandeel)}
                </span>
              ) : null}
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
