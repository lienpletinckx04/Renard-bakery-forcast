import { cookies } from "next/headers.js";

import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import KaartUitklap from "@/components/KaartUitklap";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import Toelichting from "@/components/Toelichting";
import { COOKIE, lees } from "@/lib/auth";
import type { MargeData, StandData } from "@/lib/contract";
import { datumKort, datumMetTijd, geheelGetal, invoerWaarde, procent } from "@/lib/format";
import { huidigeTaal, laadContract, laadWinkels } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";
import { statusWoord } from "@/lib/stand";
import { laadSyncStand } from "@/lib/syncstand";
import { veldLabel } from "@/lib/toelichting";

import KostenFormulier, { type KostenRegel } from "./KostenFormulier";

export const dynamic = "force-dynamic";

/**
 * De groepen voor het kostenformulier komen uit het totaal-contract: de
 * groepen die werkelijk omzet dragen, met hun aandeel erbij, zwaarste eerst.
 * Het scherm verzint geen groepen en rekent niets (harde regel 4). Bewust het
 * totaal en niet de gekozen winkel: de kostinvoer geldt voor het hele
 * assortiment.
 */
function kostenRegels(marge: MargeData): KostenRegel[] {
  if (!("per_groep" in marge)) return [];
  return marge.per_groep.map((r) => ({
    groep: r.groep,
    aandeel: procent(r.aandeel),
    kosten: Object.fromEntries(
      r.kosten.map((k) => [k.criterium, invoerWaarde(k.pct)]),
    ),
    marge: r.marge_pct === null ? null : procent(r.marge_pct),
  }));
}

export default async function InstellingenPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const [stand, marge, winkels, sync] = await Promise.all([
    laadContract<StandData>("stand", { totaal: true }),
    laadContract<MargeData>("marge", { totaal: true }),
    laadWinkels(),
    laadSyncStand(),
  ]);

  // De rol bepaalt of het kostenformulier verschijnt. De server-actie
  // controleert hem óók (daar zit de beveiliging); dit is de eerlijke
  // voorkant. Een lezer kreeg tot 18 aug 2026 een volledig ingevuld formulier
  // met een knop die altijd weigerde — het scherm beloofde iets wat het niet
  // deed, en dat is precies wat de onbeschikbaar-staat moet voorkomen.
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  const magBewerken = sessie?.rol === "beheerder";
  const regels = kostenRegels(marge.data);
  const criteria = "criteria" in marge.data ? marge.data.criteria : [];
  const criteriaBron =
    "criteria_bron" in marge.data ? marge.data.criteria_bron : "suggestie";

  return (
    <div className="space-y-6">
      <PaginaKop
        titel={t("inst.titel")}
        ondertitel={t("inst.ondertitel")}
      />

      <Briefing briefing={stand.briefing} titel={t("briefing.titel")} />

      {/* De stand van het platform zelf: per bron en per wachter, in woorden.
          De oordelen komen kant-en-klaar uit de berekeningslaag; status is
          tekst en nooit kleur — de huisstijl kent geen betekeniskleuren. */}
      {/* De regels lijnen in kolommen uit en dragen géén proza meer: met vijf
          bronnen en zeven wachters stonden hier twaalf alinea's onder elkaar,
          en dan leest niemand er nog één. De toelichtingen staan compleet
          achter één uitklap per sectie — één per regel zou twaalf "▸"-linkjes
          opleveren en precies de drukte terugbrengen die eruit moest.

          Wat zichtbaar blijft is het signaal zelf: naam, status, meetdag en
          aantal. Een bron die hapert, ziet er dus nog steeds haperend uit
          zonder dat je iets hoeft open te klikken (harde regel 8).

          De kolommaten staan vast en zijn voor bronnen en wachters
          identiek — daardoor lijnen de statuswoorden van beide tabellen onder
          elkaar uit. Onder `sm` valt alles terug op één kolom, want vier
          kolommen op een telefoon is geen uitlijning maar een wringend
          raster. */}
      <Kaart titel={t("inst.leeft")}>
        <h3 className="text-sm font-medium text-zwart">{t("inst.bronnen")}</h3>
        <ul className="mt-3 space-y-1.5">
          {stand.data.bronnen.map((b) => (
            <li
              key={b.bron}
              className="grid grid-cols-1 items-baseline gap-x-6 gap-y-0.5 sm:grid-cols-[minmax(0,14rem)_6rem_minmax(0,13rem)_7rem]"
            >
              {/* De bronnaam is een machinesleutel ("odoo-kassa"), net als
                  de wachternamen hieronder; hij gaat door hetzelfde
                  veldLabel als zij. De sleutel zelf blijft in het
                  contract — alleen de weergave vertaalt. */}
              <span className="text-sm font-medium text-zwart">
                {veldLabel(b.bron, taal)}
              </span>
              <span className="text-sm text-zwart">
                {statusWoord(b.status, taal)}
              </span>
              <span className="text-sm font-light text-zwart">
                {/* Geen meetdag is geen streepje: de toelichting achter de
                    uitklap draagt de reden (harde regel 8). */}
                {b.laatste_meetdag !== null
                  ? t("inst.laatsteMeetdag", {
                      datum: datumKort(b.laatste_meetdag, taal),
                    })
                  : t("inst.geenMeetdag")}
              </span>
              {/* Rechts uitgelijnd en tabular-nums: alleen dan staan de
                  eenheden onder elkaar en is een rij van vijf cijfers in één
                  oogopslag te vergelijken. Zwart, zoals elk cijfer.

                  `whitespace-nowrap`: "219.503 rijen" brak op de eerste
                  schermafbeelding over twee regels en trok de hele rij uit
                  het lood. Een getal en zijn eenheid horen bij elkaar. */}
              <span className="whitespace-nowrap text-sm font-light text-zwart tabular-nums sm:text-right">
                {t("inst.rijen", { aantal: geheelGetal(b.rijen) })}
              </span>
            </li>
          ))}
        </ul>
        <MeerInfo label={t("inst.toelichting")}>
          <dl className="space-y-2">
            {stand.data.bronnen.map((b) => (
              <div key={b.bron}>
                <dt className="text-sm font-medium text-zwart">
                  {veldLabel(b.bron, taal)}
                </dt>
                <dd className="text-sm font-light text-zwart">
                  {b.toelichting}
                </dd>
              </div>
            ))}
          </dl>
        </MeerInfo>

        <h3 className="mt-6 border-t border-warmgrijs pt-4 text-sm font-medium text-zwart">
          {t("inst.wachters")}
        </h3>
        <ul className="mt-3 space-y-1.5">
          {stand.data.wachters.map((w) => (
            <li
              key={w.naam}
              className="grid grid-cols-1 items-baseline gap-x-6 gap-y-0.5 sm:grid-cols-[minmax(0,14rem)_6rem_minmax(0,13rem)_7rem]"
            >
              {/* De naam van een wachter is een machinesleutel
                  ("gat_in_de_reeks"); op het scherm staat Nederlands (O12).
                  Een wachter die er later bijkomt, wordt door het vangnet in
                  veldLabel leesbaar gemaakt en niet ruw doorgelaten. */}
              <span className="text-sm font-medium text-zwart">
                {veldLabel(w.naam, taal)}
              </span>
              <span className="text-sm text-zwart">
                {statusWoord(w.uitkomst, taal)}
              </span>
            </li>
          ))}
        </ul>
        <MeerInfo label={t("inst.toelichting")}>
          <dl className="space-y-2">
            {stand.data.wachters.map((w) => (
              <div key={w.naam}>
                <dt className="text-sm font-medium text-zwart">
                  {veldLabel(w.naam, taal)}
                </dt>
                <dd className="text-sm font-light text-zwart">
                  {w.toelichting}
                </dd>
              </div>
            ))}
          </dl>
        </MeerInfo>

        {/* De dodemansknop, en als enige blok op dit scherm niet uit het
            contract. De reden staat in lib/syncstand.ts: het contract wordt
            gebouwd dóór de sync, dus een oordeel over de sync dat in het
            contract staat, bevriest op "loopt nu". Dit wordt gelezen op het
            moment dat je kijkt.

            Op de bestandsroute is `sync` null en staat hier niets: dan is er
            geen nachtelijke synchronisatie om over te waken, en een leeg vak
            met een reden zou een probleem suggereren dat niet bestaat. */}
        {sync ? (
          <div className="mt-6 border-t border-warmgrijs pt-4">
            {/* Dezelfde kolommaten als de bronnen en de wachters hierboven, en
                om dezelfde reden: dan staat dit statuswoord onder de andere
                statuswoorden. Wat hier NIET in de eerste kolom past is de zin
                eronder — die is proza en geen label, en geperst in 14rem brak
                hij over vier regels naast een leeg vlak. */}
            <div className="grid grid-cols-1 items-baseline gap-x-6 gap-y-0.5 sm:grid-cols-[minmax(0,14rem)_6rem]">
              <span className="text-sm font-medium text-zwart">
                {t("sync.titel")}
              </span>
              <span className="text-sm text-zwart">
                {statusWoord(sync.oordeel, taal)}
              </span>
            </div>
            <p className="mt-1.5 text-sm font-light text-zwart">
              {t(`sync.${sync.geval}`, {
                moment:
                  sync.geslaagd_gestart_op !== null
                    ? datumMetTijd(sync.geslaagd_gestart_op, taal)
                    : t("sync.geenGeslaagde"),
              })}
              {/* De melding komt uit etl_run en draagt per afspraak geen data
                  (migratie 003) — alleen het type en de tekst van de fout. */}
              {sync.laatste_melding ? (
                <> {t("sync.melding", { tekst: sync.laatste_melding })}</>
              ) : null}
            </p>
          </div>
        ) : null}
      </Kaart>

      {/* Het formulier staat er op beide routes. Tot 18 aug 2026 (avond) stond
          hier onder CONTRACT_BRON=db een onbeschikbaar-vak: het formulier kon
          alleen een lokaal bestand schrijven, en dat leest op de gehoste
          omgeving niemand. Sinds migratie 009 schrijft de server-actie daar naar
          kosten_criterium/kosten_waarde, dus de reden is vervallen — en een
          onbeschikbaar-melding die niet meer waar is, is precies zo misleidend
          als de opslag die ze verving. Wat er wél anders is op die route, zegt
          het formulier bij het opslaan: de cijfers volgen bij de volgende
          berekening.

          `data-buiten-rapport`: het kostenmodel is een invoerhandeling van de
          beheerder. Het hoort op dit scherm en niet in het CFO-rapport, waar
          het een dood invulveld op papier zou zijn. Wat de invoer oplevert,
          staat wél in het rapport — op het margescherm. */}
      <div data-buiten-rapport>
      {!magBewerken ? (
        <Onbeschikbaar
          t={t}
          titel={t("inst.kostenmodel")}
          reden={t("inst.kostenAlleenBeheerder")}
        />
      ) : (
        /* Dicht sinds 19 aug 2026. Het kostenmodel is een invoerhandeling die
           een beheerder een paar keer per jaar doet, en het draagt negentien
           rijen invoervelden plus de volledige methodetekst. Instellingen is
           het scherm waar je ook komt om de synchronisatiestand te lezen, en
           die stond onder een formulier van twee schermlengtes. */
        <KaartUitklap titel={t("inst.kostenmodel")}>
          {/* De methodetekst stond hier tot 18 aug 2026 open boven het
              formulier: vier alinea's vóór het eerste invulveld, waarvan er
              drie al achter een uitklap zaten. Nu zit de hele uitleg achter
              dezelfde uitklap, in leesorde, en begint de kaart bij het
              formulier — waar de beheerder voor kwam. Het rekenvoorschrift
              (brutomarge = 100 − som) staat bovenaan die uitleg, en het
              formulier laat dezelfde som live zien. */}
          <MeerInfo label={t("inst.hoewerkt")}>
            <p>{t("inst.kostenVoedt")}</p>
            <p>{t("inst.uitlegCriterium")}</p>
            <p>{t("inst.uitlegReferentie")}</p>
            <p>{t("inst.uitlegNaOpslaan")}</p>
          </MeerInfo>
          <div className="mt-4">
            {regels.length > 0 ? (
              <KostenFormulier
                regels={regels}
                criteria={criteria}
                criteriaBron={criteriaBron}
                taal={taal}
              />
            ) : (
              <p className="max-w-prose text-sm font-light text-zwart">
                {t("inst.geenGroepen")}
              </p>
            )}
          </div>
        </KaartUitklap>
      )}
      </div>

      <Kaart titel={t("inst.winkels")}>
        {winkels.winkels.length > 0 ? (
          <>
            <ul className="max-w-prose space-y-1">
              {winkels.winkels.map((w) => (
                <li key={w.slug} className="text-sm text-zwart">
                  {w.naam}
                </li>
              ))}
            </ul>
            {winkels.niet_toegewezen.length > 0 ? (
              <p className="mt-3 max-w-prose text-sm font-light text-zwart">
                {t("inst.nietToegewezen", {
                  filialen: winkels.niet_toegewezen.join(", "),
                })}{" "}
                <code className="text-xs">config/winkels.json</code>.
              </p>
            ) : null}
            {/* Een winkel uit de config zonder schermen verscheen tot 17 aug
                nergens: niet in de kiezer, niet hier. De reden lag nochtans
                klaar in de bouwuitvoer (audit 15 aug). */}
            {winkels.overgeslagen.map((w) => (
              <p
                key={w.naam}
                className="mt-3 max-w-prose text-sm font-light text-zwart"
              >
                {t("inst.winkelOvergeslagen", { naam: w.naam })} {w.reden}
              </p>
            ))}
          </>
        ) : (
          <>
            {/* De stand blijft staan, het vooruitzicht klapt in. Een genegeerd
                winkelbestand is géén vooruitzicht maar een afwijking die nú
                geldt, en die hoort dus zichtbaar te blijven — hij verdient
                dezelfde behandeling als een haperende bron. */}
            <p className="max-w-prose text-sm font-light text-zwart">
              {t("inst.eenGeheel")}
              {winkels.melding
                ? t("inst.winkelbestandGenegeerd", { melding: winkels.melding })
                : null}
            </p>
            {winkels.melding ? null : (
              <MeerInfo label={t("inst.hoewerkt")}>
                <p>{t("inst.winkelsLater")}</p>
              </MeerInfo>
            )}
          </>
        )}
      </Kaart>

      {/* `data-buiten-rapport`: wie er toegang heeft is beheer, geen cijfer over
          de bakkerij. Zie het kostenmodel hierboven. */}
      <div data-buiten-rapport>
        {/* Dit stond tot 18 aug 2026 als een gewone kaart met één lange alinea,
            terwijl het commentaar erboven zélf al zei dat het "eerlijk
            onbeschikbaar" is. Nu is het dat ook echt: hetzelfde vak als elk
            ander ontbrekend onderdeel, dus met "Nog niet beschikbaar" in beeld
            en de weg-eromheen achter de uitklap. Eén patroon voor één
            toestand. */}
        <Onbeschikbaar
          t={t}
          titel={t("inst.gebruikers")}
          reden={t("inst.gebruikersLater")}
        />
      </div>

      <Toelichting titel={t("algemeen.watNietStaat")} regels={stand.onbeschikbaar} t={t} taal={taal} />
    </div>
  );
}
