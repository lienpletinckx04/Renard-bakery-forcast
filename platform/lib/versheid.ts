// Relatief geïmporteerd, niet via "@/": deze module wordt ook door de
// testrunner van node geladen, en die kent de padalias van Next niet.
import { datumKort, datumMetTijd } from "./format";
import { maakT, type Taal } from "./taal";

/**
 * De versheid van de cijfers, in woorden.
 *
 * De voettekst zei tot nu toe alleen "Bijgewerkt op <bijgewerkt_op>". Dat is
 * het moment waarop het contract gebouwd is, niet de recentheid van de data:
 * met een jongste verkoopdag van 31 juli en een contract van 12 augustus
 * scheelt dat twaalf dagen, en de lezer las het als versheid. Daarom staan er
 * twee uitspraken, en zeggen ze allebei wát ze betekenen:
 *
 *   Cijfers tot en met 31 jul 2026 · verwerkt op 12 aug 2026, 21:53
 *
 * Er wordt hier niets gerekend: geen verschil in dagen, geen "12 dagen oud".
 * Twee datums, uitgeschreven, en de lezer trekt zelf de conclusie.
 */
export type Versheid = {
  /** Tot waar de cijfers lopen, of waarom dat onbekend is. */
  cijfers: string;
  /** Wanneer ze verwerkt zijn. */
  verwerkt: string;
};

export function versheid(
  bijgewerkt_op: string,
  /**
   * Null wanneer er geen gemeten open winkeldag is. Undefined kan er in de
   * praktijk ook staan, namelijk bij een contract van vóór dit veld; dat is
   * hetzelfde geval en krijgt dezelfde behandeling.
   */
  gemeten_tot: string | null | undefined,
  taal: Taal = "nl",
): Versheid {
  const t = maakT(taal);
  return {
    cijfers: gemeten_tot
      ? t("versheid.cijfersTot", { datum: datumKort(gemeten_tot, taal) })
      : t("versheid.onbekend"),
    verwerkt: t("versheid.verwerkt", {
      datum: datumMetTijd(bijgewerkt_op, taal),
    }),
  };
}
