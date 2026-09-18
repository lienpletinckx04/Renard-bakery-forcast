import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import KaartUitklap from "@/components/KaartUitklap";
import Lijngrafiek from "@/components/Lijngrafiek";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import Tabel from "@/components/Tabel";
import Toelichting from "@/components/Toelichting";
import type { PrognoseData } from "@/lib/contract";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";
import { datumKort, euro, factor, geheelGetal, procent } from "@/lib/format";
import { reden, verdeelPrognoseRegels } from "@/lib/toelichting";
import { eersteLinks, uitlijning } from "@/lib/uitlijning";

/**
 * Het aantal dagen op dit scherm staat nergens hardgecodeerd. Het venster slaat
 * dagen over waarop de winkel volgens de kalender dicht is, dus "zeven" is niet
 * gegarandeerd waar; elk aantal in de tekst komt uit het contract of uit de
 * lengte van de reeks zelf.
 */
export const dynamic = "force-dynamic";

export default async function PrognosePagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const antwoord = await laadContract<PrognoseData>("prognose");
  // `?? []` en geen kale destructurering: `data` is een leeg object wanneer de
  // contractbouw bewust géén prognose levert -- te weinig historiek voor een
  // backtest (harde regel 7), of een winkel met te weinig gemeten dagen. Dat is
  // de eerlijke tak, en hij hoort te eindigen in het onbeschikbaar-vak verderop.
  // Tot 18 aug 2026 las regel 37 hieronder `dagen.length` achttien regels vóór
  // die guard, en dan werd de nette weigering een 500 op het scherm.
  const dagen = antwoord.data.dagen ?? [];
  const { weektotaal, weektotaal_dagen, grafiek } = antwoord.data;
  // `?? null`: een contract van vóór het trackrecord-veld is hetzelfde geval
  // als een contract dat er bewust null in zet, en krijgt dezelfde behandeling.
  const trackrecord = antwoord.data.trackrecord ?? null;
  const categorieen = antwoord.data.categorieen ?? null;
  const modelkaart = antwoord.data.modelkaart ?? null;
  const regels = verdeelPrognoseRegels(antwoord.onbeschikbaar);

  // Ontbreekt weektotaal_dagen (een contract van vóór dat veld), dan is de
  // lengte van de reeks het enige aantal dat er met zekerheid is.
  const somDagen = weektotaal_dagen ?? dagen.length;

  // Kop én briefing samen, want ze horen in allebei de takken hieronder: juist
  // als er géén prognose staat, wil een lezer weten waarom.
  const kop = (
    <>
      <PaginaKop
        titel={t("prog.titel")}
        ondertitel={
          dagen.length > 0
            ? t("prog.ondertitelMet", { n: geheelGetal(dagen.length) })
            : t("prog.ondertitelZonder")
        }
      />
      <Briefing briefing={antwoord.briefing} titel={t("briefing.titel")} />
    </>
  );

  // Geen dagen betekent geen prognose. Dat wordt een onbeschikbaar-vak met de
  // reden erbij, en nooit een leeg tekenvlak of een nul (harde regel 8).
  if (dagen.length === 0) {
    return (
      <div className="space-y-6">
        {kop}
        <Onbeschikbaar
              t={t}
          titel={t("prog.titel")}
          reden={
            reden(antwoord.onbeschikbaar, "prognose") ??
            reden(antwoord.onbeschikbaar, "prognose.dagen") ??
            t("leeg.prognosedagen")
          }
        />
        <Toelichting titel={t("algemeen.watNietStaat")} regels={antwoord.onbeschikbaar} t={t} taal={taal} />
      </div>
    );
  }

  // De opbouwkolom staat er alleen wanneer het contract haar levert. De
  // tekst is samengesteld uit machinewaarden die de berekeningslaag per test
  // gelijk houdt aan de voorspelling zelf: uitleg, geen tweede model.
  const heeftOpbouw = dagen.some((d) => d.opbouw);
  const opbouwTekst = (d: (typeof dagen)[number]): string =>
    d.opbouw
      ? `${euro(d.opbouw.basis)} ${factor(d.opbouw.niveau)}${
          d.opbouw.kalenderfactor
            ? ` ${factor(d.opbouw.kalenderfactor)} (${d.opbouw.kenmerk})`
            : ""
        }`
      : "";

  const tabel = {
    kolommen: [
      t("kol.dag"),
      t("kol.verwachteOmzet"),
      t("kol.ondergrens"),
      t("kol.bovengrens"),
      ...(heeftOpbouw ? [t("prog.opbouwKolom")] : []),
    ],
    rijen: dagen.map((d) => [
      datumKort(d.datum, taal),
      euro(d.verwacht),
      euro(d.onder),
      euro(d.boven),
      ...(heeftOpbouw ? [opbouwTekst(d)] : []),
    ]),
    uitlijning: heeftOpbouw
      ? uitlijning("links", "rechts", "rechts", "rechts", "links")
      : eersteLinks(4),
  };

  return (
    <div className="space-y-6">
      {kop}

      {/* Het totaal staat er, of het staat er niet met de reden erbij. Een
          leeg contractveld wordt nooit een nul en nooit een streepje. */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        {weektotaal ? (
          /* `kerncijfer kerncijfer-accent`: dit is het tweede vaste bordeaux
             vlak van de huisstijl, met de hand gezet en niet via Kerncijfer.
             Zonder deze haakjes zou het op papier een wit cijfer op wit blijven
             — zie de afdruksectie in globals.css. */
          <div className="kerncijfer kerncijfer-accent rounded-klein bg-bordeaux p-6 sm:w-72 sm:shrink-0">
            <div className="kapitaal-label text-beige">{t("prog.verwachtTotaal")}</div>
            <div className="mt-2 text-3xl font-semibold text-wit tabular-nums xl:text-4xl">
              {euro(weektotaal)}
            </div>
            {/* Label op een bordeaux vlak staat in beige, niet in wit: alleen
                het cijfer zelf draagt wit (huisstijl-verfijning 12 aug). */}
            <div className="mt-1 text-sm font-light text-beige">
              {t("prog.somVan", { n: geheelGetal(somDagen) })}
            </div>
          </div>
        ) : (
          <div className="sm:w-72 sm:shrink-0">
            <Onbeschikbaar
              t={t}
              titel={t("prog.verwachtTotaal")}
              reden={
                reden(antwoord.onbeschikbaar, "prognose.weektotaal") ??
                t("leeg.totaal")
              }
            />
          </div>
        )}

        {/* Het voorbehoud bij het meest prominente cijfer staat ernaast, niet
            drie schermlengtes lager. */}
        {weektotaal && regels.tegel.length > 0 ? (
          <div className="max-w-prose space-y-2">
            {regels.tegel.map((r) => (
              <p key={r.veld} className="text-xs font-light text-zwart">
                {r.reden}
              </p>
            ))}
          </div>
        ) : null}
      </div>

      <Kaart
        titel={t("prog.dagomzetTitel", { n: geheelGetal(dagen.length) })}
      >
        <Lijngrafiek data={grafiek} bandLabel={t("algemeen.band")} />
      </Kaart>

      {/* Hoe dit scherm gelezen moet worden: methode en gemeten
          nauwkeurigheid uit de backtest, en waar de reeks begint. Sinds de
          audit van 14 aug ná het cijfer en de grafiek — eerst het inzicht,
          dan de leesinstructie — maar onverkort zichtbaar. */}
      <Toelichting
        titel={t("prog.hoelezen")}
        regels={regels.kop}
        t={t}
        taal={taal}
      />

      {/* Welke hoek van het assortiment draagt de verwachte week? Elke
          categorie met haar eigen gemeten afwijking, uitklapbaar tot op de
          dag. De blokken tellen bewust niet op tot het weektotaal; de
          toelichting uit het contract zegt waarom. */}
      {categorieen && categorieen.blokken.length > 0 ? (
        <KaartUitklap
          titel={t("prog.percategorie")}
          samenvatting={t("prog.categorieenInVenster", {
            n: geheelGetal(categorieen.blokken.length),
          })}
        >
          <ul>
            {categorieen.blokken.map((c) => (
              <li key={c.categorie} className="border-b border-warmgrijs">
                <details className="group">
                  {/* `uitklap-kop`: afdrukhaakje. Deze regel draagt de
                      categorienaam, het aandeel, de gemeten afwijking en het
                      weektotaal van de categorie — en geen ervan staat in de
                      dagtabel eronder. Zonder de klasse verbergt de
                      afdrukregel haar en stonden er in de PDF zeven naamloze
                      dagtabellen zonder verantwoording (19 aug 2026). */}
                  <summary className="uitklap-kop flex cursor-pointer list-none flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5 [&::-webkit-details-marker]:hidden">
                    <span className="text-sm text-zwart">
                      <span
                        aria-hidden="true"
                        className="mr-2 inline-block transition-transform group-open:rotate-90"
                      >
                        ›
                      </span>
                      {c.categorie}
                      <span className="font-light">
                        {" "}
                        ·{" "}
                        {t("prog.categorieMeta", {
                          aandeel: procent(c.aandeel),
                          wape: procent(c.wape),
                        })}
                      </span>
                    </span>
                    <span className="text-sm font-medium text-zwart tabular-nums">
                      {euro(c.weektotaal)}
                    </span>
                  </summary>
                  <div className="pb-3 pl-6">
                    <Tabel
                      data={{
                        kolommen: [t("kol.dag"), t("kol.verwacht"), t("kol.onder"),
                                     t("kol.boven")],
                        rijen: c.dagen.map((d) => [
                          datumKort(d.datum, taal),
                          euro(d.verwacht),
                          euro(d.onder),
                          euro(d.boven),
                        ]),
                        uitlijning: eersteLinks(4),
                      }}
                    />
                  </div>
                </details>
              </li>
            ))}
          </ul>
          <p className="mt-3 max-w-prose text-xs font-light text-zwart">
            {categorieen.toelichting}
          </p>
        </KaartUitklap>
      ) : null}

      <KaartUitklap
        titel={t("prog.perdag")}
        samenvatting={t("prog.dagenInVenster", { n: geheelGetal(dagen.length) })}
      >
        <Tabel data={tabel} />
        {regels.dagen.length > 0 ? (
          <div className="mt-4 max-w-prose space-y-2 border-t border-warmgrijs pt-4">
            {regels.dagen.map((r) => (
              <p key={r.veld} className="text-xs font-light text-zwart">
                {r.reden}
              </p>
            ))}
          </div>
        ) : null}
      </KaartUitklap>

      {/* Het trackrecord is de verantwoording van alles hierboven (harde
          regel 7): wat het model voorspelde tegenover wat er gemeten is.
          Zonder trackrecord blijft het vak staan en zegt het waarom. */}
      {trackrecord ? (
        <KaartUitklap titel={t("prog.hoegoed")} standaardOpen>
          <Lijngrafiek data={trackrecord.grafiek} />
          <dl className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-warmgrijs pt-4">
            <div>
              <dt className="kapitaal-label text-zwart">{t("prog.gemetenDagen")}</dt>
              <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                {geheelGetal(trackrecord.dagen)}
              </dd>
            </div>
            <div>
              <dt className="kapitaal-label text-zwart">{t("algemeen.periode")}</dt>
              <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                {datumKort(trackrecord.van, taal)} – {datumKort(trackrecord.tot, taal)}
              </dd>
            </div>
            <div>
              <dt className="kapitaal-label text-zwart">{t("prog.gemAfwijking")}</dt>
              <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                {/* Geen afwijking is geen nul: dan staat er dat ze ontbreekt. */}
                {trackrecord.wape !== null
                  ? procent(trackrecord.wape)
                  : t("algemeen.nietMeegeleverd")}
              </dd>
            </div>
          </dl>
        </KaartUitklap>
      ) : (
        <Onbeschikbaar
              t={t}
          titel={t("prog.hoegoed")}
          reden={
            reden(antwoord.onbeschikbaar, "prognose.trackrecord") ??
            t("leeg.trackrecord")
          }
        />
      )}

      {/* De modelkaart: de verantwoording van het model in één blok, alles
          gemeten door de berekeningslaag en hier alleen weergegeven. Zonder
          modelkaart (ouder contract) verschijnt er niets — de teksten in de
          toelichting hierboven blijven dan de enige verantwoording.

          Dicht geklapt, en zónder cijfer in de kop. Dat laatste is een
          correctie op de eerste versie van 19 aug 2026: daar stond
          `trackrecord.wape` naast de titel — 8,1 %, de afwijking over de
          laatste 28 dagen — terwijl de kaart eronder 7,8 % noemt, de afwijking
          over de hele backtest. Twee verschillende metingen onder één label, en
          de dichtgeklapte kaart liet juist de verkeerde zien. Een rij uit
          `modelkaart.rijen` pakken kan niet: die labels komen vertaald uit het
          contract, en op een label zoeken is raden.

          Verantwoord blijft het: het trackrecord hierboven staat open en toont
          de gemeten afwijking voluit. Deze kaart is de verdieping daarvan.
          Harde regel 7 vraagt dat de meting op het scherm staat, niet dat ze er
          twee keer staat. */}
      {modelkaart ? (
        <KaartUitklap titel={t("prog.modelkaart")}>
          <dl className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
            {modelkaart.rijen.map((r) => (
              <div key={r.label}>
                <dt className="kapitaal-label text-zwart">{r.label}</dt>
                <dd className="mt-0.5 text-sm font-light text-zwart">
                  {r.waarde}
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-5 max-w-prose border-t border-warmgrijs pt-4 text-xs font-light text-zwart">
            {modelkaart.toelichting}
          </p>
        </KaartUitklap>
      ) : null}

      <Toelichting titel={t("algemeen.watNietStaat")} regels={regels.overig} t={t} taal={taal} />
    </div>
  );
}
