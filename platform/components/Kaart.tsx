/** Wit paneel op het beige vlak. Geen schaduw, geen kader, hoeken max 4px.
 *
 *  De klasse `paneel` is geen opmaak maar een haakje: de afdrukregels in
 *  globals.css geven elk paneel op papier een haarlijn, omdat een printer
 *  achtergronden pas op verzoek meeneemt en een wit vlak op wit papier anders
 *  onvindbaar is. Zonder zo'n haakje zou die regel op Tailwind-utilities moeten
 *  mikken, en dan breekt ze zodra hier een klasse verandert. */
export default function Kaart({
  titel,
  children,
}: {
  titel?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="paneel rounded-klein bg-wit p-6">
      {titel ? <h2 className="kapitaal-label mb-4 text-zwart">{titel}</h2> : null}
      {children}
    </section>
  );
}
