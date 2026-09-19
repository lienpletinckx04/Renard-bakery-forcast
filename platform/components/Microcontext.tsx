import type { ContextItem } from "@/lib/contract";
import { aantal, euro, verschilProcent } from "@/lib/format";
import { richtingChip } from "@/lib/signaal";

function tekst(item: ContextItem): string {
  switch (item.soort) {
    case "euro":
      return euro(item.waarde);
    case "aantal":
      return aantal(item.waarde);
    case "verschil":
      return verschilProcent(item.waarde);
  }
}

/**
 * De regel cijfers onder een grafiek: totaal, gemiddelde, beste dag,
 * verschil met de vorige periode. Labels en waarden komen kant-en-klaar uit
 * het contract; hier wordt alleen opgemaakt, nooit gerekend.
 *
 * Bedragen en aantallen in zwart. Een VERSCHIL draagt sinds 18 september 2026
 * de signaalkleur van zijn richting, naast pijl en teken -- zie lib/signaal.ts
 * voor waarom dat één tabel is en niet per component een eigen keuze.
 */
export default function Microcontext({ items }: { items: ContextItem[] }) {
  if (items.length === 0) return null;
  return (
    <dl className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-warmgrijs pt-4">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="kapitaal-label text-zwart">{item.label}</dt>
          <dd
            className={`mt-0.5 text-sm tabular-nums ${
              item.soort === "verschil"
                ? richtingChip(item.richting) || "font-medium text-zwart"
                : "font-semibold text-zwart"
            }`}
          >
            {item.soort === "verschil" && item.richting ? (
              <span aria-hidden="true">
                {item.richting === "neer" ? "↓ " : "↑ "}
              </span>
            ) : null}
            {tekst(item)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
