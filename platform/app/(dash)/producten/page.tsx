import Briefing from "@/components/Briefing";
import Kaart from "@/components/Kaart";
import KaartUitklap from "@/components/KaartUitklap";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import Ontbinding from "@/components/Ontbinding";
import PaginaKop from "@/components/PaginaKop";
import Staafgrafiek from "@/components/Staafgrafiek";
import Tabel from "@/components/Tabel";
import Toelichting from "@/components/Toelichting";
import type { ProductenData, VerschuivingRij } from "@/lib/contract";
import { aantal, euro, procent, verschilProcent } from "@/lib/format";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { maakT, type T } from "@/lib/taal";
import { reden } from "@/lib/toelichting";
import { eersteLinks, uitlijning } from "@/lib/uitlijning";

/** Rijen voor de verschuivingstabel; "nieuw" is een woord, geen percentage. */
function verschuivingsTabel(rijen: VerschuivingRij[], t: T) {
  return {
    kolommen: [t("kol.product"), t("kol.nu"), t("kol.ervoor"),
               t("kol.verschil")],
    rijen: rijen.map((r) => [
      r.naam,
      euro(r.omzet_nu),
      euro(r.omzet_vorig),
      r.nieuw
        ? `${euro(r.verschil)} (${t("prod.nieuw")})`
        : r.verschil_pct
          ? `${euro(r.verschil)} (${verschilProcent(r.verschil_pct)})`
          : euro(r.verschil),
    ]),
    uitlijning: eersteLinks(4),
  };
}

export const dynamic = "force-dynamic";

export default async function ProductenPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const antwoord = await laadContract<ProductenData>("producten");
  const { top, groepen, verschuiving } = antwoord.data;
  // `?? null`: een contract van vóór deze velden is hetzelfde geval als een
  // contract dat er bewust null in zet, en krijgt dezelfde behandeling.
  const concentratie = antwoord.data.concentratie ?? null;
  const prijsVolume = antwoord.data.prijs_volume ?? null;
  const groepenDetail = antwoord.data.groepen_detail ?? [];

  const tabel = {
    kolommen: [t("kol.product"), t("kol.groep"), t("kol.stuks"),
               t("kol.omzet"), t("kol.aandeel")],
    rijen: top.map((p) => [
      p.naam,
      p.groep,
      aantal(p.stuks),
      euro(p.omzet),
      procent(p.aandeel),
    ]),
    uitlijning: uitlijning("links", "links", "rechts", "rechts", "rechts"),
  };

  // De berekeningslaag weigert de vergelijking wanneer de twee vensters niet
  // even veel gemeten open dagen tellen. Dan zijn beide tabellen leeg, en een
  // lege tabel zonder uitleg is precies wat harde regel 8 verbiedt.
  const geenVerschuiving =
    verschuiving.stijgers.length === 0 && verschuiving.dalers.length === 0;
  const verschuivingReden =
    reden(antwoord.onbeschikbaar, "verschuiving") ??
    t("leeg.verschuiving");

  return (
    <div className="space-y-6">
      <PaginaKop
        titel={t("prod.titel")}
        ondertitel={t("prod.ondertitel")}
      />

      <Briefing briefing={antwoord.briefing} titel={t("briefing.titel")} />

      <Kaart titel={t("prod.top30")}>
        <Tabel data={tabel} />
      </Kaart>

      {/* De omzet bewoog: gingen er minder stuks over de toonbank, of brachten
          dezelfde stuks minder op? Dat onderscheid staat vóór de vraag welke
          producten het waren — anders leest de tabel eronder als de verklaring
          terwijl ze alleen de plaats aanwijst. */}
      {prijsVolume ? (
        <Kaart titel={t("prod.stuksOfPrijs")}>
          <Ontbinding data={prijsVolume} meerLabel={t("algemeen.meerInfo")} />
        </Kaart>
      ) : (
        <Onbeschikbaar
              t={t}
          titel={t("prod.stuksOfPrijs")}
          reden={
            reden(antwoord.onbeschikbaar, "prijs_volume") ??
            t("leeg.ontbinding")
          }
        />
      )}

      {geenVerschuiving ? (
        <Onbeschikbaar t={t} titel={t("prod.watbeweegt")} reden={verschuivingReden} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Kaart titel={t("prod.stijgers")}>
              <Tabel data={verschuivingsTabel(verschuiving.stijgers, t)} />
            </Kaart>
            <Kaart titel={t("prod.dalers")}>
              <Tabel data={verschuivingsTabel(verschuiving.dalers, t)} />
            </Kaart>
          </div>
          <MeerInfo label={t("algemeen.meerInfo")}>
            <p>{verschuiving.toelichting}</p>
          </MeerInfo>
        </>
      )}

      {/* Waar het geld werkelijk vandaan komt. Een assortimentsdiscussie gaat
          zelden over de kop en bijna altijd over de staart, en dat bedrag
          staat hier met zoveel woorden. */}
      {concentratie ? (
        /* Dicht sinds 19 aug 2026. Een assortimentsdiscussie is een
           kwartaalgesprek, geen ochtendblik — en dit blok draagt een tabel,
           twee kengetallen en een toelichting. */
        <KaartUitklap titel={t("prod.leunt")}>
          <Tabel
            data={{
              /* Koppen en rijlabels komen vertaald uit het contract; de UI
                 plakt hier geen eigen tekst meer (harde regel 4). */
              kolommen: concentratie.kolommen,
              rijen: concentratie.rijen.map((r) => [
                r.drempel,
                r.label,
                procent(r.aandeel_assortiment),
              ]),
              uitlijning: eersteLinks(3),
            }}
          />
          <dl className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-warmgrijs pt-4">
            <div>
              <dt className="kapitaal-label text-zwart">{t("prod.verkocht")}</dt>
              <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                {aantal(concentratie.totaal_producten)}
              </dd>
            </div>
            <div>
              <dt className="kapitaal-label text-zwart">
                {t("prod.staart", {
                  aantal: aantal(concentratie.staart_producten),
                })}
              </dt>
              <dd className="mt-0.5 text-sm font-medium text-zwart tabular-nums">
                {euro(concentratie.staart_omzet)}
              </dd>
            </div>
          </dl>
          <MeerInfo label={t("algemeen.meerInfo")}>
            <p>{concentratie.toelichting}</p>
          </MeerInfo>
        </KaartUitklap>
      ) : (
        <Onbeschikbaar
              t={t}
          titel={t("prod.leunt")}
          reden={
            reden(antwoord.onbeschikbaar, "concentratie") ??
            t("leeg.verdeling")
          }
        />
      )}

      {/* Dicht sinds 19 aug 2026: een staafgrafiek plus negentien
          uitklapbare groepen met elk een producttabel. De top-30 hierboven
          beantwoordt de dagelijkse vraag al; dit is de verdieping. */}
      <KaartUitklap titel={t("prod.pergroep")}>
        <Staafgrafiek
          data={groepen}
          meetdagenTitel={t("algemeen.meetdagenTitel")}
          geenMetingTitel={t("algemeen.geenMetingTitel")}
          geenMetingTekst={t("algemeen.geenMeting")}
          meetdagenTekst={t("algemeen.meetdagenKort")}
        />

        {/* De drill-down: dezelfde groepen, uitklapbaar tot op het product.
            Native <details> — geen script, geen toestand die kan liegen. De
            rest-regel houdt de som van de zichtbare rijen gelijk aan de
            groepsomzet: acht producten tonen en twaalf stil weglaten zou de
            staaf erboven tegenspreken. */}
        {groepenDetail.length > 0 ? (
          <div className="mt-6 border-t border-warmgrijs pt-4">
            <h3 className="kapitaal-label text-zwart">
              {t("prod.vanGroepNaarProduct")}
            </h3>
            <ul className="mt-3">
              {groepenDetail.map((g) => (
                <li key={g.groep} className="border-b border-warmgrijs">
                  <details className="group">
                    {/* `uitklap-kop`: afdrukhaakje. Deze regel draagt de
                        groepsnaam, het aandeel en de groepsomzet, en geen
                        ervan staat in de tabel eronder. Zonder de klasse
                        verbergt de afdrukregel haar en stonden er in de PDF
                        negentien naamloze producttabellen (19 aug 2026). */}
                    <summary className="uitklap-kop flex cursor-pointer list-none items-baseline justify-between gap-4 py-2.5 [&::-webkit-details-marker]:hidden">
                      <span className="text-sm text-zwart">
                        <span
                          aria-hidden="true"
                          className="mr-2 inline-block transition-transform group-open:rotate-90"
                        >
                          ›
                        </span>
                        {g.groep}
                        {g.aandeel !== null ? (
                          <span className="font-light">
                            {" "}
                            {t("prod.vanDeOmzet", {
                              pct: procent(g.aandeel),
                            })}
                          </span>
                        ) : null}
                      </span>
                      <span className="text-sm font-medium text-zwart tabular-nums">
                        {euro(g.omzet_30d)}
                      </span>
                    </summary>
                    <div className="pb-3 pl-6">
                      <Tabel
                        data={{
                          kolommen: [
                            t("kol.product"),
                            t("kol.stuks"),
                            t("kol.omzet"),
                            t("kol.indegroep"),
                          ],
                          rijen: [
                            ...g.producten.map((p) => [
                              p.naam,
                              aantal(p.stuks),
                              euro(p.omzet),
                              procent(p.aandeel_in_groep),
                            ]),
                            ...(g.rest
                              ? [[
                                  g.rest.label,
                                  "",
                                  euro(g.rest.omzet_30d),
                                  "",
                                ]]
                              : []),
                          ],
                          uitlijning: eersteLinks(4),
                        }}
                      />
                    </div>
                  </details>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </KaartUitklap>

      <Toelichting titel={t("algemeen.watNietStaat")} regels={antwoord.onbeschikbaar} t={t} taal={taal} />
    </div>
  );
}
