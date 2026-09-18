import { NextResponse, type NextRequest } from "next/server";

import { COOKIE, lees } from "@/lib/auth";

/**
 * De bewaking staat vóór de router, niet in de schermen.
 *
 * Dat is het verschil tussen een slot en een gordijn: zou elk scherm zelf
 * moeten controleren, dan is één vergeten scherm genoeg om de cijfers van de
 * klant openbaar te maken. Hier komt niemand langs zonder geldige sessie,
 * ook niet langs de RSC-payload van een statisch voorgerenderde bladzijde.
 */
export default async function proxy(verzoek: NextRequest) {
  const pad = verzoek.nextUrl.pathname;

  if (pad === "/login") {
    // Al aangemeld? Dan is het inlogscherm een omweg.
    if (await lees(verzoek.cookies.get(COOKIE)?.value)) {
      return NextResponse.redirect(new URL("/", verzoek.url));
    }
    return NextResponse.next();
  }

  if (await lees(verzoek.cookies.get(COOKIE)?.value)) return NextResponse.next();

  const naarLogin = new URL("/login", verzoek.url);
  if (pad !== "/") naarLogin.searchParams.set("terug", pad);
  const antwoord = NextResponse.redirect(naarLogin);
  antwoord.cookies.delete(COOKIE); // een verlopen of vervalste cookie ruimen we op
  return antwoord;
}

export const config = {
  // Alles behalve de statische bestanden van Next, het lettertype en de
  // merkbeelden (logo en fotografie: identiteit, geen cijfers — het
  // inlogscherm heeft ze nodig vóór er een sessie is). Het contract zit niet
  // bij die statische bestanden: het wordt op de server gelezen en verlaat de
  // server alleen binnen een bewaakt antwoord.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|fonts/|brand/).*)"],
};
