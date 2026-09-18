import Image from "next/image";

import TaalKiezer from "@/components/TaalKiezer";
import Woordmerk from "@/components/Woordmerk";
import { huidigeTaal } from "@/lib/laadContract";
import { maakT } from "@/lib/taal";
import Formulier from "./Formulier";

export async function generateMetadata() {
  const t = maakT(await huidigeTaal());
  return { title: t("meta.login") };
}

/**
 * Het toegangsscherm als tweeluik, naar de flyer uit het moodboard: een effen
 * bordeaux vlak met het beige woordmerk en een foto-inzet, daarnaast het
 * formulier op beige met het handgetekende lijnpatroon. Op een smal scherm
 * klapt het tweeluik naar een bordeaux kopband boven het formulier.
 */
export default async function LoginPagina({
  searchParams,
}: {
  searchParams: Promise<{ terug?: string }>;
}) {
  const { terug } = await searchParams;
  const taal = await huidigeTaal();
  const t = maakT(taal);
  return (
    <main className="flex min-h-screen flex-col lg:flex-row">
      <section className="flex flex-col justify-between bg-bordeaux px-8 py-10 text-beige lg:w-[44%] lg:px-14 lg:py-14">
        <div>
          <Woordmerk className="w-52 lg:w-72" />
          <p className="mt-4 text-[0.6875rem] font-light uppercase tracking-[0.22em]">
            {t("nav.ondertitel")}
          </p>
        </div>
        <div className="mt-10 hidden lg:block">
          <Image
            src="/brand/verpakking.png"
            alt={t("login.fotoAlt")}
            width={401}
            height={478}
            priority
            className="w-64 xl:w-72"
          />
          <p className="mt-4 text-[0.625rem] font-light uppercase tracking-[0.22em]">
            {t("login.merkregel")}
          </p>
        </div>
      </section>

      <section className="lijnpatroon flex flex-1 items-center justify-center px-6 py-12">
        <Formulier terug={terug ?? "/"} taal={taal} />
      </section>
      {/* Ook hier, want wie nog niet aangemeld is moet dit scherm kunnen
          lezen. `kiesTaal` vraagt bewust geen sessie; zie taal-acties.ts. */}
      <TaalKiezer actief={taal} label={t("taal.label")} />
    </main>
  );
}
