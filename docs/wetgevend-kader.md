# Wetgevend kader — wat het raakt, en wat bewust buiten de deur blijft

> Bureauonderzoek van 14 augustus 2026, met bronvermelding en per punt een
> zekerheidsgraad. Dit is geen juridisch advies; het is de lijst waarmee we de
> opzet van het platform toetsen en die Lien aan een jurist kan voorleggen.
> De rode draad: het platform is een **afgeleide, lezende rapportagelaag** —
> geen kassa, geen facturatie, geen boekhouding, geen klantgegevens. Bijna elk
> zwaar regime blijkt daardoor níét van toepassing, en dat is een
> ontwerpkeuze om te bewaken, geen toeval.

## 1. AVG / GDPR — het enige kader met echt werk

**Rolverdeling in het hostingmodel (vraag 40/41):** de bakkerij is
verwerkingsverantwoordelijke, asklien.ai (host) is verwerker, Supabase is
subverwerker; zolang wij productietoegang hebben, zijn ook wij (sub)verwerker.
Art. 28 AVG eist een schriftelijke verwerkersovereenkomst bakkerij↔asklien.ai
met de subverwerkers benoemd. Dit bevestigt en verscherpt wat al in vraag 41
staat. *(vastgesteld in bron)*

**De DPA met Supabase hoeft niet apart getekend te worden** — nagekeken bij de
bron op 14 augustus 2026, nadat het dashboard erover meldde. De precieze vorm
wijkt af van wat hierboven eerst stond ("asklien.ai sluit de standaard-DPA"),
en het verschil is administratief van belang:

- De DPA is een **zelfstandig document, versie 1, van kracht 1 augustus 2026**,
  dat door de Terms of Service wordt geïncorporeerd (§1(d) en §7(b)) en bij
  strijdigheid vóórgaat op de Terms.
- Aanvaarding gaat **automatisch bij gebruik** van de dienst — geen
  handtekening, geen aparte handeling. Liens organisatie heeft hem dus al
  aanvaard door het project aan te maken.
- **Gevolg voor het dossier:** er valt niets te tekenen, maar er valt wél iets
  vast te leggen. In het dossier van de eindklant hoort de verwijzing naar DPA
  v1 (1 aug 2026) met de datum waarop het project is aangemaakt. Een
  verwerkersovereenkomst waarvan niemand de versie noteerde, is bij een
  controle net zo goed als geen.
- De DPA bevat de **standaardcontractbepalingen** (Schedule 2) voor doorgifte
  buiten de EER, met modules voor zowel controller→processor als
  processor→processor. In onze keten — Renard verantwoordelijke, asklien.ai
  verwerker, Supabase subverwerker — is de **processor→processor**-module de
  toepasselijke. Iers recht, Ierse rechtbanken.
- **Subverwerkers: 30 dagen aankondiging, 5 dagen om bezwaar te maken.** Dat
  is een termijn die alleen bestaat als iemand die e-mails ook leest. Die
  meldingen gaan naar het account van Liens organisatie, niet naar ons.
  → openstaand punt, zie hieronder.

*(vastgesteld in bron: supabase.com/legal/dpa en supabase.com/terms, gelezen
14 aug 2026. De toewijzing van de processor→processor-module aan onze keten is
redenering, geen bronvaststelling.)*

**Datalekken:** melding door de verantwoordelijke binnen 72 uur aan de GBA;
de verwerker meldt "zonder onredelijke vertraging" aan de verantwoordelijke.
De keten Supabase → asklien.ai → bakkerij moet dus afgesproken zijn vóór de
livegang — één paragraaf in het onderhoudscontract. *(vastgesteld in bron)*

**Wat persoonsgegevens zijn en wat niet:** de geaggregeerde productverkoop
(datum × product × kanaal × aantal × omzet) bevat geen natuurlijke persoon en
is naar alle waarschijnlijkheid geen persoonsgegeven *(waarschijnlijk — geen
autoriteitsuitspraak over precies dit geval gevonden)*. De
**gebruikersaccounts** (namen, e-mails) zijn dat wél: de AVG is dus gewoon van
toepassing, met een kleine voetafdruk. Gevolg: accountgegevens in de
documentatie benoemen als "de enige persoonsgegevens in het systeem", en een
bewaarregel afspreken (account weg bij uitdiensttreding).

**EU-regio:** kies in Supabase een **specifieke EU-regio**; de generieke groep
"Europe" omvat ook Londen en Zürich en dat zijn geen EU-lidstaten.
**Gekozen op 14 augustus 2026: `eu-north-1` (Stockholm, Zweden)** — een
EU-lidstaat, dus aan de eis is voldaan. Een regio is na aanmaak niet te
wijzigen. *(vastgesteld in bron)*

Bronnen: [Supabase GDPR](https://supabase.com/docs/guides/security/gdpr-compliance),
[Supabase DPA](https://supabase.com/legal/dpa),
[GBA datalekken](https://www.gegevensbeschermingsautoriteit.be/melding-van-gegevenslekken).

## 2. Fiscale bewaarplicht (België): 10 jaar — maar niet voor ons

Sinds 2023 geldt 10 jaar bewaarplicht voor boeken en verantwoordingsstukken
(btw én inkomstenbelastingen). Die plicht rust op de **bakkerij** en betreft
de **bronstukken** — óók de Deliveroo-rapporten en TGTG-afrekeningen, want dat
zijn verantwoordingsstukken van omzet. Het platform is zelf geen wettelijk
boek of stuk en hoeft geen 10 jaar te garanderen, **op voorwaarde dat het
nooit het enige archief wordt**. *(regel vastgesteld in bron; de kwalificatie
van het platform is redenering, geen bronvaststelling)*

Ontwerpgevolgen, allebei al staand beleid en nu met reden vastgelegd
(bijgesteld 18 aug: de ingestmailbox is op 17 aug geschrapt, en dat maakt dit
argument alleen maar sterker — er bestaat bij ons nu níéts dat op een archief
lijkt):
- "Alles herbouwbaar uit de bron" blijft; het platform vervangt de bron-CSV's
  en de TGTG-documenten niet.
- **Aan de bakkerij bevestigen dat zíj de bronbestanden 10 jaar bewaren**
  (vraag 52). De TGTG-stukken hangen sinds het schrappen van de mailbox
  volledig aan MyStore, het portaal van TGTG zelf — en dat is een dienst van
  een derde, geen wettelijk archief van de bakkerij. Zij moet de documenten
  dus zelf veiligstellen; noch het platform, noch MyStore vervult die plicht
  voor haar.

België kent geen certificeringsregime voor boekhoudsoftware; gereguleerd zijn
alleen kassasystemen (GKS) en facturatie (Peppol). Een tool die geen
boekingen maakt, geen facturen uitreikt en geen verkoop registreert valt
buiten beide. Het platform nooit "de boekhouding" noemen, in geen contract en
op geen scherm — `scope.md` sluit dat al uit.

Bron: [CBN-advies bewaring](https://www.cbn-cnc.be/nl/adviezen/bewaring-van-boeken-en-verantwoordingsstukken).

## 3. GKS / witte kassa (en GKS 2.0): plicht van de kassa, niet van ons

GKS is verplicht vanaf € 25.000 omzet uit **verbruik ter plaatse**; voor een
bakkerij telt alleen de verbruikszaal, niet de toonbank. GKS 2.0 (realtime
doorsturen naar FOD Financiën) wordt verplicht voor nieuwe plichtigen vanaf
1 juli 2026, bestaande migreren 2027–2029. Het regime certificeert
**kassasystemen**; een tool die achteraf geaggregeerde kassadata leest valt er
niet onder. *(vastgesteld in bron)*

Wél een afhankelijkheid: als Renard een verbruikszaal boven de drempel heeft,
migreert hun kassa ooit naar GKS 2.0 en kan het Odoo-exportformaat wijzigen.
→ feitenvraag 53 aan Lien; voor ons alleen iets om te weten, niets om te bouwen.

Bron: [geregistreerdkassasysteem.be, richtlijnen met bakkersvoorbeeld](https://www.geregistreerdkassasysteem.be/nl/ondernemer/voor-wie/richtlijnen).

## 4. E-facturatie / Peppol (sinds 1 januari 2026): niet ons vak

Binnenlandse B2B-facturen moeten sinds 1 januari 2026 gestructureerd
elektronisch (Peppol). Het platform reikt geen facturen uit en ontvangt er
geen — de plicht raakt de bakkerij (haar pakket) en **asklien.ai zelf** (het
onderhoudsabonnement moet via Peppol gefactureerd). Ontwerpgevolg is een
scope-bewaker: **geen facturatiefunctie inbouwen**, anders komt dit hele
regime mee naar binnen. *(vastgesteld in bron)*

Bron: [SBB over e-facturatie 2026](https://www.sbb.be/nl/magazine/vanaf-1-januari-2026-wordt-elektronische-facturatie-verplicht).

## 5. EU AI Act: de prognose valt erbuiten — en zo houden we het

De Commissie-richtsnoeren (feb. 2025) sluiten eenvoudige statistische
schatters uit van het begrip "AI-systeem"; onze weekdagmediaan met
niveauschaling en vakantiecorrectie is precies dat. Zelfs mét kwalificatie:
omzetprognoses staan niet in Annex III (hoog risico = besluiten over
personen) en vallen niet onder de transparantieplichten van art. 50. Na de
Digital Omnibus (in werking 27 juli 2026) zijn de hoog-risicodeadlines
bovendien verschoven naar eind 2027/2028 — hier hoe dan ook niet relevant.
*(timing vastgesteld in bron; kwalificatie waarschijnlijk)*

Ontwerpgevolgen: het model in alle teksten **statistisch** blijven noemen
(niet "AI" — de kwalificatie hangt mede aan wat je ervan zegt), en de eigen
lat (harde regel 7: geen voorspelling zonder backtest) is al strenger dan wat
de wet vraagt. Komt er in fase 2+ een zwaarder model (gradient boosting), dan
verandert de conclusie niet zolang het niets over personen beslist.

Bron: [Commissie-richtsnoeren definitie AI-systeem](https://ai-act-service-desk.ec.europa.eu/sites/default/files/2025-08/commission_guidelines_on_the_definition_of_an_artificial_intelligence_system_established_by_regulation_eu_20241689_ai_actenglish_nf2skcqfrtjdfggjavcodopcwz4_112455.PDF),
[Gibson Dunn over de omnibus-deadlines](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/).

## 6. Scraping en de partnerportalen: onze download/CSV-route is de juiste

Het Ryanair-arrest (C-30/14) laat platforms scraping contractueel verbieden,
ook op onbeschermde data; schending is wanprestatie met het account van de
**bakkerij** als inzet. De gekozen routes (TGTG-documenten die de bakkerij
zelf uit MyStore haalt — de maandmail-constructie is op 17 aug geschrapt —,
Deliveroo-CSV door Sophie zelf) zijn kanalen die de platforms aanbieden —
geen risico. De
P2B-verordening (2019/1150, art. 9) geeft de bakkerij bovendien recht op een
beschrijving van haar datatoegang; dat is de juridische kapstok als er later
méér automatisering gewenst is. Dit bevestigt de beslissing van 12 augustus
(vraag 35) met de juridische onderbouwing erbij. *(vastgesteld in bron; de
actuele ToS-teksten van TGTG/Deliveroo zelf zijn niet gelezen)*

## 7. NIS2 / cyberwet: niet van toepassing, wél een gratis checklist

De Belgische NIS2-wet grijpt pas vanaf 50 werknemers of € 10 mln omzet in een
gelijste sector; asklien.ai valt daar ruim buiten. Supabase valt er als
cloudaanbieder mogelijk wél onder — hún plicht. Vrijwillig passend bij deze
schaal: de **CyberFundamentals "Small"** van het CCB als checklist voor de
hostingopzet. *(drempels vastgesteld in bron; detailuitzonderingen niet
artikelsgewijs geverifieerd)*

Bron: [CCB over NIS2](https://ccb.belgium.be/nl/nis2).

## 8. EU Data Act: van toepassing, en gunstig — mits één contractzin

Sinds 12 september 2025 geldt de Data Act ook voor SaaS ("data processing
services"): wisselrecht, opzegtermijn max. 2 maanden, vanaf 2027 geen
switchingkosten. Maar **art. 31** zondert maatwerkdiensten voor één klant
uit — precies dit platform. Dan vervallen de zwaarste plichten en blijft
over: export in een gestructureerd machineleesbaar formaat (het genummerde
JSON-contract en "herbouwbaar uit bron" dekken dat al) én de plicht om de
klant **vóór contractsluiting** te melden welke verplichtingen niet gelden.
→ die informatieclausule moet in Liens onderhoudscontract (S10/vraag 41).
*(regel vastgesteld in bron; kwalificatie als maatwerk waarschijnlijk)*

Bron: [Data Act art. 31](https://www.eu-data-act.com/Data_Act_Article_31.html).

## 9. Bewust niet relevant — en waarom dat zo moet blijven

- **Loongegevens/sociale documenten:** het platform bevat geen loon- of
  prestatiegegeven; namen/e-mails zijn alleen login-identiteit. Zolang er
  nooit personeelskost **per persoon** in de margeberekening komt (het
  kostenmodel rekent op groepsniveau, in percentages), blijft dit domein
  buiten beeld.
- **Voedseletikettering (1169/2011):** richt zich op informatie aan
  consumenten op het verkooppunt; een intern financieel platform heeft er
  geen raakvlak mee. (De FGBB/Alimento-opleidingen hierover zijn voor de
  bakkerij zelf relevant, niet voor deze tool.)
- **Belgische B2B-wet (onrechtmatige bedingen):** raakt het
  onderhoudscontract van Lien, niet de software. Niet verder onderzocht.

## Samengevat: zes acties, waarvan één intussen gedaan

| # | Actie | Van wie | Waar belegd |
|---|---|---|---|
| 1 | Verwerkersovereenkomst bakkerij↔asklien.ai (subverwerkers benoemd, datalek-keten 72u, bewaarregel accounts) | Lien | was al vraag 41; aangescherpt |
| ~~2~~ | ~~Specifieke EU-regio kiezen bij S2~~ ✅ **14 aug: `eu-north-1` (Stockholm)** | | vervallen |
| 5 | Supabase-DPA v1 (1 aug 2026) mét aanmaakdatum project vastleggen in het dossier van de eindklant — tekenen hoeft niet, aanvaarding gaat automatisch bij gebruik | Lien | vervangt de oude lezing "DPA sluiten" |
| 6 | Iemand moet Supabase' subverwerker-aankondigingen lezen: 30 dagen vooraf, 5 dagen bezwaartermijn. Die mail gaat naar Liens organisatie, niet naar ons | Lien | nieuw, 14 aug |
| 3 | Data Act-informatieclausule (art. 31) in het onderhoudscontract | Lien | vraag 41/S10 |
| 4 | Bevestiging dat de bakkerij bronbestanden 10 jaar zelf bewaart + verbruikszaal-vraag (GKS) | Sophie via Lien | vragen 52 en 53 |

En drie dingen die we **niet** gaan bouwen, met de wet als extra reden naast
de scope: geen facturatie (Peppol), geen boekingen (bewaarplicht/controle),
geen kassafunctie (GKS). Elk daarvan zou een regime binnentrekken dat er nu
netjes buiten blijft.
