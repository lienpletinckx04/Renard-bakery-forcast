import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

import { huidigeTaal } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";

const interTight = localFont({
  src: "../fonts/InterTight-VariableFont_wght.ttf",
  weight: "300 700",
  variable: "--font-inter-tight",
  display: "swap",
});

/* Titel en omschrijving volgen de taalcookie: een Franse lezer hoort ook in
 * de browsertab Frans te zien. Elke pagina is al dynamisch (sessiecookie),
 * dus dit verandert niets aan het renderen. */
export async function generateMetadata(): Promise<Metadata> {
  const t = maakT(await huidigeTaal());
  return {
    title: t("meta.titel"),
    description: t("meta.omschrijving"),
  };
}

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const taal = await huidigeTaal();
  return (
    <html lang={taal === "fr" ? "fr-BE" : "nl-BE"} className={interTight.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
