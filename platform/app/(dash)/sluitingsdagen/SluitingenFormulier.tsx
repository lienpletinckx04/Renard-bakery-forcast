"use client";

import { useActionState, useState } from "react";

import { REDEN_MAX } from "@/lib/sluitingsdagen";
import { maakT, type Sleutel, type T, type Taal } from "@/lib/taal";
import { bewaarSluitingen, type SluitingenUitkomst } from "./acties";

const LEEG: SluitingenUitkomst = {};

/** De drie toestanden van een kandidaat, in de volgorde van het scherm. */
const TOESTANDEN = ["open", "dicht", "onbekend"] as const;
type Toestand = (typeof TOESTANDEN)[number];

/** Knoptekst per toestand; onbekend toont het vraagteken, het woord staat in
 * het aria-label. */
const KNOP: Record<Toestand, Sleutel> = {
  open: "sluit.open",
  dicht: "sluit.dicht",
  onbekend: "sluit.onbekendKnop",
};

const WOORD: Record<Toestand, Sleutel> = {
  open: "sluit.open",
  dicht: "sluit.dicht",
  onbekend: "sluit.onbekend",
};

/** De zeven weekdagen, 0 = maandag zoals overal in dit project. */
const WEEKDAGEN: Sleutel[] = [
  "sluit.wd0",
  "sluit.wd1",
  "sluit.wd2",
  "sluit.wd3",
  "sluit.wd4",
  "sluit.wd5",
  "sluit.wd6",
];

function meldingTekst(uitkomst: SluitingenUitkomst, t: T): string {
  const sleutel = uitkomst.fout ?? uitkomst.ok;
  if (!sleutel) return "";
  return t(sleutel, uitkomst.waarden);
}

export type Kandidaat = {
  /** ISO-datum, tevens de formuliersleutel. */
  datum: string;
  /** "vr 25 december 2026", uit het contract, al vertaald. */
  datumTekst: string;
  naam: string;
  toestand: Toestand;
};

export type PeriodeInvoer = { van: string; tot: string; reden: string };

export type RegelInvoer = { weekdag: number; vanaf: string; tot: string };

export type OverigeRij = {
  van: string;
  tot: string;
  toestand: "open" | "dicht";
  reden: string;
};

const invoerKlasse =
  "rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm text-zwart outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart";

/**
 * De bevestigingslijst van de sluitingskalender. Geen leeg invoerscherm maar
 * de feestdagen van de komende twaalf maanden met per dag één vraag: open of
 * dicht? Plus de eigen periodes en de vaste wekelijkse sluitingsdag. Het
 * formulier rekent niets (harde regel 4): elke uitkomst van deze invoer —
 * welke dagen de prognose overslaat, welk voorbehoud verdwijnt — komt uit de
 * berekeningslaag, bij de eerstvolgende nachtelijke herrekening.
 *
 * Zonder `magBewerken` wordt dezelfde stand getoond als woorden in plaats
 * van knoppen: de kalender is ook voor een lezer informatie.
 */
export default function SluitingenFormulier({
  kandidaten,
  periodes: beginPeriodes,
  regel,
  overige,
  magBewerken,
  taal,
}: {
  kandidaten: Kandidaat[];
  periodes: PeriodeInvoer[];
  regel: RegelInvoer | null;
  overige: OverigeRij[];
  magBewerken: boolean;
  taal: Taal;
}) {
  const t = maakT(taal);
  const [uitkomst, actie, bezig] = useActionState(bewaarSluitingen, LEEG);
  const [periodes, setPeriodes] = useState<(PeriodeInvoer & { id: number })[]>(
    beginPeriodes.map((p, i) => ({ id: i, ...p })),
  );
  const [volgendId, setVolgendId] = useState(beginPeriodes.length);

  function voegPeriodeToe() {
    setPeriodes([...periodes, { id: volgendId, van: "", tot: "", reden: "" }]);
    setVolgendId(volgendId + 1);
  }

  function verwijderPeriode(id: number) {
    setPeriodes(periodes.filter((p) => p.id !== id));
  }

  const feestdagen = (
    <table className="w-full min-w-[30rem] text-sm">
      <caption className="sr-only">{t("sluit.feestdagen")}</caption>
      <thead>
        <tr className="border-b border-warmgrijs text-left">
          <th scope="col" className="py-2 pr-4 font-medium text-zwart">
            {t("kol.dag")}
          </th>
          <th scope="col" className="py-2 pr-4 font-medium text-zwart">
            {t("kol.feestdag")}
          </th>
          <th scope="col" className="py-2 font-medium text-zwart">
            {t("kol.toestand")}
          </th>
        </tr>
      </thead>
      <tbody>
        {kandidaten.map((k) => (
          <tr key={k.datum} className="border-b border-beige">
            <th
              scope="row"
              className="py-2 pr-4 text-left font-normal text-zwart"
            >
              {k.datumTekst}
            </th>
            <td className="py-2 pr-4 font-light text-zwart">{k.naam}</td>
            <td className="py-1.5">
              {magBewerken ? (
                <span
                  role="radiogroup"
                  aria-label={t("sluit.toestandVan", { datum: k.datumTekst })}
                  className="inline-flex gap-1"
                >
                  {TOESTANDEN.map((w) => (
                    <label key={w}>
                      <input
                        type="radio"
                        name={`toestand:${k.datum}`}
                        value={w}
                        defaultChecked={k.toestand === w}
                        aria-label={t(WOORD[w])}
                        className="peer sr-only"
                      />
                      <span className="inline-block cursor-pointer rounded-klein border border-warmgrijs px-3 py-1 text-sm text-zwart peer-checked:border-zwart peer-checked:bg-beige peer-checked:font-semibold peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-zwart">
                        {t(KNOP[w])}
                      </span>
                    </label>
                  ))}
                </span>
              ) : (
                <span
                  className={
                    k.toestand === "onbekend"
                      ? "font-light text-zwart"
                      : "font-medium text-zwart"
                  }
                >
                  {t(WOORD[k.toestand])}
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const periodeBlok = (
    <fieldset className="mt-8 max-w-2xl">
      <legend className="text-sm font-medium text-zwart">
        {t("sluit.periodes")}
      </legend>
      <p className="mt-1 max-w-prose text-sm font-light text-zwart">
        {t("sluit.periodesUitleg")}
      </p>
      {magBewerken ? (
        <>
          <ul className="mt-3 space-y-2">
            {periodes.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-1.5 text-sm font-light text-zwart">
                  {t("sluit.van")}
                  <input
                    type="date"
                    name={`periode:${p.id}:van`}
                    defaultValue={p.van}
                    className={invoerKlasse}
                  />
                </label>
                <label className="flex items-center gap-1.5 text-sm font-light text-zwart">
                  {t("sluit.tot")}
                  <input
                    type="date"
                    name={`periode:${p.id}:tot`}
                    defaultValue={p.tot === p.van ? "" : p.tot}
                    className={invoerKlasse}
                  />
                </label>
                <input
                  type="text"
                  name={`periode:${p.id}:reden`}
                  defaultValue={p.reden}
                  maxLength={REDEN_MAX}
                  placeholder={t("sluit.redenVoorbeeld")}
                  aria-label={t("sluit.reden")}
                  className={`min-w-40 flex-1 ${invoerKlasse} font-light`}
                />
                <button
                  type="button"
                  onClick={() => verwijderPeriode(p.id)}
                  aria-label={t("sluit.verwijderPeriode", {
                    van: p.van || t("sluit.reden"),
                  })}
                  className="rounded-klein border border-warmgrijs px-3 py-1.5 text-sm text-zwart hover:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
                >
                  {t("sluit.verwijder")}
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={voegPeriodeToe}
            className="mt-3 rounded-klein border border-warmgrijs px-3 py-1.5 text-sm text-zwart hover:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
          >
            {t("sluit.periodeToevoegen")}
          </button>
        </>
      ) : (
        <ul className="mt-3 space-y-1">
          {periodes.length === 0 ? (
            <li className="text-sm font-light text-zwart">
              {t("sluit.onbekend")}
            </li>
          ) : (
            periodes.map((p) => (
              <li key={p.id} className="text-sm text-zwart">
                {p.van}
                {p.tot !== p.van ? ` – ${p.tot}` : ""}
                {p.reden !== "" ? (
                  <span className="font-light"> · {p.reden}</span>
                ) : null}
              </li>
            ))
          )}
        </ul>
      )}
    </fieldset>
  );

  const regelBlok = (
    <fieldset className="mt-8 max-w-2xl">
      <legend className="text-sm font-medium text-zwart">
        {t("sluit.regel")}
      </legend>
      <p className="mt-1 max-w-prose text-sm font-light text-zwart">
        {t("sluit.regelUitleg")}
      </p>
      {magBewerken ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm font-light text-zwart">
            {t("sluit.weekdagLabel")}
            <select
              name="regel:weekdag"
              defaultValue={regel === null ? "" : String(regel.weekdag)}
              className={invoerKlasse}
            >
              <option value="">{t("sluit.geenRegel")}</option>
              {WEEKDAGEN.map((sleutel, i) => (
                <option key={sleutel} value={String(i)}>
                  {t(sleutel)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-sm font-light text-zwart">
            {t("sluit.vanafLabel")}
            <input
              type="date"
              name="regel:vanaf"
              defaultValue={regel?.vanaf ?? ""}
              className={invoerKlasse}
            />
          </label>
          <label className="flex items-center gap-1.5 text-sm font-light text-zwart">
            {t("sluit.totLabel")}
            <input
              type="date"
              name="regel:tot"
              defaultValue={regel?.tot ?? ""}
              className={invoerKlasse}
            />
          </label>
        </div>
      ) : (
        <p className="mt-3 text-sm text-zwart">
          {regel === null
            ? t("sluit.geenRegel")
            : `${t(WEEKDAGEN[regel.weekdag])} · ${t("sluit.vanafLabel")} ${regel.vanaf}${regel.tot !== "" ? ` · ${t("sluit.tot")} ${regel.tot}` : ""}`}
        </p>
      )}
    </fieldset>
  );

  const overigeBlok =
    overige.length === 0 ? null : (
      <div className="mt-8 max-w-2xl">
        <h3 className="text-sm font-medium text-zwart">
          {t("sluit.bewaardeInvoer")}
        </h3>
        <p className="mt-1 max-w-prose text-sm font-light text-zwart">
          {t("sluit.bewaardeInvoerUitleg")}
        </p>
        <ul className="mt-3 space-y-1">
          {overige.map((rij) => (
            <li key={rij.van} className="text-sm text-zwart">
              {rij.van}
              {rij.tot !== rij.van ? ` – ${rij.tot}` : ""} ·{" "}
              {t(WOORD[rij.toestand])}
              {rij.reden !== "" ? (
                <span className="font-light"> · {rij.reden}</span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    );

  const inhoud = (
    <>
      <h3 className="kapitaal-label mb-3">{t("sluit.feestdagen")}</h3>
      <div className="overflow-x-auto">{feestdagen}</div>
      {periodeBlok}
      {regelBlok}
      {overigeBlok}
    </>
  );

  if (!magBewerken) {
    return <div>{inhoud}</div>;
  }

  return (
    <form action={actie}>
      {inhoud}
      <button
        type="submit"
        disabled={bezig}
        className="mt-6 rounded-klein bg-bordeaux px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.14em] text-wit transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart disabled:opacity-50"
      >
        {bezig ? t("sluit.opslaanBezig") : t("sluit.opslaan")}
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
