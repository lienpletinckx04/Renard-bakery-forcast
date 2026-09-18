"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { COOKIE, SESSIEDUUR_SECONDEN, erZijnGebruikers, teken, verifieer } from "@/lib/auth";
import type { Sleutel } from "@/lib/taal";

/**
 * De uitkomst draagt een SLEUTEL en geen tekst. De server-actie weet niet welke
 * taal de lezer gekozen heeft — dat weet de bladzijde, die de cookie leest.
 * Een tekst hier zou het aanmeldscherm eentalig maken, hoe de rest ook staat.
 */
export type Uitkomst = { fout?: Sleutel };

/**
 * Rem op raden: na vijf mislukte pogingen op een naam gaat die naam een
 * minuut op slot. In het geheugen van dit proces — geen database nodig, en
 * elke poging kost sowieso al een volle PBKDF2-afleiding. Het slot zit op de
 * naam en niet op het IP: dit platform heeft een handvol bekende gebruikers,
 * en een aanvaller die namen roteert, botst per naam opnieuw op het slot.
 *
 * WAT DEZE REM OP VERCEL WÉL EN NIET DOET (opgeschreven 18 aug 2026, zodat
 * niemand hem voor meer aanziet dan hij is). "Het geheugen van dit proces" is
 * op een serverless platform het geheugen van één lambda-instantie. Vercel
 * schaalt naar meerdere instanties en koelt ze af, dus vijf pogingen is in de
 * praktijk vijf per instantie, en een herstart wist de teller.
 *
 * Dat is bewust aanvaard en geen vergissing: de echte rem op raden is hier
 * PBKDF2 (elke poging kost rekentijd, ook de mislukte) plus een gesloten
 * gebruikerslijst. Deze map is een goedkope extra horde tegen het domste
 * geraad, niet de verdediging zelf. Wie hem tot echte verdediging wil maken,
 * verhuist de teller naar de database — dat kan pas na S11, en het staat als
 * open punt genoteerd.
 */
const POGINGEN_MAX = 5;
const SLOT_MS = 60_000;
const pogingen = new Map<string, { fouten: number; tot: number }>();

export async function aanmelden(_vorige: Uitkomst, formulier: FormData): Promise<Uitkomst> {
  const gebruiker = String(formulier.get("gebruiker") ?? "");
  const wachtwoord = String(formulier.get("wachtwoord") ?? "");
  const terug = String(formulier.get("terug") ?? "/");

  if (!erZijnGebruikers()) {
    return { fout: "login.geenGebruikers" };
  }
  if (!gebruiker || !wachtwoord) {
    return { fout: "login.leegVeld" };
  }

  const sleutel = gebruiker.trim().toLowerCase();
  const stand = pogingen.get(sleutel);
  if (stand && stand.fouten >= POGINGEN_MAX && Date.now() < stand.tot) {
    return { fout: "login.opSlot" };
  }

  const sessie = await verifieer(gebruiker, wachtwoord);
  if (!sessie) {
    // Binnen het venster telt de reeks door; erbuiten begint ze opnieuw.
    const nu = Date.now();
    const vorige = pogingen.get(sleutel);
    pogingen.set(sleutel, {
      fouten: vorige && nu < vorige.tot ? vorige.fouten + 1 : 1,
      tot: nu + SLOT_MS,
    });
    // Eén melding voor beide gevallen: een aparte tekst voor "die naam bestaat
    // niet" vertelt een buitenstaander welke namen wél bestaan.
    return { fout: "login.mislukt" };
  }
  pogingen.delete(sleutel);

  const jar = await cookies();
  jar.set(COOKIE, await teken(sessie), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSIEDUUR_SECONDEN,
  });

  // Alleen een pad binnen het platform, nooit een adres van buiten.
  redirect(terug.startsWith("/") && !terug.startsWith("//") ? terug : "/");
}

export async function afmelden() {
  const jar = await cookies();
  jar.delete(COOKIE);
  redirect("/login");
}
