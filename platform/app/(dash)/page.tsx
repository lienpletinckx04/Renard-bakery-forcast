import Link from "next/link";

import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import KaartUitklap from "@/components/KaartUitklap";
import Kerncijfer from "@/components/Kerncijfer";
import Lijngrafiek from "@/components/Lijngrafiek";
import MeerInfo from "@/components/MeerInfo";
import Microcontext from "@/components/Microcontext";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import Ontbinding from "@/components/Ontbinding";
import PaginaKop from "@/components/PaginaKop";
import PeriodePaneel from "@/components/PeriodePaneel";
import Staafgrafiek from "@/components/Staafgrafiek";
import Tabel from "@/components/Tabel";
import Toelichting from "@/components/Toelichting";
import type { OverzichtData } from "@/lib/contract";
import { aantal, euro, geheelGetal, procent } from "@/lib/format";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { maakT, type T } from "@/lib/taal";
import { reden } from "@/lib/toelichting";
import { eersteLinks } from "@/lib/uitlijning";

/**
 * Een blok dat er is, of een vak dat zegt waarom het er niet is. Nooit een
 * lege plek en nooit een nul (harde regel 8). De reden komt uit het contract;
 * de tekst hieronder is alleen het vangnet voor het geval het contract er geen
 * meelevert, en dat is dan zelf de melding.
 */
function Blok({
  titel,
  veld,
  inhoud,
  onbeschikbaar,
  children,
  t,
}: {
  titel: string;
  veld: string;
  inhoud: unknown;
  onbeschikbaar: { veld: string; reden: string }[];
  children: React.ReactNode;
  /** De vertaler van de bladzijde; alleen nodig voor het vangnet hieronder. */
  t: T;
}) {
  if (inhoud === null || inhoud === undefined) {
    return (
      <Onbeschikbaar
              t={t}
        titel={titel}
        reden={
          reden(onbeschikbaar, veld) ??
          t("leeg.blok")
        }
      />
    );
  }
  return <Kaart titel={titel}>{children}</Kaart>;
}

export const dynamic = "force-dynamic";

export default async function OverzichtPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const antwoord = await laadContract<OverzichtData>("overzicht");
  const {
    kerncijfers,
    omzetverloop,
    omzetverloop_context,
    weekdagprofiel,
    jaarvergelijking,
  } = antwoord.data;

  // `?? null`: een contract van vóór deze velden is hetzelfde geval als een
  // contract dat er bewust null in zet, en krijgt dezelfde behandeling.
  const dagtabel = antwoord.data.cfo_dagtabel ?? null;
  const bonritme = antwoord.data.bonritme ?? null;
  const weekdagmix = antwoord.data.weekdagmix ?? null;
  const maandritme = antwoord.data.maandritme ?? null;
  const afwijkende = antwoord.data.afwijkende_dagen ?? null;

  return (
    <div className="space-y-6">
      <PaginaKop
        titel={t("dag.titel")}
        ondertitel={t("dag.ondertitel")}
      />

      <Briefing briefing={antwoord.briefing} titel={t("briefing.titel")} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kerncijfers.map((c, i) => (
          <Kerncijfer key={c.label} cijfer={c} t={t} accent={i === 0} />
        ))}
      </div>

      {/* Het omzetverloop met de periodekiezer: 30 dagen, 13 weken, 12
          maanden, dit jaar. De kiezer kiest alleen welk voorgebakken venster
          uit de periodekubus getoond wordt; gerekend is er al (harde regel 4).
          Zonder periodes in het contract valt dit terug op het klassieke
          30-dagenverloop. */}
      {(antwoord.data.periodes ?? []).length > 0 ? (
        <Kaart titel={t("dag.omzetverloop")}>
          <PeriodePaneel
            label={t("algemeen.periode")}
            vensters={antwoord.data.periodes}
            meetdagenTitel={t("algemeen.meetdagenTitel")}
            geenMetingTitel={t("algemeen.geenMetingTitel")}
            geenMetingTekst={t("algemeen.geenMeting")}
            meetdagenTekst={t("algemeen.meetdagenKort")}
            bandLabel={t("algemeen.band")}
            redenen={antwoord.onbeschikbaar}
          />
        </Kaart>
      ) : (
        <Kaart titel={t("dag.omzetverloop30")}>
          <Lijngrafiek data={omzetverloop} />
          <Microcontext items={omzetverloop_context} />
        </Kaart>
      )}

      {/* De week dag per dag, in de vorm waarin de opdrachtgever zijn eigen
          weekrapport opmaakte: klanten, omzet, gemiddeld ticket. Die stond tot
          nu toe naast dit platform in plaats van erin.

          Een dag zonder bonnentelling blijft in de tabel staan met een lege
          klantenkolom. Weglaten zou lezen als een dag waarop de zaak dicht
          was, en de omzet van die dag is wél gemeten. */}
      <Blok
        t={t}
        onbeschikbaar={antwoord.onbeschikbaar}
        titel={t("dag.dagtabel")}
        veld="cfo_dagtabel"
        inhoud={dagtabel}
      >
        {dagtabel ? (
          <>
            {/* De kolommen van het weekrapport van de opdrachtgever: klanten,
                kassa, Deliveroo, totaal, gemiddeld ticket. Deliveroo is netto
                en een leeg vak is een dag ná de jongste export (onbekend, geen
                nul); de reden staat onder de tabel als to-do. */}
            <Tabel
              data={{
                kolommen: [
                  t("kol.dag"),
                  t("kol.klanten"),
                  t("kol.kassa"),
                  t("kol.deliveroo"),
                  t("kol.totaal"),
                  t("kol.gemiddeldTicket"),
                ],
                uitlijning: eersteLinks(6),
                rijen: dagtabel.rijen.map((r) => [
                  r.datum,
                  // Niet geteld is niet nul, en het woord ervoor komt uit
                  // taal.ts omdat de lezer het leest. `aantal` en niet
                  // `geheelGetal`: het klantenaantal staat als
                  // machinewaarde-string in het contract, zoals elk cijfer
                  // daar; `geheelGetal` is voor de paar velden die er als
                  // `number` in staan.
                  r.klanten === null
                    ? t("cel.nietGeteld")
                    : aantal(r.klanten),
                  euro(r.omzet),
                  r.deliveroo === null ? t("cel.nietGeteld") : euro(r.deliveroo),
                  r.totaal === null
                    ? t("cel.nietGeteld")
                    : { tekst: euro(r.totaal), vet: true },
                  r.gemiddeld_ticket === null
                    ? t("cel.nietGeteld")
                    : euro(r.gemiddeld_ticket),
                ]),
              }}
            />
            <p className="mt-3 max-w-prose text-xs font-light text-zwart">
              {dagtabel.toelichting}
            </p>
            {reden(antwoord.onbeschikbaar, "cfo_dagtabel.klanten") ? (
              <p className="mt-2 max-w-prose text-xs font-light text-zwart">
                {reden(antwoord.onbeschikbaar, "cfo_dagtabel.klanten")}
              </p>
            ) : null}
            {/* Een gat in de Deliveroo-dekking is een to-do voor de bakkerij,
                en hoort dus op te vallen: in de actiekleur, dik, met de link
                naar het scherm waar het gebeurt. */}
            {reden(antwoord.onbeschikbaar, "cfo_dagtabel.deliveroo") ? (
              <p className="mt-2 max-w-prose rounded-klein border-l-4 border-signaal-letop bg-signaal-letop-vlak py-1.5 pl-3 text-sm font-bold text-zwart">
                {reden(antwoord.onbeschikbaar, "cfo_dagtabel.deliveroo")}{" "}
                <Link href="/deliveroo" className="underline underline-offset-2">
                  {t("nav.deliveroo")}
                </Link>
              </p>
            ) : null}
            {/* De vragen die elke nieuwe lezer stelt, één keer beantwoord en
                daarna ingeklapt: waarom klanten een geheel getal is, wat het
                ticket precies deelt, waarom Deliveroo netto staat. */}
            <MeerInfo label={t("dag.waaromTitel")}>
              <p>{t("dag.waaromKlanten")}</p>
              <p>{t("dag.waaromTicket")}</p>
              <p>{t("dag.waaromDeliveroo")}</p>
            </MeerInfo>
          </>
        ) : null}
      </Blok>

      {/* De eerste vraag na "de omzet bewoog": kwamen er minder klanten, of
          kochten dezelfde klanten minder? Twee heel verschillende problemen —
          minder klanten is een deur-vraag, een kleiner mandje een
          assortiments- of prijsvraag. */}
      <Blok
        t={t}
        onbeschikbaar={antwoord.onbeschikbaar}
        titel={t("dag.waarvandaan")}
        veld="bonritme"
        inhoud={bonritme}
      >
        {bonritme ? (
          <>
            <Microcontext items={bonritme.kengetallen} />
            <p className="mt-3 max-w-prose text-xs font-light text-zwart">
              {bonritme.toelichting}
            </p>
            {bonritme.ontbinding ? (
              <div className="mt-6 border-t border-warmgrijs pt-5">
                <Ontbinding
                  data={bonritme.ontbinding}
                  meerLabel={t("algemeen.meerInfo")}
                />
              </div>
            ) : (
              <p className="mt-6 max-w-prose border-t border-warmgrijs pt-5 text-sm font-light text-zwart">
                {reden(antwoord.onbeschikbaar, "bonritme.ontbinding") ??
                  t("leeg.geenOntbinding")}
              </p>
            )}
            {/* Meta-commentaar over waarom de tweede ontbinding hier níét
                staat maar op Producten. Dat is een ontwerpverantwoording en
                geen bedrijfsfeit: wie het één keer las, hoeft het niet elke
                dag onder zijn cijfers te vinden. De verwijzing zelf blijft
                bereikbaar, want zonder haar is het scherm half. */}
            <div className="mt-4 border-t border-warmgrijs pt-3">
              <MeerInfo label={t("algemeen.meerInfo")}>
                <p>
                  {t("dag.andereHelftVoor")}{" "}
                  <Link href="/producten" className="underline underline-offset-2">
                    {t("nav.producten")}
                  </Link>
                  {t("dag.andereHelftNa")}
                </p>
              </MeerInfo>
            </div>
          </>
        ) : null}
      </Blok>

      {/* Dicht bij het laden sinds 19 aug 2026. Dit is de dichtste
          tekstconcentratie van het platform — een staafgrafiek, zeven
          aandelen en twee toelichtingen van samen ruim zeshonderd tekens —
          en een weekdagpatroon is iets wat je per kwartaal bekijkt, niet elke
          ochtend. */}
      <KaartUitklap titel={t("dag.weekdag")}>
        <Staafgrafiek
          data={weekdagprofiel.grafiek}
          meetdagenTitel={t("algemeen.meetdagenTitel")}
          geenMetingTitel={t("algemeen.geenMetingTitel")}
          geenMetingTekst={t("algemeen.geenMeting")}
          meetdagenTekst={t("algemeen.meetdagenKort")}
        />
        <p className="mt-3 max-w-prose text-xs font-light text-zwart">
          {weekdagprofiel.toelichting}
        </p>

        {/* Het aandeel hoort bij dezelfde vraag als de grafiek erboven en
            krijgt daarom geen eigen kaart. Bewust alleen het aandeel: twee
            verschillende gemiddelden voor dezelfde zaterdag naast elkaar
            zetten maakt ze allebei ongeloofwaardig. */}
        {weekdagmix ? (
          <div className="mt-6 border-t border-warmgrijs pt-5">
            <h3 className="kapitaal-label text-zwart">
              {t("dag.aandeelWeekdag")}
            </h3>
            <dl className="mt-4 flex flex-wrap gap-x-10 gap-y-3">
              {weekdagmix.rijen.map((r) => (
                <div key={r.weekdag}>
                  <dt className="kapitaal-label text-zwart">{r.weekdag}</dt>
                  <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                    <span
                      title={t("dag.weekdagMeetdagen", {
                        naam: r.naam,
                        n: geheelGetal(r.meetdagen),
                      })}
                    >
                      {procent(r.aandeel)}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 max-w-prose text-xs font-light text-zwart">
              {weekdagmix.toelichting}
            </p>
          </div>
        ) : (
          /* Geen aandeel is geen stilte: het contract legt uit waarom niet
             (veld "weekdagmix"), en die reden hoort hier en niet drie
             schermlengtes lager onder "wat hier niet staat" (audit 15 aug). */
          <p className="mt-6 max-w-prose border-t border-warmgrijs pt-5 text-sm font-light text-zwart">
            {reden(antwoord.onbeschikbaar, "weekdagmix") ??
              t("algemeen.onbeschikbaar")}
          </p>
        )}
      </KaartUitklap>

      {/* De wekentabel van vroeger is opgegaan in het 13-wekenvenster van de
          periodekiezer hierboven; het contractveld `weken` blijft bestaan
          voor consumenten zonder kiezer (de PDF). */}
      <Blok
        t={t}
        onbeschikbaar={antwoord.onbeschikbaar}
        titel={t("dag.permaand")}
        veld="maandritme"
        inhoud={maandritme}
      >
        {maandritme ? (
          <>
            <Staafgrafiek
              data={maandritme.grafiek}
              meetdagenTitel={t("algemeen.meetdagenTitel")}
              geenMetingTitel={t("algemeen.geenMetingTitel")}
              geenMetingTekst={t("algemeen.geenMeting")}
              meetdagenTekst={t("algemeen.meetdagenKort")}
            />
            {/* De grafiek blijft staan, de uitleg eronder klapt in: op dit
                scherm is het beeld het antwoord en de tekst de voetnoot. */}
            <MeerInfo label={t("algemeen.meerInfo")}>
              <p>{maandritme.toelichting}</p>
            </MeerInfo>
          </>
        ) : null}
      </Blok>

      <KaartUitklap titel={t("dag.jaaropjaar")} standaardOpen>
        <Staafgrafiek
          data={jaarvergelijking}
          meetdagenTitel={t("algemeen.meetdagenTitel")}
          geenMetingTitel={t("algemeen.geenMetingTitel")}
          geenMetingTekst={t("algemeen.geenMeting")}
          meetdagenTekst={t("algemeen.meetdagenKort")}
        />
      </KaartUitklap>

      {/* Wat er uit de band sprong. Leeg is hier een uitkomst met een reden en
          geen lege tabel: "geen uitschieters" en "te weinig waarnemingen om
          het te kunnen zeggen" zien er anders hetzelfde uit. */}
      <Blok
        t={t}
        onbeschikbaar={antwoord.onbeschikbaar}
        titel={t("dag.opvallend")}
        veld="afwijkende_dagen"
        inhoud={afwijkende}
      >
        {afwijkende ? (
          <>
            <Tabel
              data={{
                kolommen: [t("kol.dag"), t("kol.omzet"), t("kol.gebruikelijk"),
                           t("kol.verschil")],
                // Geen pijl in deze kolom: een tabelcel is platte tekst, en
                // een pijl die een schermlezer voorleest naast een bedrag dat
                // zijn teken al draagt, zegt hetzelfde twee keer.
                rijen: afwijkende.rijen.map((r) => [
                  r.label,
                  euro(r.omzet),
                  euro(r.gebruikelijk),
                  // De richting komt uit het contract en kleurt de cel als
                  // chip: een uitschieter naar boven groen, naar beneden
                  // rood. Het teken blijft in de tekst staan.
                  { tekst: euro(r.verschil), richting: r.richting },
                ]),
                uitlijning: eersteLinks(4),
              }}
            />
            <MeerInfo label={t("algemeen.meerInfo")}>
              <p>{afwijkende.toelichting}</p>
            </MeerInfo>
          </>
        ) : null}
      </Blok>

      <Toelichting titel={t("algemeen.watNietStaat")} regels={antwoord.onbeschikbaar} t={t} taal={taal} />
    </div>
  );
}
