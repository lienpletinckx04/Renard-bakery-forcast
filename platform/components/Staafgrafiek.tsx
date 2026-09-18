"use client";

import { useState } from "react";

import type { Staafdata } from "@/lib/contract";
import { euroBedrag, geheelGetal, KASTLIJN } from "@/lib/format";
import {
  berekenStaafas,
  HOEK,
  KLEUR,
  kortAf,
  LABELOFFSET,
  VLAK,
} from "@/lib/staafas";

/**
 * Inline SVG-staafgrafiek, één of twee reeksen naast elkaar per categorie.
 * Uitsluitend tekengeometrie; zie Lijngrafiek.tsx voor het principe.
 *
 * De marges staan niet vast maar volgen uit de aslabels, want productgroepen
 * zijn lang ("Brood / Desembroden - dagelijks", 31 tekens) en liepen bij vaste
 * marges buiten de viewBox, die clipt. De maatvoering zit in lib/staafas.ts,
 * met een test op de meetkundige voorwaarde dat elk label binnen beeld valt.
 */

export default function Staafgrafiek({
  data,
  meetdagenTitel,
  geenMetingTitel,
  geenMetingTekst,
  meetdagenTekst,
}: {
  data: Staafdata;
  /**
   * Sjabloon voor de tooltip op een staaf met meetdagen, vooraf vertaald
   * omdat dit een clientcomponent is en een t-functie de grens niet over kan.
   * Invulplaatsen: {x} en {n}. Zonder sjabloon geen tooltip — een eentalige
   * terugval zou op een Frans scherm Nederlands voorlezen.
   */
  meetdagenTitel?: string;
  /** Sjabloon voor de title op een categorie zonder meting ({x}), zelfde
   * regel als meetdagenTitel: vooraf vertaald, zonder sjabloon geen title. */
  geenMetingTitel?: string;
  /** Platte tekst in de tooltip voor een categorie zonder meting; zonder
   * tekst staat er een kastlijn, die geen taal draagt. */
  geenMetingTekst?: string;
  /** Sjabloon voor het aantal meetdagen in de tooltip ({n}). */
  meetdagenTekst?: string;
}) {
  const [actief, zetActief] = useState<number | null>(null);
  const ticks = data.y_as.ticks;
  const yMax = Math.max(...ticks.map((t) => t.y));
  const yMin = 0; // staven starten op de basislijn
  const punten = data.reeksen[0]?.punten ?? [];
  const n = punten.length;
  if (n === 0) return null;

  // Lange categorienamen (productgroepen) staan schuin, anders lopen ze door
  // elkaar. Korte aslabels (ma, jan) blijven gewoon recht.
  const as = berekenStaafas(punten.map((p) => p.x));

  const vlakB = VLAK.breedte - as.links - VLAK.marge.rechts;
  const groepB = vlakB / n;
  const staafB = Math.min(28, (groepB * 0.7) / data.reeksen.length);

  const sy = (y: number) =>
    as.hoogte -
    as.ondermarge -
    ((y - yMin) * (as.hoogte - VLAK.marge.boven - as.ondermarge)) /
      (yMax - yMin || 1);

  // De aanwijsstaat: de hele kolom van een categorie is het doelvlak, de
  // andere staven wijken licht terug (nadruk, geen betekenis) en een tooltip
  // toont het volle label met de waarde — tonen, niet rekenen.
  const actiefMidden =
    actief === null ? 0 : as.links + groepB * actief + groepB / 2;
  const actiefTopY =
    actief === null
      ? 0
      : Math.min(
          ...data.reeksen
            .map((r) => r.punten[actief])
            .filter((p) => p !== undefined && p.meetdagen !== 0)
            .map((p) => sy(p.y)),
          sy(yMin),
        );

  return (
    <figure className="relative">
      <svg
        viewBox={`0 0 ${VLAK.breedte} ${as.hoogte}`}
        role="img"
        // Alleen de reeksnamen: die komen uit het contract en dragen dus al
        // de taal van de lezer. Een Nederlands omhulsel ("Staafgrafiek: …,
        // N staven") zou op een Frans scherm voorgelezen worden.
        aria-label={data.reeksen.map((r) => r.naam).join(", ")}
        className="w-full touch-none"
        onPointerLeave={() => zetActief(null)}
      >
        {ticks.map((t) => (
          <g key={t.y}>
            <line
              x1={as.links}
              x2={VLAK.breedte - VLAK.marge.rechts}
              y1={sy(t.y)}
              y2={sy(t.y)}
              stroke={KLEUR.warmgrijs}
              strokeWidth="1"
            />
            <text
              x={as.links - 8}
              y={sy(t.y) + 3}
              textAnchor="end"
              fontSize="10"
              fill={KLEUR.zwart}
            >
              {t.label}
            </text>
          </g>
        ))}

        {punten.map((_, i) => {
          const midden = as.links + groepB * i + groepB / 2;
          const totaalB =
            staafB * data.reeksen.length + 2 * (data.reeksen.length - 1);
          return data.reeksen.map((reeks, r) => {
            const p = reeks.punten[i];
            // Een reeks kan korter zijn dan reeks 0, waarvan de index komt:
            // tot 18 augustus 2026 wierp `p.meetdagen` dan en lag het hele
            // scherm plat (de tooltip-lus verderop deed dit al goed).
            if (p === undefined) return null;
            // Een gemiddelde zonder gemeten dagen is geen nul maar een
            // onbekende: dan wordt er geen staaf getekend (harde regel 8).
            if (p.meetdagen === 0) return null;
            const x = midden - totaalB / 2 + r * (staafB + 2);
            const top = sy(p.y);
            const basis = sy(yMin);
            return (
              <path
                key={`${reeks.naam}-${p.x}`}
                d={`M ${x} ${basis}
                    L ${x} ${top + 2}
                    Q ${x} ${top} ${x + 2} ${top}
                    L ${x + staafB - 2} ${top}
                    Q ${x + staafB} ${top} ${x + staafB} ${top + 2}
                    L ${x + staafB} ${basis} Z`}
                fill={KLEUR[reeks.kleur]}
                style={{
                  opacity: actief === null || actief === i ? 1 : 0.55,
                  transition: "opacity 120ms",
                }}
              >
                {p.meetdagen !== undefined && meetdagenTitel ? (
                  <title>
                    {meetdagenTitel
                      .replace("{x}", p.x)
                      .replace("{n}", geheelGetal(p.meetdagen))}
                  </title>
                ) : null}
              </path>
            );
          });
        })}

        {/* Onzichtbare doelvlakken, één per categorie: de hele kolom reageert,
            niet alleen de (soms smalle) staaf zelf. */}
        {punten.map((_, i) => (
          <rect
            key={`doel-${i}`}
            x={as.links + groepB * i}
            y={VLAK.marge.boven}
            width={groepB}
            height={as.hoogte - as.ondermarge - VLAK.marge.boven}
            fill="transparent"
            onPointerEnter={() => zetActief(i)}
          />
        ))}

        {punten.map((p, i) => {
          const x = as.links + groepB * i + groepB / 2;
          const label = kortAf(p.x, as.maxTekens);
          // Een afgekort label mag de volle tekst niet verzwijgen: die staat in
          // een title, voor de aanwijzer en voor de schermlezer. Een categorie
          // zonder gemeten dagen zegt daar dat er niets gemeten is, zodat de
          // ontbrekende staaf niet als een nul te lezen valt.
          const titelTekst =
            p.meetdagen === 0
              ? (geenMetingTitel?.replace("{x}", p.x) ?? null)
              : label === p.x
                ? null
                : p.x;
          const volleTekst = titelTekst ? <title>{titelTekst}</title> : null;
          return as.schuin ? (
            <text
              key={p.x}
              x={x}
              y={as.hoogte - as.ondermarge + LABELOFFSET}
              textAnchor="end"
              fontSize="10"
              fill={KLEUR.zwart}
              transform={`rotate(-${HOEK} ${x} ${as.hoogte - as.ondermarge + LABELOFFSET})`}
            >
              {volleTekst}
              {label}
            </text>
          ) : (
            <text
              key={p.x}
              x={x}
              y={as.hoogte - 8}
              textAnchor="middle"
              fontSize="10"
              fill={KLEUR.zwart}
            >
              {volleTekst}
              {label}
            </text>
          );
        })}
      </svg>

      {actief !== null && punten[actief] !== undefined ? (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+8px)] rounded-klein border border-warmgrijs bg-wit px-2.5 py-1.5 text-xs whitespace-nowrap text-zwart"
          style={{
            left: `${(actiefMidden / VLAK.breedte) * 100}%`,
            top: `${(actiefTopY / as.hoogte) * 100}%`,
          }}
        >
          <div className="font-medium">{punten[actief].x}</div>
          {data.reeksen.map((r) => {
            const p = r.punten[actief];
            if (p === undefined) return null;
            return (
              <div key={r.naam} className="tabular-nums">
                {data.reeksen.length > 1 ? (
                  <span className="font-light">{r.naam}: </span>
                ) : null}
                {p.meetdagen === 0
                  ? (geenMetingTekst ?? KASTLIJN)
                  : euroBedrag(p.y)}
                {p.meetdagen !== undefined && p.meetdagen > 0 && meetdagenTekst ? (
                  <span className="font-light">
                    {" "}
                    · {meetdagenTekst.replace("{n}", geheelGetal(p.meetdagen))}
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {data.reeksen.length >= 2 ? (
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
