"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { alsTaal, TAAL_COOKIE, type Taal } from "@/lib/taal";

/**
 * De taalkeuze is een leesvoorkeur, en de enige in dit platform die géén
 * sessie vereist.
 *
 * WAAROM DAT VERSCHIL MET `kiesWinkel`. Die actie leest de winkelindex om de
 * keuze te toetsen, en die index verklapt hoeveel vestigingen de klant heeft en
 * hoe ze heten — bedrijfsinformatie, dus alleen na aanmelden. Een taal verklapt
 * niets en geeft toegang tot niets: het is een cookie met "nl" of "fr" erin.
 * Zou hij een sessie eisen, dan kan een Franstalige gebruiker het
 * aanmeldscherm niet in zijn taal lezen — precies het scherm waar hij nog geen
 * sessie kan hebben.
 *
 * `alsTaal` toetst de waarde vóór hij de cookie in gaat. Die cookie wordt in
 * `laadContract` een mapnaam, en een niet-getoetste waarde die een pad kiest is
 * precies de fout waarmee je een lezer buiten zijn map laat kijken. Dat de
 * waarde van buiten komt, is daarom geen probleem: alleen "nl" en "fr" komen er
 * doorheen.
 *
 * `revalidatePath("/", "layout")` en niet alleen de huidige bladzijde: de taal
 * raakt de navigatie en de voettekst, en die staan in de layout.
 */
export async function kiesTaal(keuze: string): Promise<void> {
  const beheer = await cookies();
  const taal: Taal = alsTaal(keuze);
  beheer.set(TAAL_COOKIE, taal, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  revalidatePath("/", "layout");
}
