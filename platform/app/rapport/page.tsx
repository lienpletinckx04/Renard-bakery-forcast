import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Dagoverzicht from "@/app/(dash)/page";
import Kanalen from "@/app/(dash)/kanalen/page";
import Instellingen from "@/app/(dash)/instellingen/page";
import Marge from "@/app/(dash)/marge/page";
import Prognose from "@/app/(dash)/prognose/page";
import Producten from "@/app/(dash)/producten/page";
import RapportMenu from "@/components/RapportMenu";
import Woordmerk from "@/components/Woordmerk";
import { COOKIE, lees } from "@/lib/auth";
import type { OverzichtData, StandData } from "@/lib/contract";
import {
  actieveWinkel,
  huidigeTaal,
  laadContract,
} from "@/lib/laadContract";
import {
  DEEL_NAAM,
  DEEL_PARAM,
  kiesDelen,
  RAPPORT_DELEN,
  type RapportDeel,
} from "@/lib/rapport";
import { datakwaliteitVoettekst } from "@/lib/stand";
import { maakT } from "@/lib/taal";
import { veldLabel } from "@/lib/toelichting";
import { versheid } from "@/lib/versheid";

import Rapportknoppen from "./Rapportknoppen";

/**
 * Het CFO-rapport: dezelfde schermen, gekozen onderdelen, klaar om af te
 * drukken of als PDF te bewaren.
 *
 * WAAROM DIT GEEN BESTAND MEER IS. Tot 18 augustus 2026 was het rapport een PDF
 * die `make rapport-pdf` vooraf bouwde met WeasyPrint, en die deze route van
 * schijf serveerde. Dat had twee gebreken die niet met opmaak te verhelpen
 * waren. Het eerste: het bestand was zo vers als de laatste bouw, dus wie na
 * een herberekening op de knop drukte, kreeg andere cijfers dan op het scherm
 * naast hem stonden — precies wat `laadContract` voor de schermen juist
 * voorkomt. Het tweede: het was een tweede tekenlaag met een eigen kopie van de
 * huisstijl (kleuren, tabellen, SVG-geometrie) naast de componenten hier, en
 * twee tekenlagen van hetzelfde document lopen uiteen. Het rapport is nu een
 * weergave: het leest bij elk verzoek hetzelfde contract als de schermen en
 * bestaat uit dezelfde componenten. Uiteenlopen kan niet meer, en de browser
 * maakt er de PDF van.
 *
 * WAAROM DE SCHERMEN ZELF EN GEEN TWEEDE SAMENSTELLING. De onderdelen hieronder
 * zijn de paginacomponenten van de schermen, niet een tweede opbouw uit het
 * contract. Een blok dat op een scherm bijkomt, staat daarmee ook in het
 * rapport. Wat niet op papier hoort — een formulier, een knoppenrij — draagt in
 * die schermen `data-buiten-rapport` en valt hier weg (zie globals.css).
 *
 * WAT DE LEZER KIEST. De keuze staat in de URL (`?deel=kanalen&deel=prognose`),
 * niet in een cookie: zo is een rapport een adres dat je kunt doorsturen en
 * bewaren, en is er geen bewaarde toestand die van het document kan afwijken.
 */
export const dynamic = "force-dynamic";

/**
 * De schermen in een `Record` over álle sleutels: een nieuw onderdeel in
 * `RAPPORT_DELEN` zonder scherm hier is een typefout en geen stille leegte.
 * Bewust de componenten en niet hun elementen — een onderdeel dat niet gekozen
 * is, wordt dan ook niet gerenderd en leest geen contract.
 */
const ONDERDEEL: Record<RapportDeel, React.ComponentType> = {
  overzicht: Dagoverzicht,
  kanalen: Kanalen,
  producten: Producten,
  marge: Marge,
  prognose: Prognose,
  stand: Instellingen,
};

export default async function RapportPagina({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // De proxy houdt de deur al dicht; dit is de tweede grendel, net als in de
  // dash-layout. Een verkeerd afgestelde matcher faalt stilzwijgend, en dit is
  // een bladzijde met alle cijfers van de klant tegelijk.
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  if (!sessie) redirect("/login?terug=/rapport");

  const gekozen = kiesDelen((await searchParams)[DEEL_PARAM]);

  const [taal, overzicht, standAntwoord, winkel] = await Promise.all([
    huidigeTaal(),
    laadContract<OverzichtData>("overzicht"),
    laadContract<StandData>("stand"),
    actieveWinkel(),
  ]);
  const t = maakT(taal);
  const stand = versheid(overzicht.bijgewerkt_op, overzicht.gemeten_tot, taal);
  const kwaliteit = datakwaliteitVoettekst(standAntwoord.data.ergste, t);

  return (
    /* `print:bg-wit`: op papier draagt niet het beige vlak maar de haarlijn (zie
       de afdruksectie in globals.css). Daarmee ziet de afdruk er hetzelfde uit
       of de lezer "achtergronden meenemen" nu aanvinkt of niet — één
       voorspelbaar document in plaats van twee. */
    <div className="min-h-screen bg-beige print:bg-wit">
      {/* De knoppenrij hoort bij het scherm en niet bij het document: ze staat
          hierboven, blijft staan bij het scrollen, en verdwijnt bij het
          afdrukken. */}
      <div className="niet-afdrukken sticky top-0 z-20 border-b border-warmgrijs bg-beige/95 px-4 py-3 sm:px-6 lg:px-10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="text-sm font-light text-zwart underline-offset-2 hover:underline"
          >
            {t("rapport.terug")}
          </Link>
          <div className="flex items-center gap-3">
            <RapportMenu t={t} gekozen={gekozen} nieuwTabblad={false} />
            <Rapportknoppen
              label={t("rapport.afdrukken")}
              omschrijving={t("rapport.afdrukkenLang")}
            />
          </div>
        </div>
      </div>

      <article
        id="rapport"
        className="rapport mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-10"
      >
        <header className="border-b border-warmgrijs pb-6">
          {/* Zwart op licht, zoals de logogids het voorschrijft. */}
          <Woordmerk className="w-40 text-zwart" />
          <h1 className="kapitaal-kop mt-6 text-bordeaux">
            {t("rapport.titel")}
          </h1>
          {/* Twee tijdstippen, dezelfde als in de voettekst van elk scherm: tot
              waar de cijfers lopen, en wanneer ze verwerkt zijn. Op papier is
              dat geen franje maar het enige dat een afdruk dateert. */}
          <p className="mt-2 text-sm font-light text-zwart">
            {stand.cijfers} · {stand.verwerkt}
          </p>
          <p className="mt-0.5 text-sm font-light text-zwart">
            {winkel === null
              ? t("winkel.alleSamen")
              : t("winkel.alleen", { naam: winkel.naam })}{" "}
            · {t("voet.bron")}:{" "}
            {overzicht.bron.map((b) => veldLabel(b, taal)).join(", ")}
          </p>
          {/* De inhoudsopgave: op een afdruk is dit de enige plek waar staat wat
              er gekozen is, en dus ook wat er niet in zit. */}
          <p className="mt-4 max-w-prose text-sm text-zwart">
            <span className="kapitaal-label">{t("rapport.bevat")}</span>{" "}
            {gekozen.map((deel) => t(DEEL_NAAM[deel])).join(" · ")}
          </p>
          <p className="mt-3 max-w-prose text-xs font-light text-zwart">
            {t("rapport.herkomst")}
          </p>
        </header>

        {/* De vaste volgorde van RAPPORT_DELEN, niet de volgorde van de
            parameters: dezelfde keuze levert altijd hetzelfde document. */}
        {RAPPORT_DELEN.filter((deel) => gekozen.includes(deel)).map((deel) => {
          const Scherm = ONDERDEEL[deel];
          return (
            <section key={deel} className="rapportdeel space-y-6 pt-8">
              <Scherm />
            </section>
          );
        })}

        <footer className="mt-8 border-t border-warmgrijs pt-4 text-xs font-light text-zwart">
          {t("voet.bron")}:{" "}
          {overzicht.bron.map((b) => veldLabel(b, taal)).join(", ")}
          {/* Geen link zoals in de schermvoettekst: op papier klikt niemand.
              De melding zelf hoort er wél te staan — een rapport dat zwijgt
              over een haperende aanvoer, laat de lezer erin lopen. */}
          {kwaliteit ? ` · ${kwaliteit}` : null}
        </footer>
      </article>
    </div>
  );
}
