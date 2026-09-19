/**
 * Eén plek voor "welke signaalkleur hoort bij welke richting of status".
 *
 * Sinds 18 september 2026 draagt het platform kleur op een oordeel (zie de
 * noot bij de signaaltokens in globals.css). Dat oordeel komt op vier plekken
 * voor -- de briefingstatus, het verschil op een kerncijfer, het verschil in
 * de microcontext, de termen van een ontbinding -- en die vier moeten
 * dezelfde kleur bij dezelfde richting zetten, anders leert de lezer het
 * vier keer. Vandaar één tabel en geen vier.
 *
 * KLEUR KOMT ERBIJ, NOOIT IN DE PLAATS. Elke aanroeper laat de pijl, het
 * teken en het woord staan. Wie kleur niet ziet, mist niets.
 *
 * `null` (geen richting) krijgt geen kleur: een verschil van 0,0 % is geen
 * goed en geen slecht nieuws, en het mag er dus niet zo uitzien.
 */

export type Richting = "op" | "neer" | null;
export type Status = "goed" | "let_op" | "actie";

/** Tekstkleur bij een richting; leeg als er geen oordeel is. */
export function richtingKleur(richting: Richting | undefined): string {
  if (richting === "op") return "text-signaal-goed";
  if (richting === "neer") return "text-signaal-actie";
  return "";
}

/** Tekstkleur bij een briefingstatus. */
export const STATUSKLEUR: Record<Status, string> = {
  goed: "text-signaal-goed",
  let_op: "text-signaal-letop",
  actie: "text-signaal-actie",
};

/** Lijnkleur (border) bij een briefingstatus; zelfde drie tokens. */
export const STATUSLIJN: Record<Status, string> = {
  goed: "border-signaal-goed",
  let_op: "border-signaal-letop",
  actie: "border-signaal-actie",
};
