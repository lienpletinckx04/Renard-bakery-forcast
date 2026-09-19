import type { Cel, Tabeldata } from "@/lib/contract";
import { richtingChip } from "@/lib/signaal";

/** Eén cel: tekst, of tekst als chip in de kleur van het oordeel. */
function CelInhoud({ cel }: { cel: Cel }) {
  if (typeof cel === "string") return <>{cel}</>;
  const chip = richtingChip(cel.richting);
  if (chip) return <span className={chip}>{cel.tekst}</span>;
  return cel.vet ? <span className="font-bold">{cel.tekst}</span> : <>{cel.tekst}</>;
}

/**
 * Rustige tabel: 1px warmgrijze lijnen, cijfers rechts uitgelijnd en zwart.
 * Een cel met een oordeel (zie `Cel`) kleurt als chip; de tekst blijft
 * staan, de kleur komt erbij (lib/signaal.ts).
 */
export default function Tabel({ data }: { data: Tabeldata }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-warmgrijs">
            {data.kolommen.map((kolom, i) => (
              <th
                key={kolom}
                className={`kapitaal-label px-3 py-2 font-medium whitespace-nowrap text-zwart first:pl-0 last:pr-0 ${
                  data.uitlijning[i] === "rechts" ? "text-right" : "text-left"
                }`}
              >
                {kolom}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rijen.map((rij, r) => (
            <tr key={r} className="border-b border-warmgrijs">
              {rij.map((cel, i) => (
                <td
                  key={i}
                  className={`px-3 py-2.5 text-zwart first:pl-0 last:pr-0 ${
                    data.uitlijning[i] === "rechts"
                      ? "text-right tabular-nums whitespace-nowrap"
                      : "text-left"
                  }`}
                >
                  <CelInhoud cel={cel} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
