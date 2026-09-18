@AGENTS.md

# Platformregels (de kern van CLAUDE.md en de huisstijl, hier bij de hand)

- **De UI rekent nooit.** Elk cijfer op een scherm komt uit de berekeningslaag via het contract (`platform/contract/`, gelezen door `lib/contract.ts`). Ook niet tellen, ook niet sommeren: ontbreekt een getal, dan hoort het in het contract, niet in een component.
- **Alle cijfers staan in zwart.** Kleur draagt nooit betekenis — richting komt uit het teken en een pijl. De enige uitzondering zijn de vaste bordeaux vlakken (cijfer wit, label beige), die nooit meeverhuizen met goed of slecht nieuws; zie `.claude/skills/huisstijl/SKILL.md`.
- **Geen hardgecodeerde schermtekst buiten `lib/taal.ts`.** Het platform is tweetalig (NL/FR); de wacht `tests/geen-harde-tekst.test.ts` toetst dit en faalt op een literal in een component.
- **Geen grafiek- of componentbibliotheek erbij.** Grafieken zijn inline SVG; de huisstijl ligt vast en een bibliotheek levert vooral een gevecht met haar standaardkleuren op.
- **Tests draaien met `npm test` en `npx tsc --noEmit`** (samen ook via `make test-ui` vanaf de repowortel). Beide horen groen te zijn vóór een commit.
