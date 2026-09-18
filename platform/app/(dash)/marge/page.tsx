import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import KaartUitklap from "@/components/KaartUitklap";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import Staafgrafiek from "@/components/Staafgrafiek";
import Tabel from "@/components/Tabel";
import Toelichting from "@/components/Toelichting";
import type { MargeData, MargeKostRegel } from "@/lib/contract";
import { euro, geheelGetal, KASTLIJN, procent } from "@/lib/format";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";
import { reden } from "@/lib/toelichting";
import { eersteLinks, uitlijning } from "@/lib/uitlijning";

export const dynamic = "force-dynamic";

/** "Grondstoffen 30 % · Verlies 5 %" — compact, alleen weergave, geen
 * rekenwerk. De leeg-tekst komt uit het woordenboek, want deze functie kent
 * de taal van de lezer niet. */
function opbouwTekst(kosten: MargeKostRegel[], leeg: string): string {
  if (kosten.length === 0) return leeg;
  return kosten.map((k) => `${k.criterium} ${procent(k.pct)}`).join(" · ");
}

/**
 * Margebewaking. Zonder ingevulde kosten staat hier de onbeschikbaar-toestand
 * met de reden; zodra een beheerder op Instellingen het kostenmodel invult,
 * rekent de berekeningslaag en toont dit scherm het resultaat. Alles komt
 * kant-en-klaar uit het contract; hier wordt niets opgeteld of gewogen
 * (harde regel 4).
 */
export default async function MargePagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const antwoord = await laadContract<MargeData>("marge");
  const data = antwoord.data;
  const gevuld = "per_groep" in data && data.kern !== null;

  return (
    <div className="space-y-6">
      <PaginaKop
        titel={t("marge.titel")}
        ondertitel={t("marge.ondertitel")}
      />

      <Briefing briefing={antwoord.briefing} titel={t("briefing.titel")} />

      {!gevuld ? (
        <Onbeschikbaar
              t={t}
          titel={t("marge.pergroep")}
          reden={
            reden(antwoord.onbeschikbaar, "marge_per_groep") ??
            reden(antwoord.onbeschikbaar, "marge_per_kanaal") ??
            t("marge.nogniet")
          }
        />
      ) : null}

      {gevuld && "kern" in data && data.kern ? (
        <>
          {/* Het eerste kerncijfer staat op het vaste bordeaux vlak; de twee
              ernaast op wit. Vaste posities, geen betekenis (huisstijl).

              De klassen `kerncijfer` en `kerncijfer-accent` zijn afdrukhaakjes:
              deze drie vlakken zijn met de hand gezet in plaats van via de
              component Kerncijfer, en zonder de haakjes verdwijnen ze op papier
              (wit op wit). Zie de afdruksectie in globals.css. */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="kerncijfer kerncijfer-accent rounded-klein bg-bordeaux p-6">
              <div className="kapitaal-label text-beige">{t("marge.gewogen")}</div>
              <div className="mt-2 text-3xl font-semibold tabular-nums whitespace-nowrap text-wit">
                {procent(data.kern.gewogen_pct)}
              </div>
              <div className="mt-1 text-sm font-light text-beige">
                {t("marge.overGedekt")}
              </div>
            </div>
            <div className="kerncijfer rounded-klein bg-wit p-6">
              <div className="kapitaal-label text-zwart">{t("marge.brutomarge30")}</div>
              <div className="mt-2 text-3xl font-semibold tabular-nums whitespace-nowrap text-zwart">
                {euro(data.kern.marge_30d)}
              </div>
              <div className="mt-1 text-sm font-light text-zwart">
                {t("marge.opGedekteOmzet", {
                  bedrag: euro(data.kern.gedekte_omzet_30d),
                })}
              </div>
            </div>
            <div className="kerncijfer rounded-klein bg-wit p-6">
              <div className="kapitaal-label text-zwart">{t("marge.dekking")}</div>
              <div className="mt-2 text-3xl font-semibold tabular-nums whitespace-nowrap text-zwart">
                {procent(data.kern.dekking_pct)}
              </div>
              <div className="mt-1 text-sm font-light text-zwart">
                {t("marge.heeftKosten")}
              </div>
            </div>
          </div>

          {data.kostenopbouw ? (
            <Kaart titel={t("marge.vanomzet")}>
              <Tabel
                data={{
                  kolommen: ["", t("kol.gewogen"), t("kol.bedrag30d")],
                  uitlijning: eersteLinks(3),
                  rijen: [
                    [t("marge.gedekt"), "", euro(data.kostenopbouw.omzet_30d)],
                    ...data.kostenopbouw.per_criterium.map((c) => [
                      `− ${c.criterium}` +
                        (c.groepen_n < data.per_groep.length
                          ? ` ${t(
                              c.groepen_n === 1
                                ? "marge.groepEnkelvoud"
                                : "marge.groepMeervoud",
                              { n: geheelGetal(c.groepen_n) },
                            )}`
                          : ""),
                      procent(c.pct_gewogen),
                      euro(c.kost_30d),
                    ]),
                    [
                      `= ${t("kol.brutomarge")}`,
                      procent(data.kern.gewogen_pct),
                      euro(data.kostenopbouw.marge_30d),
                    ],
                  ],
                }}
              />
              <MeerInfo label={t("algemeen.meerInfo")}>
                <p>{data.kostenopbouw.toelichting}</p>
                <p>{data.kern.toelichting}</p>
              </MeerInfo>
            </Kaart>
          ) : null}

          {data.staaf ? (
            /* Dicht sinds 19 aug 2026, en om een andere reden dan de rest:
               dit is geen verdieping maar dezelfde gegevens als de tabel
               eronder, in een plaatje. Van die twee is de tabel de bruikbare
               (ze draagt ook de opbouw en de marge), dus het beeld mag de
               tweede blik zijn in plaats van de eerste. */
            <KaartUitklap titel={t("marge.brutoPerGroep")}>
              <Staafgrafiek
                data={data.staaf}
                meetdagenTitel={t("algemeen.meetdagenTitel")}
                geenMetingTitel={t("algemeen.geenMetingTitel")}
                geenMetingTekst={t("algemeen.geenMeting")}
                meetdagenTekst={t("algemeen.meetdagenKort")}
              />
            </KaartUitklap>
          ) : null}

          <Kaart titel={t("marge.perGroepKort")}>
            <Tabel
              data={{
                kolommen: [
                  t("kol.groep"),
                  t("kol.aandeelOmzet"),
                  t("kol.kostenopbouw"),
                  t("kol.marge"),
                  t("kol.omzet30d"),
                  t("kol.brutomarge30d"),
                ],
                uitlijning: uitlijning(
                  "links",
                  "rechts",
                  "links",
                  "rechts",
                  "rechts",
                  "rechts",
                ),
                rijen: data.per_groep.map((r) => [
                  r.groep,
                  procent(r.aandeel),
                  opbouwTekst(r.kosten, t("marge.opbouwLeeg")),
                  r.marge_pct === null ? KASTLIJN : procent(r.marge_pct),
                  euro(r.omzet_30d),
                  r.marge_30d === null ? KASTLIJN : euro(r.marge_30d),
                ]),
              }}
            />
            {/* De specifieke reden uit het contract (wélke groepen, welk
                aandeel, waar in te vullen) hoort bij de streepjes zelf en
                niet alleen onderaan het scherm (audit 15 aug). De generieke
                uitleg blijft eronder voor wie het mechanisme wil begrijpen. */}
            {reden(antwoord.onbeschikbaar, "marge.ontbrekende_groepen") ? (
              <p className="mt-3 max-w-prose text-sm font-light text-zwart">
                {reden(antwoord.onbeschikbaar, "marge.ontbrekende_groepen")}
              </p>
            ) : null}
            <MeerInfo label={t("algemeen.meerInfo")}>
              <p>{t("marge.streepjeUitleg")}</p>
            </MeerInfo>
          </Kaart>
        </>
      ) : null}

      <Toelichting titel={t("algemeen.watNietStaat")} regels={antwoord.onbeschikbaar} t={t} taal={taal} />
    </div>
  );
}
