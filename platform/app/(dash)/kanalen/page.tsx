import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import Lijngrafiek from "@/components/Lijngrafiek";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import Tabel from "@/components/Tabel";
import Toelichting from "@/components/Toelichting";
import type { KanalenData } from "@/lib/contract";
import { aantal, euro, procent } from "@/lib/format";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";
import { reden } from "@/lib/toelichting";
import { eersteLinks } from "@/lib/uitlijning";

/**
 * Verkoopkanalen: wat elk kanaal werkelijk bijdraagt. Bovenaan de financiële
 * wig per kanaal (bruto → commissie → netto), daaronder per kanaal zijn eigen
 * kaart met verloop. Een kanaal zonder data blijft in de rij staan als
 * onbeschikbaar met de reden (harde regel 8). Alles komt kant-en-klaar uit
 * het contract; hier wordt niets opgeteld (harde regel 4).
 */
export const dynamic = "force-dynamic";

export default async function KanalenPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const antwoord = await laadContract<KanalenData>("kanalen");

  const metWig = antwoord.data.kanalen.filter(
    (k) => k.bruto_30d !== null && k.netto_30d !== null,
  );

  return (
    <div className="space-y-6">
      <PaginaKop
        titel={t("kanalen.titel")}
        ondertitel={t("kanalen.ondertitel")}
      />

      <Briefing briefing={antwoord.briefing} titel={t("briefing.titel")} />

      {metWig.length > 0 ? (
        <Kaart titel={t("kanalen.watblijft")}>
          <Tabel
            data={{
              kolommen: [
                t("kol.kanaal"),
                t("kol.bruto"),
                t("kol.commissie"),
                t("kol.netto"),
                t("kol.inhouding"),
              ],
              uitlijning: eersteLinks(5),
              rijen: metWig.map((k) => [
                k.naam,
                euro(k.bruto_30d!),
                // Geen commissie in het contract is "onbekend", nooit € 0,00:
                // de UI verzint geen cijfer (harde regels 4 en 8).
                k.commissie_30d !== null
                  ? euro(k.commissie_30d)
                  : t("kanalen.onbekend"),
                euro(k.netto_30d!),
                k.inhouding_pct !== null
                  ? procent(k.inhouding_pct)
                  : t("kanalen.geen"),
              ]),
            }}
          />
          {/* De definitie van bruto, commissie en netto. Noodzakelijk om de
              tabel één keer te lezen, overbodig bij elke volgende blik. */}
          <MeerInfo label={t("algemeen.meerInfo")}>
            <p>{t("kanalen.wigUitleg")}</p>
          </MeerInfo>
        </Kaart>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {antwoord.data.kanalen.map((kanaal) => {
          // Via reden(), zoals elke andere leesroute op dit scherm: tot
          // 18 aug 2026 bouwde deze pagina hier een eigen Map die het
          // voorvoegsel "kanaal." wegknipte — twee routes naar dezelfde
          // regels, en de tweede vond ook sleutels die niet van een kanaal
          // waren.
          const kanaalReden = reden(
            antwoord.onbeschikbaar,
            `kanaal.${kanaal.kanaal}`,
          );
          if (kanaalReden || kanaal.omzet_30d === null || kanaal.aandeel === null) {
            return (
              <Onbeschikbaar
              t={t}
                key={kanaal.kanaal}
                titel={kanaal.naam}
                reden={kanaalReden ?? t("kanalen.geenKoppeling")}
              />
            );
          }
          return (
            <Kaart key={kanaal.kanaal} titel={kanaal.naam}>
              <div className="text-3xl font-semibold text-zwart tabular-nums">
                {euro(kanaal.omzet_30d)}
              </div>
              <div className="mt-1 text-sm font-light text-zwart">
                {t("kanalen.laatste30Aandeel")}{" "}
                <span className="font-medium text-zwart tabular-nums">
                  {procent(kanaal.aandeel)}
                </span>
              </div>
              {kanaal.verloop ? (
                <div className="mt-4">
                  <Lijngrafiek data={kanaal.verloop} compact />
                </div>
              ) : null}
              {/* Tot 18 aug verdween deze hele lijst zodra één veld ontbrak —
                  ook de velden die er wél waren, zonder reden (schending van
                  harde regel 8). Nu beslist elke regel voor zich: een
                  aanwezige waarde wordt getoond, een ontbrekende heet
                  "onbekend", zoals in de wigtabel bovenaan. Alleen het
                  bruto/commissie-paar blijft als geheel weg wanneer de wig
                  niet bestaat: voor de winkel is er geen platform dat inhoudt,
                  en dat is geen ontbrekend cijfer maar een niet-bestaand. */}
              <dl className="mt-4 space-y-1 border-t border-warmgrijs pt-3 text-sm text-zwart">
                {kanaal.commissie_30d !== null &&
                kanaal.bruto_30d !== null &&
                kanaal.inhouding_pct !== null ? (
                  <>
                    <div className="flex justify-between gap-4">
                      <dt className="font-light">{t("kanalen.brutoVerkocht")}</dt>
                      <dd className="font-medium tabular-nums">
                        {euro(kanaal.bruto_30d)}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="font-light">
                        {t("kanalen.commissiePct", {
                          pct: procent(kanaal.inhouding_pct),
                        })}
                      </dt>
                      <dd className="font-medium tabular-nums">
                        {euro(kanaal.commissie_30d)}
                      </dd>
                    </div>
                  </>
                ) : null}
                <div className="flex justify-between gap-4">
                  <dt className="font-light">{t("kanalen.perMeetdag")}</dt>
                  <dd className="font-medium tabular-nums">
                    {kanaal.gem_dagomzet !== null
                      ? euro(kanaal.gem_dagomzet)
                      : t("kanalen.onbekend")}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-light">{t("kol.stuks")}</dt>
                  <dd className="font-medium tabular-nums">
                    {kanaal.stuks_30d !== null
                      ? aantal(kanaal.stuks_30d)
                      : t("kanalen.onbekend")}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-light">{t("kol.meetdagen")}</dt>
                  <dd className="font-medium tabular-nums">
                    {kanaal.meetdagen !== null
                      ? aantal(kanaal.meetdagen)
                      : t("kanalen.onbekend")}
                  </dd>
                </div>
              </dl>
            </Kaart>
          );
        })}
      </div>

      {reden(antwoord.onbeschikbaar, "kanaal.tgtg.kost") ? (
        <Onbeschikbaar
              t={t}
          titel={t("kanalen.tgtgKost")}
          reden={reden(antwoord.onbeschikbaar, "kanaal.tgtg.kost")!}
        />
      ) : null}

      <Toelichting titel={t("algemeen.watNietStaat")} regels={antwoord.onbeschikbaar} t={t} taal={taal} />
    </div>
  );
}
