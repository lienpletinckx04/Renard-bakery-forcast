import { cookies } from "next/headers.js";

import Kaart from "@/components/Kaart";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import { COOKIE, lees } from "@/lib/auth";
import type { SluitingsdagenData } from "@/lib/contract";
import { contractBron } from "@/lib/contract-bron";
import { huidigeTaal, laadContract } from "@/lib/laadContract";
import { groepeerPeriodes } from "@/lib/sluitingsdagen";
import { laadSluitingen } from "@/lib/sluitingsdagen-db";
import { maakT } from "@/lib/taal";

import SluitingenFormulier, {
  type Kandidaat,
  type OverigeRij,
} from "./SluitingenFormulier";

export const dynamic = "force-dynamic";

/**
 * Het scherm Sluitingsdagen: de bevestigingslijst van de sluitingskalender.
 *
 * Twee gegevensbronnen, bewust gescheiden. De KANDIDATEN (welke feestdagen
 * vallen er de komende twaalf maanden?) komen uit het contract — dat is
 * kennis van de berekeningslaag. De UITSPRAKEN (wat heeft de beheerder
 * geantwoord?) komen rechtstreeks uit de database, want dit contract wordt
 * nachtelijk herbouwd en wie net iets bevestigd heeft, moet zijn eigen
 * invoer meteen terugzien — dezelfde uitzondering als de syncstand, met
 * dezelfde reden (zie lib/sluitingsdagen-db.ts).
 *
 * Is de database niet leesbaar, dan toont het scherm GEEN lijst met "nog
 * niet beantwoord": dat zou een uitspraak tonen die niemand gedaan heeft.
 * Het vak zegt wat er aan de hand is (harde regel 8).
 */
export default async function SluitingsdagenPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const [antwoord, stand, sessie] = await Promise.all([
    laadContract<SluitingsdagenData>("sluitingsdagen", { totaal: true }),
    laadSluitingen(),
    lees((await cookies()).get(COOKIE)?.value),
  ]);
  const magBewerken = sessie?.rol === "beheerder";
  const data = antwoord.data;

  const uitleg = (
    <MeerInfo label={t("sluit.hoewerkt")}>
      <p>{t("sluit.uitlegKandidaten")}</p>
      <p className="mt-2">{t("sluit.uitlegOnbekend")}</p>
      <p className="mt-2">{t("sluit.uitlegNachtelijk")}</p>
      {data.bestandsdekking_tot !== null ? (
        <p className="mt-2">
          {t("sluit.bestandsdekking", { tot: data.bestandsdekking_tekst })}
        </p>
      ) : null}
    </MeerInfo>
  );

  // Zonder leesbare database geen lijst: de kalender tonen met overal "nog
  // niet beantwoord" zou uitspraken verzwijgen die er misschien wel zijn.
  if (stand === null) {
    const reden =
      contractBron(process.env) === "db"
        ? t("sluit.dbOnbereikbaar")
        : t("sluit.alleenDb");
    return (
      <div className="space-y-6" data-buiten-rapport>
        <PaginaKop titel={t("sluit.titel")} ondertitel={t("sluit.ondertitel")} />
        <Onbeschikbaar t={t} titel={t("sluit.titel")} reden={reden} />
      </div>
    );
  }

  const perDatum = new Map(stand.dagen.map((d) => [d.datum, d]));
  const kandidaten: Kandidaat[] = data.kandidaten.map((k) => ({
    datum: k.datum,
    datumTekst: k.datum_tekst,
    naam: k.naam,
    toestand: perDatum.get(k.datum)?.toestand ?? "onbekend",
  }));

  const kandidaatDatums = new Set(data.kandidaten.map((k) => k.datum));
  const periodes = groepeerPeriodes(
    stand.dagen.filter((d) => d.bron === "periode"),
  );

  // Wat buiten het formulier valt, blijft zichtbaar: de eenmalig overgenomen
  // bestandslijst en feestdaguitspraken van eerdere jaren. Gegroepeerd per
  // aaneengesloten reeks met dezelfde reden en toestand — presentatie, geen
  // berekening.
  const buiten = stand.dagen.filter(
    (d) => d.bron !== "periode" && !kandidaatDatums.has(d.datum),
  );
  const overige: OverigeRij[] = (["dicht", "open"] as const).flatMap((w) =>
    groepeerPeriodes(buiten.filter((d) => d.toestand === w)).map((p) => ({
      ...p,
      toestand: w,
    })),
  );
  overige.sort((a, b) => (a.van < b.van ? -1 : 1));

  const eersteRegel = stand.regels[0] ?? null;

  return (
    <div className="space-y-6" data-buiten-rapport>
      <PaginaKop titel={t("sluit.titel")} ondertitel={t("sluit.ondertitel")} />

      <Kaart>
        {uitleg}
        {!magBewerken ? (
          <p className="mt-4 max-w-prose text-sm font-light text-zwart">
            {t("sluit.alleenBeheerderVak")}
          </p>
        ) : null}
        <div className="mt-4">
          <SluitingenFormulier
            kandidaten={kandidaten}
            periodes={periodes}
            regel={
              eersteRegel === null
                ? null
                : {
                    weekdag: eersteRegel.weekdag,
                    vanaf: eersteRegel.vanaf,
                    tot: eersteRegel.tot ?? "",
                  }
            }
            overige={overige}
            magBewerken={magBewerken}
            taal={taal}
          />
        </div>
      </Kaart>
    </div>
  );
}
