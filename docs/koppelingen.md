# De koppelingen

_Vastgelegd 12 augustus 2026. Drie bronnen, drie totaal verschillende mechanismen. Rangorde van de opdrachtgever: Odoo eerst, Deliveroo tweede, TGTG derde. Die rangorde geldt voor de bouwvolgorde, niet voor de datakwaliteit — TGTG is toevallig de enige bron die vandaag volledig binnen is._

---

## Too Good To Go

> **Geschrapt 17 augustus 2026** op vraag van de opdrachtgever: de ingestmailbox-constructie komt er niet. Het kanaal bevriest op de geparste historiek t/m juli 2026; het handmatige pad staat in `beheerdraaiboek.md`. Onderstaand ontwerp blijft staan voor het geval de klant het later alsnog wil.

### De situatie

Er is **geen partner-API** en die komt er voor een enkele bakkerij ook niet. Wat er wel bestaat:

- **Too Good To Go Platform** is een enterprise-aanbod voor supermarktketens (Carrefour, Auchan, SPAR). Toegang via een salescontact, en het gaat over surplusbeheer, niet over de verkoopdocumenten van een marktplaatspartner
- **Deliverect** heeft een officiële TGTG-koppeling, maar die injecteert bestellingen in de kassa. Geen facturen, geen commissie, geen rekeningoverzicht. En België staat niet in de gepubliceerde regiolijst
- De bekende Python-pakketten (`tgtg`, `tgtg-python`) zijn **volledig consumentgericht**: inloggen als koper, pakketten zoeken, bestellen. Geen enkel partner- of financieel endpoint

### Waarom we niet scrapen

Drie redenen, en elk ervan volstaat op zich:

1. De voorwaarden verbieden het letterlijk: geen geautomatiseerde systemen om data te onttrekken, niet crawlen, niet scrapen, geen beveiliging omzeilen. Schending is in dezelfde voorwaarden gekoppeld aan schorsing van het account
2. Het portaal zit achter **DataDome**. Dat is geen theoretische horde: er zijn gedocumenteerde gevallen waarin wisselende IP's, apparaten en accounts allemaal geblokkeerd bleven
3. Het zou betekenen dat de klant ons haar portaalwachtwoord geeft. Dat is op zichzelf al een probleem

Het account dat op het spel staat is niet het onze maar dat van de eindklant, met een lopend commercieel contract eraan. Die afweging maken we niet voor haar.

### Wat we wél doen: TGTG stuurt het zelf op

Dit is de vondst die de koppeling oplost. TGTG verstuurt **aan het begin van elke maand automatisch een e-mail** met de verkoopcijfers, de commissie en het saldo. De bijlagen zijn per type aan of uit te zetten in **MyStore → profielicoon → Finances → "Monthly sales overview email"**:

| Aanvinken | Levert |
|---|---|
| Order Summaries | het **Verkoopoverzicht** — een regel per bestelling |
| Invoices | de **Factuur** — commissie per stuk |
| Account Statements | het **Rekeningoverzicht** — saldo en uitbetaling |

Dat is exact de drieslag die de parser al leest.

### Het ontwerp

```
TGTG  --maandelijkse e-mail met 3 bijlagen-->  mailbox van de bakkerij
                                                      |  doorstuurregel
                                                      v
                                          ingestmailbox (tgtg@...)
                                                      |  IMAP, dagelijks
                                                      v
                                    bijlagen naar data/raw/, dan de parser
```

Vier ontwerpbeslissingen:

**Doorstuurregel eerst, supportticket parallel.** Een uitgenodigd teamlid krijgt standaard de rol *Operator*, en die mag de financiële gegevens niet zien; een financiële rol voor `renarddata@asklien.ai` vergt een supportticket bij TGTG. De doorstuurregel werkt vandaag en hangt aan niemand behalve de mailbox van de bakkerij; het ticket is structureel netter omdat TGTG dan rechtstreeks aan ons adres levert en de regel kan vervallen. Beide sporen lopen: regel nu, ticket ernaast, en wint het ticket dan schrappen we de regel. _(Aangepast 12 aug: per klant één adres, `renarddata@` — zonder streepje, definitief — in plaats van een gedeelde bus.)_

**Ontdubbelen op het documentnummer** uit de bestandsnaam. Dezelfde maand kan meermaals binnenkomen, en dat mag niets veranderen.

**Volledigheidscontrole.** Per maand horen er precies drie documenten per winkel te zijn. Ontbreekt er iets na de tiende van de maand, dan een melding — niet stil blijven. De faalwijzen zijn voorspelbaar: mail in spam, de toggle staat uit, of de lay-out is gewijzigd.

**Uploadscherm als vangnet.** Niet als hoofdroute, wel omdat het gratis meekomt: dezelfde parser, en het dekt zowel een gemiste maand als een backfill. De portaal-export levert **12 maanden per keer** — zo is de huidige dump van zeven jaar ook opgebouwd, in zeven exports. Eén gemiste periode is dus met één export gerepareerd.

### Wat de klant moet doen

Eén handeling, eenmalig: in MyStore de maandelijkse e-mail aanzetten met de drie bijlagen, en een doorstuurregel instellen. Dat hoort in het vragenblok aan Lien.

### Wat nog onbekend is

Het afzenderadres en het exacte bijlageformaat van die maandelijkse mail — dat is pas te zien als de eerste binnenkomt. De filterregel wordt dus geschreven wanneer we er één hebben, niet ervoor.

---

## Odoo

De hoofdlijn ligt vast en is op 17 augustus 2026 gebouwd: XML-RPC met een API-sleutel, nachtelijk en **altijd een volledig extract, met een poortwachter op `write_date`** — één goedkope vraag aan Odoo beslist of er iets gewijzigd is; zo niet, dan stopt de run meteen. Bewust géén incrementeel extract, hoewel dat eerst het plan was: het extract aggregeert aan de bron tot dag × product × kassa, en een dag die half opnieuw wordt opgehaald en dan geüpsert overschrijft het volledige dagtotaal met een gedeeltelijk — stille corruptie (zie `beslissingen.md`, 17 aug). De ketting draait op GitHub Actions (`nachtelijke-sync.yml`; de planning staat nu bewust uit, zie `beheerdraaiboek.md`). Twee open punten uit de audit blijven gelden: de productieomgeving is geblokkeerd op een betalende licentie (G6), en het is niet bevestigd of de preprod meesynchroniseert met productie (G5, aanname A14).

---

## Deliveroo

### De data bestaat wél, en Sophie kan er zelf bij

Dit is de belangrijkste vondst van 12 augustus. De aanname was dat de historiek alleen via de accountmanagers te krijgen is. Dat klopt niet: **Partner Hub heeft een rapportagesectie** die precies levert wat we nodig hebben, gratis, zonder goedkeuringstraject.

| Bron | Hoe ver terug | Artikelniveau | Commissie | Formaat |
|---|---|---|---|---|
| **Hub → Reports → Items Sold** | 12 maanden, in blokken van max 90 dagen | ✅ categorie, artikel, aantal, prijs, subtotaal | ❌ | CSV |
| **Hub → Reports → Orders** | idem | per order | ✅ **`Deliveroo commission` en `VAT on Deliveroo commission`** | CSV |
| **Hub → Invoices** | 12 maanden, wekelijks | — | ✅ per order uitgesplitst, plus fees en rebates | PDF **en CSV** |
| Order API | **30 dagen**, hard | ✅ | ❌ | JSON |

Het Orders-rapport is voor ons het waardevolst: het is de enige bron die de **commissie per order met datum** geeft. Daarmee is de marge per kanaal te berekenen zonder facturen te parsen.

### Waarom de API het niet oplost

De Order API is een vooruitkijkende stroom met een vangnet van dertig dagen — de documentatie zegt letterlijk dat er geen orderdata ouder dan dertig dagen wordt teruggegeven. Bovendien bevat de webhook-payload **geen commissie en geen netto-uitbetaling**: alleen subtotalen, artikelregels en klantgerichte kosten. Er bestaat geen finance-, invoice- of settlement-API.

Dat verklaart meteen waarom middleware (Deliverect, Flipdish, Lightspeed) dit niet oplost: geen enkele aanbieder kan tonen wat de webhook niet bevat, en geen enkele biedt import van orders van vóór de aansluiting.

Toegang tot de API is bovendien op uitnodiging en gericht op kassaleveranciers, niet op individuele horecazaken.

### Wat dat betekent voor de planning

**Het venster van twaalf maanden schuift elke dag op.** Elke maand die verstrijkt zonder download is permanent dataverlies — die data is daarna nergens meer te halen. Dat maakt dit het meest urgente openstaande punt van het hele project, urgenter dan de marges en urgenter dan de databasekeuze.

### Het ontwerp

> **Noot 17 augustus 2026:** de ingestmailbox is geschrapt op vraag van de opdrachtgever (zelfde beslissing als bij TGTG hierboven). De wekelijkse factuurmail-route hieronder komt er dus niet; wat overblijft is de eenmalige download uit Partner Hub en het uploadscherm. Het ontwerp blijft staan voor het geval de klant het later alsnog wil.

```
Partner Hub  --eenmalig, 4 blokken van 90 dagen-->  CSV: Items Sold + Orders
                                                          |
Deliveroo  --wekelijkse factuurmail-->  ingestmailbox  ----+--> data/raw/ -> parser
                                                          |
Order API (later)  --dagelijks, 30 dagen terug-->  vooruit accumuleren
```

Drie stappen, in deze volgorde:

1. **Nu meteen de historiek redden.** Vier blokken van 90 dagen over de laatste twaalf maanden, beide rapporttypes. Dit is het enige dat een deadline heeft
2. **De wekelijkse factuurmail naar dezelfde ingestmailbox** als TGTG. E-mail is bij Deliveroo een ondersteund kanaal — er bestaat zelfs een helpartikel over facturen die niet aankomen
3. **De API is geschrapt uit het ontwerp** (beslist 12 aug). Alles wat we nodig hebben is zonder haar gedekt: historiek via de rapporten, financiën via de factuurmail, productmix via een periodieke Hub-download (het 12-maandsvenster maakt een maandelijkse of zelfs driemaandelijkse download ruim voldoende, via het uploadscherm). De API is bovendien op uitnodiging, gericht op kassaleveranciers, mist commissie en netto-uitbetaling, en zou webhook-infrastructuur vergen op een platform dat net van eigenaar wisselde. Ze komt alleen terug in beeld als de klant expliciet dagverse, volautomatische Deliveroo-productcijfers eist — dat is dan een eigen fase

### Eén ding om eerst te testen

De documentatie zegt niet of Items Sold binnen één datumbereik **per dag uitsplitst** of over de hele periode optelt. Als het aggregeert, is het rapport per kalenderdag te draaien — bewerkelijk maar triviaal. Test dat met één bereik van drie dagen vóór er iets gebouwd wordt.

### Wat niet bevestigd is

- Of Deliveroo België op verzoek verder dan twaalf maanden teruggaat. Nergens gedocumenteerd. Dat is een vraag aan de accountmanager, geen route om op te plannen
- Of er met self-billing gewerkt wordt in België
- "Netto-uitbetaling" bestaat nergens als expliciet veld. Het is af te leiden uit omzet min commissie min fees plus rebates, maar reconciliatie tegen de bankafschrift blijft nodig

Contextrisico op middellange termijn: DoorDash rondde de overname van Deliveroo af op 2 oktober 2025. Een migratie van het partnerplatform is niet aangekondigd, maar het is een reden om niet te lang op de huidige structuur te bouwen.

### Naschrift 28 augustus 2026 — de API opnieuw nagegaan, en ze blijft geen weg

Het onderzoek hierboven dateert van 12 augustus. Op 28 augustus is de API-kant opnieuw bij de bron nagegaan, en er is niets veranderd. Deliveroo biedt partners drie suites: **Order** (bestellingen in real time), **Menu** (menu's bijwerken) en **Site** (openingsuren). Alle drie zijn operationeel bedoeld. Er is **geen rapportage-, financiële, afrekenings- of historiek-API** — wat wij nodig hebben, historiek en commissie, bestaat er domweg niet in.

Dat bevestigt de beslissing van 12 augustus om de API uit het ontwerp te schrappen. De overname door DoorDash heeft daar niets aan veranderd; het contextrisico hierboven blijft staan als risico en niet als gebeurtenis.

Wat er ondertussen wél binnenkwam — twee PDF's, rechtstreeks van Deliveroo, per maand en zonder commissie — staat in `docs/vragen-aan-lien.md` (28 augustus) en in het naschrift bovenaan `docs/plan-deliveroo-parser.md`. Het onderzoek hierboven wordt daardoor niet achterhaald: de twee Partner Hub-rapporten in de tabel blijven de bron die de commissie draagt, en ze zijn op 28 augustus bij naam gevraagd.
