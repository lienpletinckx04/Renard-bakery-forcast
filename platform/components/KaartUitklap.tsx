/**
 * Een kaart die in- en uitklapt. Verder identiek aan `Kaart`.
 *
 * WAAROM DIT NAAST Kaart BESTAAT EN NIET IN Kaart ZELF
 *
 * De huisstijl kent een rangorde van blokken (briefing > onbeschikbaar >
 * kaart > toelichting), en die loopt over gewicht, witruimte en lijnen. Een
 * uitklapbare kaart mag daarin niet verschuiven: het is dezelfde kaart, met
 * dezelfde `.kapitaal-label`-kop en dezelfde `p-6`, alleen kan de inhoud dicht.
 * Vandaar één component naast `Kaart` in plaats van een vlag erin — dan blijft
 * bij het lezen van een scherm meteen zichtbaar wát er kan inklappen.
 *
 * WAT ER NOOIT IN MAG
 *
 * Kerncijfers en onbeschikbaar-vakken. Dat er iets ontbreekt is precies wat
 * zichtbaar moet blijven (harde regel 8, en de toegankelijkheidsregel in de
 * huisstijl-skill zegt het met zoveel woorden). Deze kaart is voor wat eronder
 * ligt: verantwoording, methode, detailtabellen — dingen die je wílt kunnen
 * nalezen maar niet elke dag hoeft te zien.
 *
 * DE SAMENVATTING IN DE KOP
 *
 * `samenvatting` staat naast de titel en blijft dus staan als de kaart dicht
 * is. Dat is geen versiering maar de reden dat de modelkaart überhaupt dicht
 * mág: harde regel 7 zegt dat een voorspelling zonder gemeten fout een mening
 * is, dus de gemeten afwijking hoort niet achter een klik te verdwijnen. Dicht
 * geklapt staat ze in de kop; open staat de hele verantwoording eronder.
 *
 * Native `<details>`: werkt zonder JavaScript, met toetsenbord, en de
 * open/dicht-staat hoeft nergens bewaard te worden. Bij het afdrukken opent
 * globals.css ze allemaal — een rapport op papier kan niet uitklappen.
 */
export default function KaartUitklap({
  titel,
  samenvatting,
  standaardOpen = false,
  children,
}: {
  /** Altijd meegeven: dit onderdeel kent de taal van de lezer niet. */
  titel: string;
  /** Blijft zichtbaar als de kaart dicht is. Kort houden — één cijfer of één
   *  korte zin; de kop is geen tweede alinea. */
  samenvatting?: string;
  /** Open bij het laden. Voor blokken die je meestal wél wil zien maar soms
   *  wil wegklappen; standaard dicht. */
  standaardOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="paneel rounded-klein bg-wit p-6">
      <details className="group" open={standaardOpen}>
        {/* `list-none` plus de webkit-regel: de eigen driehoek van de browser
            wijkt per platform af en botst met het rustige beeld. De ▸ hieronder
            is dezelfde als in MeerInfo, zodat "dit klapt open" er op het hele
            platform hetzelfde uitziet. */}
        {/* `uitklap-kop` is geen opmaak maar een haakje voor de afdrukregels:
            globals.css verbergt op papier elke <summary> (dat is de klikregel
            van een toelichting, en die is dan ruis) — behálve deze, want hier
            is de summary de KOP van het blok. Zonder dat haakje verliest elk
            uitklapbaar paneel zijn titel in de PDF. */}
        <summary className="uitklap-kop flex cursor-pointer list-none flex-wrap items-baseline gap-x-3 gap-y-1 rounded-klein focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart [&::-webkit-details-marker]:hidden">
          <span className="kapitaal-label inline-flex items-baseline gap-2 text-zwart">
            <span
              aria-hidden="true"
              className="text-xs transition-transform group-open:rotate-90"
            >
              ▸
            </span>
            {titel}
          </span>
          {/* Zwart, zoals elk cijfer op dit platform, en licht van gewicht
              zodat de titel de kop blijft dragen. */}
          {samenvatting ? (
            <span className="text-sm font-light text-zwart">{samenvatting}</span>
          ) : null}
        </summary>
        <div className="mt-4">{children}</div>
      </details>
    </section>
  );
}
