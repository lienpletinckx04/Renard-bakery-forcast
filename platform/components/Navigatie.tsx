"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import Woordmerk from "@/components/Woordmerk";
import { afmelden } from "@/app/(auth)/login/acties";
import { maakT, type Sleutel, type Taal } from "@/lib/taal";

/** Het pad is de identiteit; de naam komt uit het woordenboek. */
const ITEMS: { pad: string; sleutel: Sleutel }[] = [
  { pad: "/", sleutel: "nav.dagoverzicht" },
  { pad: "/kanalen", sleutel: "nav.kanalen" },
  { pad: "/producten", sleutel: "nav.producten" },
  { pad: "/marge", sleutel: "nav.marge" },
  // Boven Prognose, bewust: de sluitingskalender is de invoer waar de
  // prognose op rekent, en het scherm dat haar voedt hoort ernaast te staan.
  { pad: "/sluitingsdagen", sleutel: "nav.sluitingsdagen" },
  { pad: "/prognose", sleutel: "nav.prognose" },
  // Bij de beheerschermen achteraan en niet vooraan: een bronbestand opladen
  // is onderhoud dat af en toe gebeurt, geen cijfer dat je dagelijks opzoekt.
  { pad: "/deliveroo", sleutel: "nav.deliveroo" },
  { pad: "/instellingen", sleutel: "nav.instellingen" },
];

/**
 * De navigatie in twee gedaanten: op een breed scherm een bordeaux zijvlak
 * met het beige woordmerk (het negatief uit de logogids), op een smal scherm
 * een bordeaux kopband met dezelfde items als horizontale rij.
 *
 * De actieve staat is een beige vlak met bordeaux tekst — het omgekeerde van
 * de rest van het vlak, in één oogopslag te zien. Bordeaux en beige zijn hier
 * allebei identiteit, nergens betekenis.
 */
export default function Navigatie({
  gebruiker,
  taal,
}: {
  gebruiker: string;
  taal: Taal;
}) {
  const pad = usePathname();
  const t = maakT(taal);

  const item = (naam: string, itemPad: string, blok: boolean) => {
    const actief = pad === itemPad;
    const basis = blok
      ? "block rounded-klein px-3 py-2.5 text-[0.6875rem] uppercase tracking-[0.14em]"
      : "inline-block rounded-klein px-2.5 py-1.5 text-[0.625rem] uppercase tracking-[0.12em] whitespace-nowrap";
    return (
      <Link
        href={itemPad}
        className={
          actief
            ? `${basis} bg-beige font-semibold text-bordeaux`
            : `${basis} font-medium text-beige hover:bg-beige/10`
        }
        aria-current={actief ? "page" : undefined}
      >
        {naam}
      </Link>
    );
  };

  return (
    <>
      {/* Breed scherm: het bordeaux zijvlak. Op papier hoort navigatie niet:
          een afdruk van een scherm zou er een leeg vlak met onleesbare beige
          tekst aan overhouden, want een printer legt achtergronden pas op
          verzoek van de lezer. */}
      <aside className="niet-afdrukken hidden w-60 shrink-0 lg:flex lg:flex-col lg:bg-bordeaux">
        <Link href="/" className="block px-6 pt-8 pb-10 text-beige">
          <Woordmerk className="w-36" />
          <span className="mt-3 block text-[0.625rem] font-light uppercase tracking-[0.22em]">
            {t("nav.ondertitel")}
          </span>
        </Link>
        {/* Een eigen nav-landmark, net als de smalle variant: zonder haar kan
            een schermlezergebruiker op een breed scherm niet naar de navigatie
            springen. Twee landmarks tegelijk levert het niet op — de andere
            variant staat op dat moment op display:none en valt daarmee buiten
            de toegankelijkheidsboom. */}
        <nav aria-label={t("nav.hoofdnavigatie")}>
          <ul className="space-y-1 px-3">
            {ITEMS.map((i) => (
              <li key={i.pad}>{item(t(i.sleutel), i.pad, true)}</li>
            ))}
          </ul>
        </nav>
        {/* De voetzone: beige met het handgetekende lijnpatroon, zoals de
            binnenkant van de broodzak. Het patroon staat alleen op beige.

            Hier stond tot 18 augustus 2026 ook de rapportknop. Die is naar de
            balk boven de inhoud verhuisd (zie app/(dash)/layout.tsx): deze zone
            gaat over wie je bent en hoe je weggaat, niet over de cijfers. */}
        <div className="lijnpatroon mt-auto space-y-1 px-6 py-5">
          <p className="text-xs font-normal text-zwart">{gebruiker}</p>
          {/* Afmelden is een handeling, geen bladzijde: een formulier dat de
              sessiecookie wist, en geen link die er alleen maar op lijkt. */}
          <form action={afmelden}>
            <button
              type="submit"
              className="text-left text-xs font-light text-zwart underline-offset-2 hover:underline"
            >
              {t("nav.afmelden")}
            </button>
          </form>
        </div>
      </aside>

      {/* Smal scherm: bordeaux kopband met dezelfde items. */}
      <header className="niet-afdrukken bg-bordeaux px-4 pt-5 pb-3 lg:hidden">
        <div className="flex items-start justify-between gap-4 text-beige">
          <Link href="/" className="block">
            <Woordmerk className="w-28" />
            <span className="mt-2 block text-[0.5625rem] font-light uppercase tracking-[0.22em]">
              {t("nav.ondertitel")}
            </span>
          </Link>
          <form action={afmelden}>
            <button
              type="submit"
              className="text-xs font-light text-beige underline-offset-2 hover:underline"
            >
              {t("nav.afmelden")}
            </button>
          </form>
        </div>
        <nav aria-label={t("nav.hoofdnavigatie")} className="-mx-4 mt-4 overflow-x-auto px-4">
          <ul className="flex gap-1">
            {ITEMS.map((i) => (
              <li key={i.pad}>{item(t(i.sleutel), i.pad, false)}</li>
            ))}
          </ul>
        </nav>
      </header>
    </>
  );
}
