import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Navigatie from "@/components/Navigatie";
import RapportMenu from "@/components/RapportMenu";
import TaalKiezer from "@/components/TaalKiezer";
import WinkelKiezer from "@/components/WinkelKiezer";
import { COOKIE, lees } from "@/lib/auth";
import type { OverzichtData, StandData } from "@/lib/contract";
import {
  actieveWinkel,
  huidigeTaal,
  laadContract,
  laadWinkels,
} from "@/lib/laadContract";
import { datakwaliteitVoettekst } from "@/lib/stand";
import { laadSyncStand, syncInVoettekst } from "@/lib/syncstand";
import { maakT } from "@/lib/taal";
import { veldLabel } from "@/lib/toelichting";
import { versheid } from "@/lib/versheid";

/**
 * Deze schermen worden per verzoek gerenderd, niet vooraf gebouwd. Dat is
 * geen prestatiekeuze maar een afschermingskeuze: een vooraf gebouwde
 * bladzijde draagt de cijfers van de klant al in zich vóór iemand zich heeft
 * aangemeld. En het is de vorm die de periodekiezer straks nodig heeft.
 */
export const dynamic = "force-dynamic";

/**
 * `proxy.ts` houdt de deur dicht. Deze tweede controle bestaat omdat een
 * verkeerd afgestelde matcher stilzwijgend faalt, en omdat de layout de naam
 * van de aangemelde gebruiker toch nodig heeft.
 */
export default async function DashLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  if (!sessie) redirect("/login");

  // Per verzoek van schijf, langs dezelfde lader als de schermen: zo tonen
  // voettekst en schermen altijd hetzelfde contract — ook vlak na een
  // herberekening, en ook wanneer er een winkel gekozen is.
  const [taal, overzicht, standAntwoord, index, winkel, sync] =
    await Promise.all([
      huidigeTaal(),
      laadContract<OverzichtData>("overzicht"),
      laadContract<StandData>("stand"),
      laadWinkels(),
      actieveWinkel(),
      // Buiten het contract om, en als enige: zie lib/syncstand.ts. Op de
      // bestandsroute is dit null en verandert er niets aan deze voettekst.
      laadSyncStand(),
    ]);
  const t = maakT(taal);

  // Alle zes de antwoorden worden in één keer gebouwd en dragen dezelfde
  // envelope; het overzicht staat hier voor alle schermen.
  const stand = versheid(overzicht.bijgewerkt_op, overzicht.gemeten_tot, taal);

  // De ergste uitkomst van de wachters draagt de voettekst van elk scherm.
  // Bij "goed" staat er niets — geen alarmvermoeidheid; anders één sober
  // woordpaar dat naar het standblok op Instellingen leidt. Tekst, geen kleur.
  const kwaliteit = datakwaliteitVoettekst(standAntwoord.data.ergste, t);

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Wie met het toetsenbord binnenkomt, hoeft niet elke keer langs het
          woordmerk en zes navigatielinks: één sprong naar de inhoud. */}
      <a
        href="#inhoud"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-klein focus:bg-wit focus:px-4 focus:py-2 focus:text-sm focus:text-zwart"
      >
        {t("nav.naarInhoud")}
      </a>
      <Navigatie gebruiker={sessie.gebruiker} taal={taal} />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* De balk boven de inhoud: links waar je naar kijkt (welke winkel),
            rechts wat je ermee doet (het rapport). Tot 18 augustus 2026 bestond
            deze balk alleen bij twee of meer winkels, en stond de rapportknop
            onderaan het bordeaux zijvlak tussen de gebruikersnaam en het
            afmelden. Dat is de accountzone; een rapport over de cijfers die je
            bekijkt, is een handeling op het document en hoort bovenaan bij de
            inhoud te staan — op elk scherm dezelfde plek.

            De winkelkeuze geldt voor élk scherm tegelijk (één waarheid per
            blik), en dus ook voor het rapport: dat leest hetzelfde contract via
            dezelfde lader. */}
        <div className="niet-afdrukken flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-warmgrijs px-4 py-2.5 sm:px-6 lg:px-10">
          {index.winkels.length >= 2 ? (
            <>
              <WinkelKiezer
                winkels={index.winkels}
                actief={winkel?.slug ?? ""}
                taal={taal}
              />
              <span className="text-xs font-light text-zwart">
                {winkel === null
                  ? t("winkel.alleSamen") +
                    (index.niet_toegewezen.length > 0
                      ? t("winkel.inclusiefNietToegewezen")
                      : "")
                  : t("winkel.alleen", { naam: winkel.naam })}
              </span>
            </>
          ) : null}
          <div className="ml-auto">
            <RapportMenu t={t} />
          </div>
        </div>
        <main id="inhoud" className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">{children}</main>
        {/* Twee tijdstippen, uitgeschreven: tot waar de cijfers lopen, en
            wanneer ze verwerkt zijn. Die twee lopen uiteen zodra een
            synchronisatie achterloopt, en dan is het verwerkingsmoment alleen
            een verkeerd signaal over de versheid. */}
        <footer className="border-t border-warmgrijs px-4 py-4 text-xs font-light text-zwart sm:px-6 lg:px-10">
          {stand.cijfers} · {stand.verwerkt} · {t("voet.bron")}:{" "}
          {/* De bronnamen in de envelope zijn machinesleutels ("deliveroo");
              hetzelfde veldLabel als op Instellingen maakt ze leesbaar. */}
          {overzicht.bron.map((b) => veldLabel(b, taal)).join(", ")}
          {kwaliteit ? (
            <>
              {" · "}
              <Link
                href="/instellingen"
                className="underline underline-offset-2"
              >
                {kwaliteit}
              </Link>
            </>
          ) : null}
          {/* De dodemansknop. Alleen zichtbaar wanneer er iets aan de hand is
              — bij een geslaagde nachtrun staat er niets, zoals bij de
              datakwaliteit hierboven. Twee tijdstippen die klopten toen ze
              geschreven werden zeggen niets over of ze nog vernieuwd worden;
              dit wel. */}
          {syncInVoettekst(sync) ? (
            <>
              {" · "}
              <Link
                href="/instellingen"
                className="underline underline-offset-2"
              >
                {t("sync.voettekst")}
              </Link>
            </>
          ) : null}
        </footer>
      </div>
      {/* Buiten de kolommen, want hij hoort bij het scherm en niet bij de
          inhoud: vast linksonder, op elk formaat dezelfde plek. */}
      <TaalKiezer actief={taal} label={t("taal.label")} />
    </div>
  );
}
