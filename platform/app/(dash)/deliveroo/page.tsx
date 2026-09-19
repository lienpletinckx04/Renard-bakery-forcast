import { cookies } from "next/headers.js";

import Kaart from "@/components/Kaart";
import MeerInfo from "@/components/MeerInfo";
import Onbeschikbaar from "@/components/Onbeschikbaar";
import PaginaKop from "@/components/PaginaKop";
import { COOKIE, lees } from "@/lib/auth";
import { contractBron } from "@/lib/contract-bron";
import { ACCEPT, MAX_MB } from "@/lib/deliveroo-upload";
import {
  laadUploads,
  LIMIET,
  type Upload,
  type VerwerktStatus,
} from "@/lib/deliveroo-upload-db";
import { datumMetTijd, geheelGetal } from "@/lib/format";
import { huidigeTaal } from "@/lib/laadContract";
import { maakT, type Sleutel, type T, type Taal } from "@/lib/taal";

import UploadFormulier from "./UploadFormulier";

export const dynamic = "force-dynamic";

/** De zin die bij een stand hoort; "nog niet verwerkt" is het ontbreken ervan. */
const STAND: Record<VerwerktStatus, Sleutel> = {
  gelukt: "deliveroo.verwerktGelukt",
  mislukt: "deliveroo.verwerktMislukt",
};

function verwerkingsTekst(rij: Upload, t: T, taal: Taal): string {
  if (rij.verwerkt_status === null) return t("deliveroo.nogNietVerwerkt");
  return t(STAND[rij.verwerkt_status], {
    datum: rij.verwerkt_op === null ? "" : datumMetTijd(rij.verwerkt_op, taal),
  });
}

/**
 * Het scherm Deliveroo-import: hier legt een beheerder een export neer.
 *
 * WAT DIT SCHERM BEWUST NIET DOET. Het opent het bestand niet. Geen voorbeeld,
 * geen rijtelling, geen controle op kolomnamen — de bytes gaan ongewijzigd naar
 * de database en de Python-inlaadlaag haalt ze er 's nachts uit. Parsen hoort
 * op één plaats thuis, en dat is die laag; een tweede lezer hier zou een tweede
 * waarheid worden zodra de export één keer van vorm verandert. Harde regel 4
 * zegt hetzelfde in het klein: de UI rekent nooit.
 *
 * DAAROM BELOOFT HET SCHERM OOK GEEN RESULTAAT. Na het opladen staat de stand
 * op "nog niet verwerkt", en dat blijft zo tot de nachtelijke verwerking. Dat
 * staat er met zoveel woorden bij: een scherm dat na een geslaagde handeling
 * zwijgt over wat er níét gebeurd is, laat de lezer denken dat de cijfers al
 * bijgewerkt zijn.
 *
 * Is de database niet leesbaar, dan toont het scherm GEEN lege lijst: "er is
 * nog niets opgeladen" is een uitspraak, en die kunnen we op dat moment niet
 * doen. Het vak zegt wat er aan de hand is (harde regel 8).
 */
export default async function DeliverooPagina() {
  const taal = await huidigeTaal();
  const t = maakT(taal);
  const [uploads, sessie] = await Promise.all([
    laadUploads(),
    lees((await cookies()).get(COOKIE)?.value),
  ]);
  const magBewerken = sessie?.rol === "beheerder";

  const kop = (
    <PaginaKop
      titel={t("deliveroo.titel")}
      ondertitel={t("deliveroo.ondertitel")}
    />
  );

  if (uploads === null) {
    const reden =
      contractBron(process.env) === "db"
        ? t("deliveroo.dbOnbereikbaar")
        : t("deliveroo.alleenDb");
    return (
      <div className="space-y-6" data-buiten-rapport>
        {kop}
        <Onbeschikbaar t={t} titel={t("deliveroo.titel")} reden={reden} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-buiten-rapport>
      {kop}

      <Kaart>
        <MeerInfo label={t("deliveroo.hoewerkt")}>
          <p>{t("deliveroo.uitlegOpladen", { max: geheelGetal(MAX_MB) })}</p>
          <p className="mt-2">{t("deliveroo.uitlegMeerdere")}</p>
          <p className="mt-2">{t("deliveroo.uitlegNachtelijk")}</p>
          <p className="mt-2">{t("deliveroo.uitlegNietGelezen")}</p>
        </MeerInfo>
        {magBewerken ? (
          <div className="mt-4">
            <UploadFormulier accept={ACCEPT} taal={taal} />
          </div>
        ) : (
          <p className="mt-4 max-w-prose text-sm font-light text-zwart">
            {t("deliveroo.alleenBeheerderVak")}
          </p>
        )}
      </Kaart>

      <Kaart titel={t("deliveroo.lijstTitel")}>
        <p className="max-w-prose text-sm font-light text-zwart">
          {t("deliveroo.lijstUitleg", { max: geheelGetal(LIMIET) })}
        </p>
        {uploads.length === 0 ? (
          <p className="mt-4 text-sm font-light text-zwart">
            {t("deliveroo.geenBestanden")}
          </p>
        ) : (
          <>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[34rem] text-sm">
                <caption className="sr-only">
                  {t("deliveroo.lijstTitel")}
                </caption>
                <thead>
                  <tr className="border-b border-warmgrijs text-left">
                    <th scope="col" className="py-2 pr-4 font-medium text-zwart">
                      {t("deliveroo.kolBestand")}
                    </th>
                    <th scope="col" className="py-2 pr-4 font-medium text-zwart">
                      {t("deliveroo.kolOpgeladen")}
                    </th>
                    <th scope="col" className="py-2 pr-4 font-medium text-zwart">
                      {t("deliveroo.kolOmvang")}
                    </th>
                    <th scope="col" className="py-2 font-medium text-zwart">
                      {t("deliveroo.kolVerwerking")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map((rij) => (
                    <tr key={rij.upload_id} className="border-b border-beige">
                      <th
                        scope="row"
                        className="py-2 pr-4 text-left font-normal text-zwart"
                      >
                        {rij.bestandsnaam}
                      </th>
                      <td className="py-2 pr-4 font-light text-zwart">
                        {datumMetTijd(rij.geladen_op, taal)}
                        {rij.geladen_door === "" ? null : (
                          <span className="block text-xs">
                            {t("deliveroo.doorWie", {
                              gebruiker: rij.geladen_door,
                            })}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 font-light text-zwart">
                        {t("deliveroo.bytes", {
                          aantal: geheelGetal(rij.bytes),
                        })}
                      </td>
                      <td className="py-2 text-zwart">
                        {verwerkingsTekst(rij, t, taal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 max-w-prose text-sm font-light text-zwart">
              {t("deliveroo.verwerktMisluktUitleg")}
            </p>
          </>
        )}
      </Kaart>
    </div>
  );
}
