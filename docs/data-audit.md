# Data-audit, dag 1

> Dit is het belangrijkste document van fase 1. Het beantwoordt één vraag: **draagt deze data een voorspelmodel, ja of nee.**
>
> Status: **INGEVULD 7 augustus 2026**, op basis van directe XML-RPC-bevraging van de Odoo-preprod (`renard_bakery_19`, Odoo 19.0+e). Alle cijfers zijn gemeten, niet geschat. Reproduceerbaar met `python3 scripts/odoo_audit.py`.

---

## Samenvatting in vier zinnen

De verkoopdata is beter dan gehoopt: negentien volle maanden, tot op de dag actueel, echte productnamen, 1,56 miljoen bonregels op 331 producten. Daar kan een voorspelmodel op.

Maar drie van de vijf dingen die dit project onderscheiden, staan **niet** in Odoo: er is geen filiaaldimensie, er is geen kanaal (Deliveroo en TGTG bestaan hier niet), en er zijn vrijwel geen kostprijzen. Zonder die drie is de beslislaag met marges per kanaal, de scherpste hoek van dit project, niet te bouwen op Odoo alleen.

Dat is geen slecht nieuws. Het is precies het bewijs dat dit project geen duplicaat is van wat Odoo al toont.

---

## Blok A. Toegang

| Vraag | Antwoord | Oordeel |
|---|---|---|
| Werkende login of API-toegang tot Odoo? | Ja, preprod. XML-RPC met API-sleutel, uid 3759, Odoo 19.0+e | **GROEN** |
| Welke rechten? | Lezen op pos.*, sale.*, product.*, stock.*, account.move. Voldoende. | GROEN |
| Volledige export of live koppeling? | Live koppeling op preprod. **Productie is geblokkeerd**: vereist een extra betalende Odoo-licentie, goed te keuren door de eindklant (mail Antoine Ludovico, 7 aug 15u24). | **AMBER** |
| Technische contactpersoon | Antoine Ludovico, Idealis Consulting (`alu@idealisconsulting.com`). Ali Ozdomurcuk is de ontwikkelaar op Renard. | GROEN |
| Deliveroo: export of API? | Nog niets ontvangen. Zit **niet** in Odoo. | **ROOD** |
| Too Good To Go: export? | Nog niets ontvangen. Zit **niet** in Odoo. | **ROOD** |

**Vaststelling over de preprod.** De preprod is geen lege testbak: hij bevat de reële historiek tot en met vandaag. Bouwen kan dus meteen. Twee waarschuwingen. Ten eerste is deze omgeving op 7 augustus al één keer herbouwd, waarbij het gebruikersaccount verdween. Idealis heeft niet bevestigd of dat periodiek gebeurt. Ten tweede is opleveren op preprod geen oplevering: artikel 4 vraagt een **operationele** koppeling, en dat is productie.

---

## Blok B. Granulariteit

| Vraag | Antwoord | Oordeel |
|---|---|---|
| Eén rij per bon, per bonregel of per dagtotaal? | **Per bonregel.** 1.556.770 regels op 678.309 kassabonnen. | GROEN |
| Product identificeerbaar per stuk (SKU)? | Ja, `product_id` met stabiele id. 331 producten met verkoop, 395 in de catalogus, 33 categorieën. | GROEN |
| Filiaal identificeerbaar? | **Nee.** Eén `res.company` (Renard Foods BV), één `stock.warehouse` (Renard Bakery), drie `pos.config` (Kassa 1, 2, 3). Alle drie hangen aan hetzelfde magazijn. | **ROOD, zie hieronder** |
| Tijdstip beschikbaar? | Ja, `date_order` bevat het uur. | GROEN, bonus |
| Kanaal herkenbaar in de rij? | **Nee.** `source` = `pos` voor alle 678.309 orders. Geen enkel Deliveroo- of TGTG-spoor. | **ROOD** |

**Het filiaalprobleem.** Er zijn drie kassa's met een vergelijkbaar volume:

| Kassa | Bonnen | Omzet |
|---|---|---|
| Kassa 1 | 219.825 | € 2.501.378 |
| Kassa 2 | 197.409 | € 2.069.786 |
| Kassa 3 | 261.075 | € 2.576.217 |

Drie kassa's met elk ruwweg een derde van de omzet kan twee dingen betekenen: drie registers in één winkel, of drie winkels met elk één register. De inrichting van Odoo zegt het eerste (één magazijn, één vennootschap), het gesprek zei twee vestigingen. **Dit moet bevestigd worden vóór het datamodel vastligt**, want het bepaalt of `filiaal_id` een echte dimensie is of een fictie. Als de kassa's registers zijn binnen één winkel, is de baklijst één lijst en geen drie, en vervalt het argument "ontworpen zodat vestiging drie erin schuift" tot er een tweede winkel in Odoo staat.

**Dubbele productnamen.** `Cappuccino` en `Sandwich` bestaan elk twee keer als verschillend product-id, met substantieel volume op beide (Sandwich: 84.990 en 53.361). Nooit op naam groeperen, altijd op id, en de twee paren apart bekijken op hernoeming of splitsing.

---

## Blok C. Historiek

| Vraag | Antwoord | Oordeel |
|---|---|---|
| Eerste en laatste datum? | 19 sep 2024 tot 7 aug 2026 | |
| Bruikbare historiek? | **Januari 2025 tot juli 2026 = 19 volle maanden.** Sep tot dec 2024 bevat 11 orders voor € 629 in totaal: implementatie-ruis, niet meetellen. | **GROEN** |
| Volledige jaarcyclus? | Ja, met overlap. Jan tot jul bestaat twee keer, dus jaar-op-jaar vergelijken kan. | GROEN |
| Breuken? | De start van de reeks is de Odoo-ingebruikname, geen bedrijfsbreuk. Geen filiaalopening of -sluiting zichtbaar. | GROEN |
| Uitzonderlijke periode? | Geen corona in bereik. Wel jaarlijkse zomersluiting, zie blok D. | GROEN |

**Omzet per maand** (kassa, incl. btw zoals geregistreerd):

| Maand | Dagen | Bonnen | Omzet | | Maand | Dagen | Bonnen | Omzet |
|---|---|---|---|---|---|---|---|---|
| 2025-01 | 30 | 37.434 | € 449.855 | | 2026-01 | 31 | 40.697 | € 514.186 |
| 2025-02 | 28 | 35.874 | € 363.059 | | 2026-02 | 28 | 38.357 | € 402.709 |
| 2025-03 | 31 | 40.449 | € 413.006 | | 2026-03 | 31 | 43.499 | € 451.889 |
| 2025-04 | 23 | 28.364 | € 289.221 | | 2026-04 | 30 | 40.447 | € 418.482 |
| 2025-05 | 31 | 37.917 | € 395.082 | | 2026-05 | 31 | 39.039 | € 420.771 |
| 2025-06 | 30 | 36.001 | € 370.577 | | 2026-06 | 30 | 37.729 | € 371.715 |
| 2025-07 | 26 | 29.075 | € 287.309 | | 2026-07 | 31 | 35.486 | € 350.744 |
| 2025-08 | **7** | 8.632 | € 89.789 | | 2026-08 | **3** | 11 | € 75 |
| 2025-09 | 30 | 39.073 | € 384.114 | | | | | |
| 2025-10 | 31 | 41.315 | € 417.989 | | | | | |
| 2025-11 | 30 | 39.544 | € 421.452 | | | | | |
| 2025-12 | 22 | 29.355 | € 334.729 | | | | | |

Totaal gemeten: **€ 7.147.381 over 539 verkoopdagen.** Jaar-op-jaar groeit januari tot juli met ongeveer 8 procent in omzet bij een licht dalend bonaantal, dus de gemiddelde bon stijgt. Dat is prijszetting of assortimentsverschuiving, en het is relevant: een model dat op stuks traint, mag niet op euro's beoordeeld worden zonder dat effect te scheiden.

---

## Blok D. Volledigheid

| Vraag | Antwoord | Oordeel |
|---|---|---|
| Ontbrekende dagen? | 149 van 688 kalenderdagen (21,7%) hebben geen enkele bon. | **AMBER** |
| Verdeling over weekdagen? | Vlak: 20 tot 23 ontbrekende dagen per weekdag. | zie hieronder |
| Sluitingsdagen als nul of als afwezige rij? | **Als afwezige rij.** Er staat geen nulregistratie. | **AMBER** |
| Negatieve aantallen? | Nul producten met netto negatief volume. Retours zitten niet als correctie in de data. | GROEN |
| Duplicaten? | Geen aanwijzing op productniveau. Te hertoetsen op bonregelniveau bij de eerste load. | GROEN |

**Wat die 149 dagen zijn.** Ze zijn niet willekeurig en ze zijn geen wekelijkse sluitingsdag: de spreiding over de weekdagen is vlak (20 tot 23 per dag), wat een vaste sluitingsdag zou uitsluiten. Ze klonteren:

- **augustus 2025: 24 van de 31 dagen leeg**
- **augustus 2026: 1 tot en met 6 leeg, en 7 augustus staat op € 75**
- 28 tot 31 december 2025
- verspreide dagen in april en juli 2025

Twee augustussen op rij vrijwel volledig leeg is geen datafout, dat is een **jaarlijkse zomersluiting**. Dezelfde conclusie geldt voor de dagen tussen Kerst en Nieuwjaar. Dat betekent ook dat de bakkerij op dit moment vermoedelijk gesloten is, wat verklaart waarom er deze week geen verse verkopen binnenkomen.

**Waarom dit ertoe doet.** Een afwezige rij en een nul betekenen niet hetzelfde. Als de loader ontbrekende dagen als nulvraag inleest, leert het model dat augustus een instortende maand is en dat de eerste week van januari halveert. De correcte behandeling is: sluitingsdagen markeren als *geen meting*, uit de trainingsset houden, en in de baklijst overslaan. Dat vereist een bevestigde sluitingskalender, niet een gok uit de data. Zie `aannames.md` A6.

---

## Blok E. Gecensureerde vraag

| Vraag | Antwoord | Waarde |
|---|---|---|
| Wordt geregistreerd hoeveel er gebakken is? | **Nee.** `mrp.production` = 0 records. | ontbreekt |
| Wordt geregistreerd hoeveel er overbleef? | **Nee.** `stock.scrap` = 0 records. | ontbreekt |
| Tijdstip van de laatste verkoop per product? | **Ja**, `date_order` bevat het uur. Afleidbaar. | zilver |
| TGTG-aantallen per dag? | Niet in Odoo. Afhankelijk van de export. | zilver, pending |
| Is er niets van dit alles? | Bijna niets. | **ROOD** |

**Dit is het zwaarste blok en het valt negatief uit.** Er is 326.434 keer een voorraadbeweging geregistreerd, maar geen enkele productieorder en geen enkele afvalregistratie. Er is dus **geen enkele meting van het aanbod**. Wat we zien is uitsluitend wat verkocht is.

Voor een bakkerij is dat een echt probleem en geen formaliteit. Als de croissants om tien uur op zijn, meet de kassa de rekcapaciteit en niet de vraag. Een model dat daarop traint, voorspelt structureel te laag, waarop er minder gebakken wordt, waarop de meting het model bevestigt. Dat is een neerwaartse spiraal die er in de cijfers uitziet als een goed presterend model.

**Wat er wel kan.** Het uur van de laatste verkoop per product per dag is beschikbaar en is een bruikbare uitverkoop-proxy: een product dat structureel om elf uur zijn laatste verkoop heeft en daarna niets, is vrijwel zeker uitverkocht. Dat is geen vervanging voor restaantallen, wel een detectiemechanisme om de censurering zichtbaar te maken in plaats van te negeren. Dat hoort in het eindrapport, met de aanbeveling om restaantallen te beginnen registreren. Dat advies heeft blijvende waarde ook nadat dit project afloopt.

---

## Blok F. Kanalen en marges

| Vraag | Antwoord |
|---|---|
| Aandeel winkel / Deliveroo / TGTG? | **100 procent winkel** in Odoo. De andere twee kanalen bestaan hier niet. |
| Kostprijs of brutomarge per product? | **3 van de 395 producten hebben een `standard_price` groter dan nul. Eén procent.** |
| Marge per productgroep aanvaardbaar? | Zal wel moeten. Er zijn 33 categorieën, waarvan de top drie samen ruim 1,5 miljoen stuks dragen. |
| Deliveroo-commissie? | Onbekend, op te vragen. |
| TGTG-opbrengst per pakket en gederfde marge? | Onbekend, op te vragen. |

**Dit is de tweede rode vlag en commercieel de belangrijkste.** De beslislaag heeft per product twee getallen nodig: wat kost een onverkocht stuk, en wat kost een gemiste verkoop. Zonder kostprijzen is er geen van beide. Dan wordt de baklijst een voorspelling met een grafiek erbij in plaats van een economische beslissing, en dat is precies het onderscheid waarop dit project verkocht is.

Er zijn twee uitwegen, in volgorde van voorkeur. Ofwel levert de bakkerij een kostprijs of brutomarge per productgroep aan, wat voor een bakker een normale vraag is en in een halfuur beantwoord kan worden. Ofwel wordt met een geschatte marge per categorie gewerkt, expliciet als aanname, met een gevoeligheidsanalyse in de backtest die toont hoeveel de baklijst verschuift als de marge tien procent afwijkt. Optie twee is werkbaar maar zwakker, en moet dan in het eindrapport staan.

**Volumeverdeling naar categorie** (stuks over de hele reeks, top 12):

| Categorie | Stuks |
|---|---|
| Koffiekoeken | 968.792 |
| Brood / Pistolets & baguettes | 314.365 |
| Brood / Desembroden dagelijks | 233.952 |
| Zout assortiment / Lunch | 209.397 |
| Patisserie / Individueel gebak | 138.715 |
| Dranken | 69.488 |
| All | 64.187 |
| Zakjes koekjes | 37.712 |
| Brood / Gesuikerde broden | 34.971 |
| Op bestelling | 29.328 |
| Patisserie / Croûtes | 26.187 |
| Brood / Desembroden weekend | 18.360 |

De categorie `All` met 64.187 stuks is de Odoo-standaardcategorie en betekent "niet ingedeeld". Die producten hebben dus geen bruikbare groepering en zullen apart behandeld moeten worden. `Bag` staat met 44.204 stuks in de top vijftien van producten: dat is verpakking, geen product, en het hoort niet in een baklijst.

---

## Blok G. Kalender en context

| Vraag | Antwoord |
|---|---|
| Openingsuren en sluitingsdagen per filiaal bekend? | Eén `resource.calendar` aanwezig, inhoud nog niet getoetst. De sluitingsdagen zijn uit de data af te leiden maar niet bevestigd. |
| Lokale evenementen? | Onbekend, op te vragen. |
| Promoties gedateerd beschikbaar? | Niet gevonden. `discount` bestaat wel op de bonregel, dus kortingen zijn per regel zichtbaar en gedateerd afleidbaar. |
| Filialen met afwijkend profiel? | Niet vast te stellen zolang de filiaalvraag uit blok B openstaat. |

Positief punt: `discount` per bonregel betekent dat promotiedruk meetbaar is zonder dat iemand een promotiekalender hoeft op te graven. Dat is een aanname minder.

---

## Nevenbevinding: sale.order

Er staan 31.112 verkooporders naast de kassa, met 134.495 regels. Van die orders staan er **10.381 in `draft`** (33 procent) tegenover 20.613 in `sale` en 110 geannuleerd. De bedragen zijn klein (de recentste drie: € 14,72, € 13,14, € 10,16), dus dit is geen groothandel maar consumentenvolume, waarschijnlijk bestellingen of click-and-collect. De categorie `Op bestelling` met 29.328 stuks past daarbij.

Een derde van deze orders in draft is een kwaliteitssignaal: draft-orders zijn mogelijk nooit uitgevoerd. **Voorstel: alleen `state = sale` meenemen, en de overlap met de kassaverkopen controleren vóór optellen**, anders wordt besteld-en-afgehaald volume twee keer geteld.

---

## Eindoordeel

**De data draagt het model met deze beperkingen:**

De verkoopkant is sterk. Negentien volle maanden op bonregelniveau, per product, met tijdstip, actueel tot vandaag, met een volledige jaarcyclus en jaar-op-jaar overlap. Daar is een betrouwbaar voorspelmodel per product per dag op te bouwen, en de baselines waar dat model tegen afgerekend wordt kunnen deze week draaien.

Drie beperkingen bepalen wat er bovenop dat model gebouwd kan worden.

**Eén.** De vraag is niet gemeten, alleen de verkoop. Er is geen productie- en geen restregistratie, dus uitverkoop is onzichtbaar behalve via het uur van de laatste verkoop. Het model voorspelt daarmee verkoop, niet vraag, en dat moet in elke uitspraak staan die eruit komt.

**Twee.** Er zijn geen kostprijzen (één procent van de catalogus). Zonder marge per product of per groep is de beslislaag met kanaalmarges niet te bouwen zoals bedoeld, en valt de baklijst terug op een voorspelling zonder economische afweging.

**Drie.** Deliveroo en Too Good To Go bestaan niet in Odoo. Het geconsolideerde overzicht over alle verkoopkanalen uit artikel 4 kan dus per definitie niet uit Odoo komen. Zolang die exports er niet zijn, is dat deel van de opdracht niet uitvoerbaar, en de dagen die eraan hangen zijn opgeschort conform artikel 4.

Geen van deze drie is een reden om te stoppen, en geen van deze drie is de schuld van iemand hier. Twee ervan (kostprijzen, restaantallen) zijn met een halfuur werk aan de kant van de bakkerij op te lossen. De derde (kanaalexports) loopt al.

Wat wél verandert: de eerste dagen gaan naar het model op winkelverkoop, niet naar de consolidatie, want die kan nog niet. Dat is een andere volgorde dan verwacht, en die verschuiving hoort vandaag gemeld te worden en niet op dag vier.

---

_Ingevuld 7 aug 2026 op basis van `scripts/odoo_audit.py` tegen `renard_bakery_19`. Alle cijfers reproduceerbaar. Geen enkele klantrij verliet de Odoo-omgeving: dit document bevat uitsluitend aggregaten._

---

## Addendum, 12 augustus 2026

> Hercontrole vijf dagen na de audit. `scripts/odoo_audit.py` opnieuw gedraaid tegen dezelfde omgeving. De cijfers hierboven blijven ongewijzigd geldig: 678.309 kassabonnen, 1.556.770 bonregels, 331 producten met verkoop, 539 verkoopdagen, 3 kassa's, 1 magazijn, 0 productieorders, 0 afvalregistraties. Uid 3759 werkt nog, de omgeving is dus niet opnieuw opgebouwd sinds 7 augustus (A13).

### Bevinding 1. De omgeving leeft, maar er is niets meer in geschreven sinds 7 augustus

De preprod is bereikbaar en in gebruik: uid 3759 authenticeert, alle bevragingen lopen, en de omgeving is op 12 augustus ook langs de kant van de opdrachtnemer geopend. Bereikbaar is dus bewezen. Dat is niet hetzelfde als meesynchroniseren met productie, en dat tweede is wél open.

Sinds 7 augustus 13u39 is er namelijk **geen enkel record aangemaakt of gewijzigd**, in geen enkel model:

| Model | Veld | Laatste | Aantal na 7 aug |
|---|---|---|---|
| `pos.order` | `create_date` | 2026-08-07 12:18 | 0 |
| `pos.order` | `write_date` | 2026-08-07 12:38 | 0 |
| `sale.order` | `create_date` | 2026-08-07 13:39 | 0 |
| `account.move` | `create_date` | 2026-08-07 12:43 | 0 |
| `stock.move` | `create_date` | 2026-08-07 12:41 | 0 |
| `product.product` | `write_date` | 2026-08-04 06:20 | 0 |
| `res.users` | `write_date` | 2026-08-07 13:38 | 0 |

Twee verklaringen passen daar even goed op, en ze zijn van buitenaf niet te onderscheiden:

**Ofwel is de bakkerij dicht** en is er dus niets om te registreren. Dat past bij de zomersluiting uit blok D: augustus 2025 was 24 van de 31 dagen leeg, augustus 2026 is leeg vanaf de eerste, en 7 augustus staat op € 75.

**Ofwel is de preprod een kopie die niet meesynchroniseert** met productie. Dat de laatste schrijfactie samenvalt met het uur waarop het werkaccount werd aangemaakt, past even goed bij die lezing.

Het onderscheid is niet academisch. Blok A noteert "live koppeling op preprod". Als de tweede lezing klopt, is dat woord onjuist en bouwen we op een aftakking die niet meer bijwerkt: bij heropening komen de nieuwe verkopen er dan nooit in aan, en dat blijkt pas bij de operationele koppeling van artikel 4. **Zolang de bakkerij dicht is, ziet een niet-synchroniserende kopie er exact hetzelfde uit als een synchroniserende.** Daarom hoort deze vraag nu gesteld: vandaag kost ze één mail aan Idealis, na de heropening is ze zelf te beantwoorden maar pas nadat er tijd verloren is. Zie `aannames.md` A14 en `vragen-aan-lien.md` vraag 27.

Voor het bouwwerk zelf verandert er niets: negentien maanden historiek is negentien maanden historiek, en de baselines kunnen erop draaien.

### Bevinding 2. De kostprijs staat ook niet op de bonregel, en dat is nu sluitend

Blok F stelde het ontbreken van kostprijzen vast op `product.standard_price`. Daar was een voor de hand liggend tegenargument op: Odoo berekent marge op de kassabonregel zelf, via `total_cost` en `margin`. Nagekeken, en het houdt geen stand:

| | Bonregels | Aandeel |
|---|---|---|
| Totaal | 1.556.770 | 100% |
| `total_cost` > 0 | **715** | 0,0% |
| `total_cost` = 0 | 1.556.054 | 100,0% |
| `is_total_cost_computed` = waar | 1.556.770 | **100,0%** |

De laatste regel is de beslissende. Odoo heeft de kostprijs op **elke** bonregel wél berekend, en kwam 1.556.054 keer uit op nul. Dit is dus geen "nog niet ingevuld" maar een gemeten nul: er zit geen kostprijsinformatie in het systeem om mee te rekenen. De 715 regels met een kostprijs hangen aan dezelfde 3 producten die ook een `standard_price` hebben, goed voor 1.017 stuks op een totaal van 2.218.211 verkochte stuks, oftewel **0,0 procent van het volume**.

Ook `margin` en `purchase_price` zijn niet bevraagbaar op deze modellen (server-fout bij het filteren), dus daar valt niets te halen.

**Gevolg:** A4 staat niet alleen overeind, hij is nu langs twee kanten dichtgetimmerd. De vraag naar een brutomarge per productgroep (vraag 19) is daarmee niet één van de opties maar de enige weg naar een beslislaag die een economische afweging maakt in plaats van een voorspelling met een grafiek erbij. Dat is het waard om zo te brengen: het is een halfuur werk bij de bakker en het is het verschil tussen D4 zoals verkocht en D4 uitgekleed.

_Addendum 12 aug 2026. Zelfde methode, zelfde belofte: uitsluitend aggregaten, geen enkele klantrij op schijf._

---

## Addendum 2, 12 augustus 2026: de TGTG-reeks

> De documentendump van Too Good To Go is geparst met `make tgtg`. Reproduceerbaar. Uitsluitend aggregaten hieronder, geen enkele bestelregel.

### Wat er in zit

| | |
|---|---|
| Documenten | 250 pdf's in zeven deelexports, **alle 250 gelezen** |
| Periode | **4 juli 2019 t/m 31 juli 2026** — zeven jaar, vier en een half jaar meer dan Odoo |
| Winkel | één: `storeId 8113`, Renard Bakery, Place Fernand Cocq, 1050 Elsene |
| Pakketten | twee soorten: `Panier Surprise` (31.026 stuks) en `Feestdagenpakket` (3 stuks) |
| Volume | **31.029 pakketten over 1.872 verkoopdagen** |

### Groei

| Jaar | Dagen | Pakketten | Gem./dag |
|---|---|---|---|
| 2019 | 76 | 630 | 8,3 |
| 2020 | 220 | 2.239 | 10,2 |
| 2021 | 241 | 3.440 | 14,3 |
| 2022 | 237 | 3.550 | 15,0 |
| 2023 | 263 | 5.110 | 19,4 |
| 2024 | 326 | 5.781 | 17,7 |
| 2025 | 298 | 5.671 | 19,0 |
| 2026 | 211 | 4.608 | 21,8 |

### Wat een pakket opbrengt

Dit is het eerste **gemeten** getal over de waarde van een overschot in dit dossier. Berekend als de gemiddelde bruto verkoopprijs uit het verkoopoverzicht min de commissie per stuk van de factuur.

| Jaar | Bruto per pakket | Commissie | Netto per pakket |
|---|---|---|---|
| 2019 – 2022 | € 3,99 | € 1,29 | **€ 2,70** |
| 2023 | € 4,18 | € 1,29 | € 2,86 |
| 2024 | € 5,21 | € 1,29 | € 3,93 |
| 2025 | € 5,94 | € 1,95 | € 4,01 |
| 2026 | € 6,16 | € 1,87 | **€ 4,28** |

Over de hele reeks: 31.029 pakketten, € 152.893 bruto, € 4,93 gemiddeld per pakket.

**Let op bij de uitbetalingen.** Het rekeningoverzicht vermeldt een betalingscyclus per kwartaal (januari, april, juli, oktober) en draagt een openstaand saldo over naar de volgende maand. De maandbedragen zijn daardoor niet zomaar op te tellen en niet toe te wijzen aan de maand waarin de pakketten verkocht zijn. Gebruik de berekende netto-opbrengst hierboven, niet de uitbetaling.

### De weekdagverdeling, en waarom ze ertoe doet

| ma | di | wo | do | vr | za | zo |
|---|---|---|---|---|---|---|
| 5.688 | **2.899** | 3.580 | 4.422 | 3.433 | 5.225 | **5.782** |

Zondag en maandag zijn samen goed voor 37 procent van alle pakketten, dinsdag voor 9 procent. Dat is een factor twee tussen de uitersten. Twee lezingen, en het onderscheid is te maken zodra het Odoo-extract er is: ofwel is dinsdag een sluitingsdag of een dag na sluiting, ofwel wordt er op zondag en maandag structureel te veel gebakken. Het eerste is een kalenderfeit, het tweede is geld.

### Wat dit repareert aan blok E

Blok E stelde vast dat er **geen enkele meting van de aanbodkant** bestaat: `mrp.production` = 0 en `stock.scrap` = 0. Dat blijft waar voor productie en afval, maar het is niet langer volledig waar voor overschot. Een TGTG-pakket is per definitie wat er overbleef. Zeven jaar dagreeks van overschot is geen restregistratie, maar het is de enige aanbodmeting die er is, en ze is bruikbaar als ondergrens.

---

## Addendum 3, 12 augustus 2026: de kassavraag, gemeten

> Reproduceerbaar met `make kassa`. Gedraaid op het extract van 12 augustus (219.503 geaggregeerde rijen uit 1.556.736 bonregels) en op de TGTG-dagreeks.

### De aanleiding

De opdrachtgever gaf aan dat er maar één kassa nodig is, die van de bakkerij, en dat de andere twee vermoedelijk andere concepten van Renard Foods zijn. Dat is getoetst.

### Wat er gemeten is

**Productmix.** De top van het assortiment is bij alle drie de kassa's vrijwel identiek:

| | Kassa 1 | Kassa 2 | Kassa 3 |
|---|---|---|---|
| Pain au chocolat | 6,6% | 6,8% | 7,2% |
| Sandwich | 6,4% | 6,4% | 5,9% |
| Croissant | 5,7% | 5,7% | 5,8% |
| Cinnamon Roll | 3,6% | 4,3% | 4,8% |
| Baguette White | 3,7% | 3,6% | 3,2% |

**Sluitingsdagen.** Kassa 1 draaide 534 dagen, Kassa 2 528, Kassa 3 513. Op 0, 6 en 21 dagen stond er één stil terwijl een andere draaide. Ze volgen dus dezelfde kalender.

**Omzetaandeel.** 35,0 / 29,0 / 36,0 procent.

**Correlatie met de TGTG-volumes**, over 500 gedeelde dagen: Kassa 1 r = +0,14, Kassa 2 r = +0,05, Kassa 3 r = −0,10. Alle drie te zwak om iets op te bouwen.

**Onderlinge samenhang** van de dagomzet, over 511 dagen waarop alle drie draaiden: r = +0,17 tot +0,23.

**Stabiliteit van het dagaandeel:** spreiding van 19,6 tot 26,3 procent, met uitschieters van 0,0 tot 90,6 procent op afzonderlijke dagen.

### Wat dit uitsluit

**De premisse klopt niet: geen van de drie kassa's is een ander concept.** Croissants, pains au chocolat en sandwiches staan bij alle drie bovenaan, in vrijwel dezelfde verhoudingen. Filteren op één kassa zou ongeveer tweederde van de bakkerijomzet weggooien.

### Wat open blijft

Registers in één winkel, of drie vestigingen van dezelfde bakkerij. De data wijst niet hard aan:

- Drie registers achter één toonbank delen dezelfde klantenstroom en zouden bijna gelijk moeten lopen. Ze doen dat niet (r ≈ 0,2)
- Drie vestigingen met een eigen klantenkring zouden een stabiel aandeel hebben. Dat is het maar half: de spreiding zit in het grijze gebied
- Dagen waarop één kassa op 0 procent of op 90 procent uitkomt, passen beter bij registers die naar gelang de bezetting opengaan dan bij vaste vestigingen

### Gevolg voor het datamodel

**Alle drie meenemen.** `filiaal_id` blijft in het model bestaan, maar wordt opgeteld tot één geheel zolang de opdrachtgever niet bevestigt wat het is. Dat is de enige keuze die bij beide uitkomsten juist blijft: klopt "registers", dan was optellen altijd al correct; klopt "vestigingen", dan staat de dimensie er en is uitsplitsen een rapportagekwestie, geen verbouwing.

### Nevenbevinding over TGTG

Het aantal pakketten per dag schommelt sterk (gemiddeld 20,2 in 2025-2026, spreiding 63 procent) maar hangt **nauwelijks samen met de dagomzet van de winkel** (r = +0,06 tegen alle kassa's samen). Het overschot volgt dus niet de drukte. Dat is op zich een bevinding: wat er overblijft, wordt bepaald door wat er 's ochtends gebakken is, niet door hoeveel er die dag verkocht werd. Precies het soort verband dat dit platform zichtbaar hoort te maken.
