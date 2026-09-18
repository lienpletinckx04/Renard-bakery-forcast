"use client";

import { useActionState, useState } from "react";

import { KASTLIJN } from "@/lib/format";
import { MAX_CRITERIA, NAAM_MAX } from "@/lib/kostenmodel";

import { maakT, type T, type Taal } from "@/lib/taal";
import { bewaarKostenmodel, type KostenUitkomst } from "./acties";

const LEEG: KostenUitkomst = {};

/**
 * De melding onder de opslaanknop. De actie stuurt een sleutel met kale
 * invulwaarden (zie acties.ts); hier wordt vertaald. Alleen de twee
 * bewaard-sleutels vragen meer dan invullen: enkelvoud of meervoud van
 * "criterium" en "groep" is presentatie, dus het formulier kiest hier de
 * woordvorm — dezelfde afweging als de groepenteller op Margebewaking.
 *
 * Twee sleutels en niet één, omdat de twee opslagroutes iets anders waarmaken:
 * lokaal is het contract na het opslaan herrekend, op de gehoste omgeving volgt
 * dat bij de volgende berekening. Zie acties.ts.
 */
function meldingTekst(uitkomst: KostenUitkomst, t: T): string {
  const sleutel = uitkomst.fout ?? uitkomst.ok;
  if (!sleutel) return "";
  if (sleutel === "kosten.bewaard" || sleutel === "kosten.bewaardDb") {
    const criteria = uitkomst.waarden?.criteria ?? "";
    const groepen = uitkomst.waarden?.groepen ?? "";
    return t(sleutel, {
      criteria: t(
        criteria === "1" ? "kosten.criteriumEnkelvoud" : "kosten.criteriumMeervoud",
        { n: criteria },
      ),
      groepen: t(
        groepen === "1" ? "kosten.groepEnkelvoud" : "kosten.groepMeervoud",
        { n: groepen },
      ),
    });
  }
  return t(sleutel, uitkomst.waarden);
}

export type KostenRegel = {
  groep: string;
  /** Aandeel in de winkelomzet, al opgemaakt ("28,9 %"). Context bij de rij. */
  aandeel: string;
  /** Huidige invoer per criteriumnaam, als invoertekst ("30,5"). */
  kosten: Record<string, string>;
  /** Brutomarge zoals het contract die nu draagt, al opgemaakt, of null. */
  marge: string | null;
};

type Criterium = {
  /** Stabiele client-sleutel; hernoemen behoudt de ingevulde cellen. */
  id: number;
  naam: string;
  omschrijving: string;
};

/**
 * Het enige formulier in het platform dat cijfers aanmaakt. De klant stelt
 * zelf het menu van kostencriteria samen — toevoegen, hernoemen, verwijderen —
 * en vult per productgroep per criterium een percentage van de omzet in. De
 * brutomarge (100 min de som) rekent de berekeningslaag na het opslaan uit;
 * dit formulier telt zelf niets op (harde regel 4).
 */
export default function KostenFormulier({
  regels,
  criteria: begin,
  criteriaBron,
  taal,
}: {
  regels: KostenRegel[];
  criteria: { naam: string; omschrijving: string }[];
  criteriaBron: "ingevuld" | "suggestie";
  taal: Taal;
}) {
  const t = maakT(taal);
  const [uitkomst, actie, bezig] = useActionState(bewaarKostenmodel, LEEG);
  const [criteria, setCriteria] = useState<Criterium[]>(
    begin.map((c, i) => ({ id: i, ...c })),
  );
  const [volgendId, setVolgendId] = useState(begin.length);
  const [nieuw, setNieuw] = useState("");

  function voegToe() {
    const naam = nieuw.trim();
    if (naam === "" || criteria.length >= MAX_CRITERIA) return;
    setCriteria([...criteria, { id: volgendId, naam, omschrijving: "" }]);
    setVolgendId(volgendId + 1);
    setNieuw("");
  }

  function verwijder(c: Criterium) {
    const zeker = window.confirm(t("inst.bevestigVerwijder", { naam: c.naam }));
    if (zeker) setCriteria(criteria.filter((x) => x.id !== c.id));
  }

  return (
    <form action={actie}>
      {criteriaBron === "suggestie" ? (
        <p className="mb-4 max-w-prose text-sm font-light text-zwart">
          {t("inst.menuVoorzet")}
        </p>
      ) : null}

      <fieldset className="max-w-2xl">
        <legend className="text-sm font-medium text-zwart">
          {t("inst.deCriteria")}
        </legend>
        <ul className="mt-3 space-y-2">
          {criteria.map((c, i) => (
            <li key={c.id} className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                name={`criterium:${c.id}:naam`}
                value={c.naam}
                maxLength={NAAM_MAX}
                aria-label={t("inst.naamVanCriterium", {
                  nummer: String(i + 1),
                })}
                onChange={(e) =>
                  setCriteria(
                    criteria.map((x) =>
                      x.id === c.id ? { ...x, naam: e.target.value } : x,
                    ),
                  )
                }
                className="w-52 rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm text-zwart outline-none focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
              />
              <input
                type="text"
                name={`criterium:${c.id}:omschrijving`}
                value={c.omschrijving}
                placeholder={t("inst.omschrijvingPlaceholder")}
                aria-label={t("inst.omschrijvingVan", {
                  naam:
                    c.naam ||
                    t("inst.criteriumNummer", { nummer: String(i + 1) }),
                })}
                onChange={(e) =>
                  setCriteria(
                    criteria.map((x) =>
                      x.id === c.id
                        ? { ...x, omschrijving: e.target.value }
                        : x,
                    ),
                  )
                }
                className="min-w-40 flex-1 rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm font-light text-zwart outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
              />
              <button
                type="button"
                onClick={() => verwijder(c)}
                className="rounded-klein border border-warmgrijs px-3 py-1.5 text-sm text-zwart hover:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
              >
                {t("inst.verwijderen")}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex items-center gap-2">
          <input
            type="text"
            value={nieuw}
            maxLength={NAAM_MAX}
            placeholder={t("inst.nieuwPlaceholder")}
            aria-label={t("inst.nieuwCriterium")}
            onChange={(e) => setNieuw(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                voegToe();
              }
            }}
            className="w-64 rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm text-zwart outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
          />
          <button
            type="button"
            onClick={voegToe}
            disabled={nieuw.trim() === "" || criteria.length >= MAX_CRITERIA}
            className="rounded-klein border border-warmgrijs px-3 py-1.5 text-sm text-zwart hover:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart disabled:opacity-50"
          >
            {t("inst.toevoegen")}
          </button>
          {criteria.length >= MAX_CRITERIA ? (
            <span className="text-sm font-light text-zwart">
              {t("inst.hoogstensCriteria", { aantal: String(MAX_CRITERIA) })}
            </span>
          ) : null}
        </div>
      </fieldset>

      {criteria.length > 0 ? (
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <caption className="sr-only">{t("inst.tabelBijschrift")}</caption>
            <thead>
              <tr className="border-b border-warmgrijs text-left">
                <th scope="col" className="py-2 pr-4 font-medium text-zwart">
                  {t("kol.productgroep")}
                </th>
                {criteria.map((c) => (
                  <th
                    scope="col"
                    key={c.id}
                    className="px-2 py-2 text-right font-medium text-zwart"
                  >
                    {c.naam || KASTLIJN}
                  </th>
                ))}
                <th scope="col" className="py-2 pl-4 text-right font-medium text-zwart">
                  {t("kol.brutomarge")}
                </th>
              </tr>
            </thead>
            <tbody>
              {regels.map((r) => (
                <tr key={r.groep} className="border-b border-beige">
                  <th scope="row" className="py-2 pr-4 text-left font-normal text-zwart">
                    {r.groep}{" "}
                    <span className="font-light">· {r.aandeel}</span>
                  </th>
                  {criteria.map((c) => (
                    <td key={c.id} className="px-2 py-1.5 text-right">
                      <input
                        type="text"
                        inputMode="decimal"
                        name={`kost:${c.id}:${encodeURIComponent(r.groep)}`}
                        defaultValue={r.kosten[c.naam] ?? ""}
                        placeholder={KASTLIJN}
                        aria-label={t("inst.celLabel", {
                          criterium: c.naam || t("inst.criterium"),
                          groep: r.groep,
                        })}
                        className="w-20 rounded-klein border border-warmgrijs bg-wit px-2 py-1 text-right text-sm text-zwart tabular-nums outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
                      />
                    </td>
                  ))}
                  {/* De marge komt uit het contract, niet uit dit formulier:
                      het scherm telt zelf niets op (harde regel 4). */}
                  <td className="py-2 pl-4 text-right tabular-nums text-zwart">
                    {r.marge ?? KASTLIJN}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 max-w-prose text-sm font-light text-zwart">
            {t("inst.allesInPct")}
          </p>
        </div>
      ) : (
        <p className="mt-6 max-w-prose text-sm font-light text-zwart">
          {t("inst.zonderCriteria")}
        </p>
      )}

      <button
        type="submit"
        disabled={bezig}
        className="mt-6 rounded-klein bg-bordeaux px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.14em] text-wit transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart disabled:opacity-50"
      >
        {bezig ? t("inst.herrekenen") : t("inst.opslaan")}
      </button>
      {/* Vaste hoogte, zodat het formulier niet verspringt bij een melding. */}
      <p
        aria-live="polite"
        className="mt-3 min-h-[1.25rem] max-w-prose text-sm font-light text-zwart"
      >
        {meldingTekst(uitkomst, t)}
      </p>
    </form>
  );
}
