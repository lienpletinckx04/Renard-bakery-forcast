"use client";

import { useState } from "react";

import type { Lijndata } from "@/lib/contract";
import { euroBedrag } from "@/lib/format";
import { KLEUR, TEKENBREEDTE, VLAK } from "@/lib/staafas";

/**
 * Inline SVG-lijngrafiek. Alles wat hier gebeurt is tekengeometrie:
 * waarden uit het contract worden naar pixels geschaald, nooit opgeteld,
 * afgerond of anderszins bewerkt. Elk leesbaar label komt kant-en-klaar
 * uit de data (punt.label, y_as.ticks[].label).
 *
 * De aanwijsstaat is de enige interactie: wie over de grafiek beweegt, ziet
 * de dag met zijn waarde (en bij een prognose de band). Ook dat is tonen en
 * niet rekenen — de tooltip zet alleen de y-waarde van het contract om naar
 * tekst, via dezelfde opmaaklaag als elk ander bedrag. Cijfers in zwart,
 * de gidslijn in warmgrijs: geen kleur met betekenis.
 */

// Zelfde tekenvlak als de staafgrafiek; de zes maten stonden hier tot
// 18 augustus 2026 als lokale kopie en konden dus ongemerkt gaan afwijken.
const B = VLAK.breedte;
const H = VLAK.hoogte;
const M = VLAK.marge;

export default function Lijngrafiek({
  data,
  compact = false,
  bandLabel,
}: {
  data: Lijndata;
  compact?: boolean;
  /**
   * Vertaald woord vóór de bandgrenzen in de tooltip ("band € 900 – € 1.100"),
   * vooraf vertaald omdat dit een clientcomponent is en een t-functie de grens
   * niet over kan — zelfde regel als de vier sjablonen van Staafgrafiek.
   * Zonder label geen bandregel: een eentalige terugval zou op een Frans
   * scherm Nederlands tonen.
   */
  bandLabel?: string;
}) {
  const [actief, zetActief] = useState<number | null>(null);

  const ticks = data.y_as.ticks;
  const yMin = Math.min(...ticks.map((t) => t.y));
  const yMax = Math.max(...ticks.map((t) => t.y));
  const n = data.reeksen[0]?.punten.length ?? 0;
  if (n === 0) return null;

  const hoogte = compact ? 72 : H;
  const marge = compact
    ? { links: 4, rechts: 4, boven: 6, onder: 6 }
    : M;

  const sx = (i: number) =>
    marge.links + (i * (B - marge.links - marge.rechts)) / Math.max(n - 1, 1);
  const sy = (y: number) =>
    hoogte -
    marge.onder -
    ((y - yMin) * (hoogte - marge.boven - marge.onder)) / (yMax - yMin || 1);

  const xLabelStap = n > 14 ? Math.ceil(n / 7) : 1;

  // Datumlabels staan gecentreerd onder hun punt, maar het laatste punt ligt
  // op de rechterrand van het plotvlak: een gecentreerd label steekt daar een
  // halve labelbreedte voorbij de viewBox, en die clipt ("30 août" verloor
  // zijn t). Dezelfde breedteschatting als de staafas (lib/staafas.ts) schuift
  // zo'n label net ver genoeg naar binnen; een label dat al paste, blijft op
  // de pixel staan waar het stond. Alleen plaatsing, geen stijl.
  const sxLabel = (i: number, tekst: string) => {
    const half = (tekst.length * TEKENBREEDTE) / 2;
    return Math.min(Math.max(sx(i), half), B - half);
  };

  function bijBeweging(e: React.PointerEvent<SVGSVGElement>) {
    const kader = e.currentTarget.getBoundingClientRect();
    const xInVlak = ((e.clientX - kader.left) / kader.width) * B;
    const stap = (B - marge.links - marge.rechts) / Math.max(n - 1, 1);
    const i = Math.round((xInVlak - marge.links) / stap);
    zetActief(Math.max(0, Math.min(n - 1, i)));
  }

  const actiefPunt = actief === null ? null : data.reeksen[0].punten[actief];
  const actiefBand =
    actief === null || !data.band ? null : (data.band[actief] ?? null);
  // De tooltip hangt boven het hoogste punt van de actieve dag.
  const actiefTopY =
    actief === null
      ? 0
      : Math.min(...data.reeksen.map((r) => sy(r.punten[actief]?.y ?? yMin)));

  return (
    <figure className="relative">
      <svg
        viewBox={`0 0 ${B} ${hoogte}`}
        role="img"
        aria-label={data.reeksen.map((r) => r.naam).join(", ")}
        className="w-full touch-none"
        onPointerMove={bijBeweging}
        onPointerLeave={() => zetActief(null)}
      >
        {!compact &&
          ticks.map((t) => (
            <g key={t.y}>
              <line
                x1={marge.links}
                x2={B - marge.rechts}
                y1={sy(t.y)}
                y2={sy(t.y)}
                stroke={KLEUR.warmgrijs}
                strokeWidth="1"
              />
              <text
                x={marge.links - 8}
                y={sy(t.y) + 3}
                textAnchor="end"
                fontSize="10"
                fill={KLEUR.zwart}
              >
                {t.label}
              </text>
            </g>
          ))}

        {data.band ? (
          <polygon
            points={[
              ...data.band.map((b, i) => `${sx(i)},${sy(b.boven)}`),
              ...[...data.band].reverse().map((b, i) => {
                const j = data.band!.length - 1 - i;
                return `${sx(j)},${sy(b.onder)}`;
              }),
            ].join(" ")}
            fill={KLEUR.geel}
          />
        ) : null}

        {actief !== null ? (
          <line
            x1={sx(actief)}
            x2={sx(actief)}
            y1={marge.boven}
            y2={hoogte - marge.onder}
            stroke={KLEUR.warmgrijs}
            strokeWidth="1"
          />
        ) : null}

        {data.reeksen.map((reeks) => (
          <polyline
            key={reeks.naam}
            points={reeks.punten.map((p, i) => `${sx(i)},${sy(p.y)}`).join(" ")}
            fill="none"
            stroke={KLEUR[reeks.kleur]}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {actief !== null
          ? data.reeksen.map((reeks) =>
              reeks.punten[actief] !== undefined ? (
                <circle
                  key={reeks.naam}
                  cx={sx(actief)}
                  cy={sy(reeks.punten[actief].y)}
                  r="3.5"
                  fill={KLEUR[reeks.kleur]}
                  stroke={KLEUR.wit}
                  strokeWidth="1.5"
                />
              ) : null,
            )
          : null}

        {!compact &&
          data.reeksen[0].punten.map((p, i) =>
            i % xLabelStap === 0 || i === n - 1 ? (
              <text
                key={p.x}
                x={sxLabel(i, p.x)}
                y={hoogte - 8}
                textAnchor="middle"
                fontSize="10"
                fill={KLEUR.zwart}
              >
                {p.x}
              </text>
            ) : null,
          )}
      </svg>

      {actief !== null && actiefPunt !== undefined && actiefPunt !== null ? (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+8px)] rounded-klein border border-warmgrijs bg-wit px-2.5 py-1.5 text-xs whitespace-nowrap text-zwart"
          style={{
            left: `${(sx(actief) / B) * 100}%`,
            top: `${(actiefTopY / hoogte) * 100}%`,
          }}
        >
          <div className="font-medium">{actiefPunt.x}</div>
          {data.reeksen.map((r) =>
            r.punten[actief] !== undefined ? (
              <div key={r.naam} className="tabular-nums">
                {data.reeksen.length > 1 ? (
                  <span className="font-light">{r.naam}: </span>
                ) : null}
                {euroBedrag(r.punten[actief].y)}
              </div>
            ) : null,
          )}
          {actiefBand && bandLabel ? (
            <div className="font-light tabular-nums">
              {bandLabel} {euroBedrag(actiefBand.onder)} –{" "}
              {euroBedrag(actiefBand.boven)}
            </div>
          ) : null}
        </div>
      ) : null}

      {!compact && data.reeksen.length >= 2 ? (
        <figcaption className="mt-2 flex gap-6 text-xs text-zwart">
          {data.reeksen.map((r) => (
            <span key={r.naam} className="inline-flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-2.5 w-2.5"
                style={{ backgroundColor: KLEUR[r.kleur] }}
              />
              {r.naam}
            </span>
          ))}
        </figcaption>
      ) : null}
    </figure>
  );
}
