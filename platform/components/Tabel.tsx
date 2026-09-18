import type { Tabeldata } from "@/lib/contract";

/** Rustige tabel: 1px warmgrijze lijnen, cijfers rechts uitgelijnd en zwart. */
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
                  {cel}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
