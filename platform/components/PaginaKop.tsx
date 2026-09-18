/**
 * De kop van elk scherm: wijd gespatieerde kapitalen in bordeaux, met een
 * dunne lijn eronder — het typografische register van het woordmerk, niet
 * de vette paginatitel van een dashboardsjabloon. De ondertitel is gewone
 * tekst en draagt de nuance ("laatste 30 gemeten open dagen").
 */
export default function PaginaKop({
  titel,
  ondertitel,
}: {
  titel: string;
  ondertitel?: string;
}) {
  return (
    <header className="border-b border-warmgrijs pb-4">
      <h1 className="kapitaal-kop text-bordeaux">{titel}</h1>
      {ondertitel ? (
        <p className="mt-1 max-w-prose text-sm font-light text-zwart">{ondertitel}</p>
      ) : null}
    </header>
  );
}
