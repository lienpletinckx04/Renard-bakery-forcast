"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { COOKIE, lees } from "@/lib/auth";
import { laadWinkels, WINKEL_COOKIE } from "@/lib/laadContract";

/**
 * De winkelkeuze is een leesvoorkeur per gebruiker, geen wijziging aan data.
 * De slug wordt tegen de index getoetst: wat de contractbouw niet kent,
 * wordt het totaal (lege cookie). Alleen ingelogde gebruikers, elke rol.
 */
export async function kiesWinkel(slug: string): Promise<void> {
  const beheer = await cookies();
  const sessie = await lees(beheer.get(COOKIE)?.value);
  if (!sessie) return;

  const index = await laadWinkels();
  const bekend = index.winkels.some((w) => w.slug === slug);
  if (bekend) {
    beheer.set(WINKEL_COOKIE, slug, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  } else {
    beheer.delete(WINKEL_COOKIE);
  }
  revalidatePath("/", "layout");
}
