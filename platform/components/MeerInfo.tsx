/**
 * Een rustige uitklap voor toelichting die niet iedereen elke dag hoeft te
 * lezen. De kerncijfers en de onbeschikbaar-blokken blijven altijd zichtbaar
 * (harde regel 8 gaat over wat er níét staat); dit is voor de uitleg
 * eromheen: methodetekst, meetdetails, langere duiding.
 *
 * Bewust een native <details>: werkt zonder JavaScript, met toetsenbord, en
 * de open/dicht-staat hoeft nergens bewaard te worden.
 */
export default function MeerInfo({
  label,
  children,
}: {
  /** Altijd meegeven: dit onderdeel kent de taal van de lezer niet. */
  label: string;
  children: React.ReactNode;
}) {
  return (
    <details className="group mt-3 max-w-prose">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 text-sm text-zwart underline decoration-warmgrijs underline-offset-4 hover:decoration-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart [&::-webkit-details-marker]:hidden">
        <span aria-hidden className="text-xs transition-transform group-open:rotate-90">
          ▸
        </span>
        {label}
      </summary>
      <div className="mt-2 space-y-2 text-sm font-light text-zwart">
        {children}
      </div>
    </details>
  );
}
