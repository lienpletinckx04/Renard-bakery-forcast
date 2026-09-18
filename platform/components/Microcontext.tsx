import type { ContextItem } from "@/lib/contract";
import { aantal, euro, verschilProcent } from "@/lib/format";

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
 * het contract; hier wordt alleen opgemaakt, nooit gerekend. Alles in zwart,
 * richting via pijl en teken.
 */
export default function Microcontext({ items }: { items: ContextItem[] }) {
  if (items.length === 0) return null;
  return (
    <dl className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-warmgrijs pt-4">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="kapitaal-label text-zwart">{item.label}</dt>
          <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
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
