# Vragen aan de opdrachtgever

> Vragen worden hier verzameld en in **blokken** gesteld, niet druppelsgewijs. Dat scheelt haar tijd, het maakt van de vragen een document in plaats van ruis, en het voorkomt dat een half antwoord in een chatstroom verdwijnt.
>
> Werkwijze: verzamelen, één keer per dagdeel als genummerde lijst versturen, antwoorden hier terugschrijven met datum.

## Blok 1, te stellen vóór de start

**Contractueel**
1. Staat er een dagprijs met een geraamd aantal dagen in, of een totaalbedrag? (Een totaalbedrag maakt er stilzwijgend een vaste prijs van.)
2. Voorschot vijftig procent, betaalbaar vóór dag 1: bevestigd?
3. Betalingstermijn van de facturen, en is die onafhankelijk van de betaling door de eindklant?
4. Staat het woord introductietarief in de tekst, met het standaardtarief ernaast?
5. Wie is eigenaar van de code, en op welk moment gaat het eigendom over?
6. API- en tokenkosten zijn voor rekening van de eindklant: staat dat er expliciet in?

**Scope**
7. Bevestiging dat het CFO-dashboard als afgewerkte applicatie, de app-versie, de notificaties, de AI-uitleglaag en de opleiding **niet** in fase 1 zitten. (Deze zijn alle vijf genoemd in het gesprek van 7 augustus.)
8. Welke filialen zitten in fase 1, en welke productgroepen?
9. Wat is de gewenste opleverdatum van fase 1, en waar komt die vandaan?

**Data**
10. Wanneer is de Odoo-toegang of de volledige export beschikbaar?
11. Wie is de technische contactpersoon aan de kant van de eindklant?
12. Zijn er restaantallen, bakaantallen of uitverkoop-momenten beschikbaar? (Dit bepaalt of we de vraag zien of alleen de verkoop. Zie `data-audit.md` blok E.)
13. Zijn kostprijzen of marges per product beschikbaar, en de Deliveroo-commissie en de TGTG-opbrengst per pakket?
14. Zijn openingsuren, sluitingsdagen en gedateerde promoties beschikbaar?

**Techniek**
15. Welke toegangen krijgen we, en kan dat als projectgebonden account in plaats van een hoofdaccount?
16. Hosting: is Supabase plus Vercel een eis van de eindklant, of een voorkeur? (Voor een nachtelijke berekening plus een baklijst is een kleine server met een cron eenvoudiger en goedkoper. Dit hoeft geen discussie te worden, wel een bewuste keuze.)
17. Op wiens naam en rekening staat de infrastructuur? Voorkeur is: op naam van de eindklant, met beheertoegang voor ons.

---

## Antwoorden

<!-- Terugschrijven met datum en bron, bijvoorbeeld: "3. Betalingstermijn 30 dagen, niet gekoppeld aan eindklant. Bevestigd door Lien, WhatsApp, 12 aug." -->

**Alle antwoorden via Kwinten, 12 aug 2026:**

1. De facto totaalbedrag. 2. Voorschot betaald; contract nog niet getekend. 3. Ja. 4. Contractzaak, niet voor hier. 5. Eigendom code: Lien; idem abonnement met credits. 6. Zie 5. 7. **App zit niet in fase 1; notificaties en AI-uitleglaag wél; opleiding is voor Lien.** ⚠ Dit is méér dan de scope van 12 aug beschreef — impact op de raming, zie dagboek. 8. Ixelles, één vestiging, met mogelijkheid tot uitbreiding vestiging 2. 9. **Deadline 27 augustus.** 10. Opgelost. 11. Alles via Lien. 12. Onbekend. 13. Oké → zie 19. 14. Openingsuren via Google; sluitingen meten we zelf. 15. Oké. 16. Supabase+Vercel is een eis. 17. Opgelost door 40. 18. Wordt gecheckt; werkhypothese: **kassa's in één vestiging** — strookt met onze meting, optellen blijft correct. 19. **Herzien 12 aug: marges zijn een add-on, geen fase 1** — de data bestaat niet bij de klant en het is onzeker of ze dit in deze fase willen. Het margescherm blijft in de onbeschikbaar-staat, met die reden. 20. Onbekend bij Lien/Kwinten; vraag ligt bij de bakkerij, blokkeert niets. 21. Oké. 22. Open. 23. Ja, rebuilds kunnen — gedekt door het verzekeringsextract. 24. Aanname bevestigd te houden: sep–dec 2024 is ruis, start jan 2025. 25. **Gemeten 12 aug, gesloten: er is géén overlap.** Van de 20.613 bevestigde verkooporders is er nul via de kassa afgerekend (`pos_order_line_ids` leeg bij alle). Het is een apart bestelkanaal: € 1,8 miljoen, gemiddeld € 88 per order tegenover € 10,54 per kassabon — B2B-profiel, goed voor ~25% bovenop de kassaomzet. Zie vraag 43. Bijvangst: één conceptorder (18 feb 2026) heeft een tikfout van 1,9 × 10²⁵ euro; onschuldig want concept, maar op te ruimen. 26. Ok. 27. **Bakkerij in verlof tot 23 aug** — verklaart de stilstand sinds 7 aug; de synchronisatievraag beantwoordt zichzelf na de heropening. 28. **Bevestigd.** 29. Enkele familieleden die RB besturen. 30. Te bekijken; onze aanname blijft de werkbasis. 31. Oké. 32. Opgelost door 40. 33. Inderdaad. 34. Uitleg + stappen gegeven, actie Sophie. 35. Oké. 36. **Wordt nu opgevraagd.** 37. Accountmanagers vragen om verder dan 12 maanden terug te gaan. 38. Ingestmailbox uitgelegd, opzet volgt. 39. Uitgelegd. 40. **Bevestigd: Renard = project binnen Liens Supabase/Vercel, via abonnement.** 41. To-dolijst per persoon gegeven. 42. Ja; Kwinten maakt het project zelf aan (in Liens org of met overdracht).

---

## Blok 2, na de data-audit van 7 augustus

> Deze vragen komen niet uit een aanname maar uit de gemeten data. Ze zijn genummerd zodat ze één voor één beantwoord kunnen worden, en gerangschikt naar hoeveel ze blokkeren. De eerste drie bepalen wat er in de vijf dagen realistisch gebouwd kan worden.

**Blokkerend voor het datamodel**

18. **Zijn Kassa 1, 2 en 3 drie verschillende winkels, of drie registers in dezelfde winkel?** In Odoo hangen ze alle drie aan dezelfde vennootschap en hetzelfde magazijn, wat op het tweede wijst, terwijl er in het gesprek sprake was van twee vestigingen. Dit bepaalt of de baklijst één lijst is of drie, en of de opzet "zodat een derde vestiging erin schuift" nu al iets betekent. Als er een tweede winkel bestaat die nog niet in Odoo staat: wanneer komt die erin?

_Spoor gevonden op 12 aug: onder de gebruikersaccounts van deze Odoo staan er meerdere die toebehoren aan andere horecazaken. **Opgelost, gemeten 12 aug:** dat zijn geen concepten van Renard maar B2B-kláchten met een portaallogin. Alle tien de grootste kopers van het bestelkanaal (vraag 43) zijn portaalgebruiker; 2.497 van de 7.482 kopers hebben zo'n login. De horecazaken onder de users zijn dus afnemers die via het bestelportaal groothandelsorders plaatsen — burger buns, baguettes en croissants in bulk. Dit ondersteunt de werkhypothese dat de drie kassa's gewoon registers in één vestiging zijn._

_Tweede meting 12 aug, en die maakt het zo goed als zeker: de drie kassa's zijn drie fysieke registers naast elkaar, geen functionele splitsing. Bongrootte vrijwel gelijk (mediaan € 7,15 / € 7,50 / € 7,95), het uurprofiel is tot op het procentpunt identiek (open rond 6u, piek 10–11u, dicht na 17u), en op 530 van de 539 verkoopdagen waren er twee of meer kassa's actief binnen hetzelfde uur — op 509 dagen alle drie tegelijk. Ze draaien dus zij aan zij met dezelfde openingsuren. De wisselvallige dagverdeling (0%–90%) past daarbij: klanten verdelen zich over de rijen al naargelang de bezetting. Vraag 18 blijft formeel open voor Sophie's bevestiging, maar de data laat weinig ruimte._

19. **Kostprijzen.** Van de 395 producten heeft er één procent een kostprijs ingevuld. _(Aangescherpt 12 aug: ook op de kassabonregel staat niets. Odoo heeft de kostprijs op alle 1.556.770 bonregels berekend en kwam 1.556.054 keer uit op nul. Dit is dus geen veld dat nog ingevuld moet worden, er is gewoon geen kostprijsinformatie in het systeem. De vraag hieronder is daarmee de enige weg.)_ De beslislaag heeft per product twee getallen nodig: wat kost een onverkocht stuk, en wat kost een gemiste verkoop. Zonder die twee wordt de baklijst een voorspelling met een grafiek erbij in plaats van een economische afweging. Een brutomarge per productgroep volstaat, dat hoeft geen calculatie per artikel te zijn. Kan de bakker dat aanleveren? Dat is doorgaans een halfuur werk aan hun kant.

20. **Wordt ergens bijgehouden hoeveel er gebakken wordt en hoeveel er overblijft?** In Odoo staat nul productie en nul afval. Zonder dat meten we verkoop en niet vraag: als de croissants om tien uur op zijn, meet de kassa de rek en niet de klant. Dat is te ondervangen, maar het moet expliciet in het eindrapport en het beperkt wat het model mag claimen. Bestaat er een papieren of Excel-registratie die niet in Odoo terechtkomt?

**Planning en scope**

21. **Deliveroo en Too Good To Go staan niet in Odoo**, in geen enkele vorm. Het geconsolideerde overzicht over alle kanalen kan dus niet uit Odoo komen. Zolang die exports er niet zijn, is dat deel niet uitvoerbaar en zijn de bijhorende dagen opgeschort conform artikel 4. Wat is de stand van beide?

22. **De productieomgeving blijft geblokkeerd op een betalende Odoo-licentie.** Bouwen kan op preprod, opleveren niet: artikel 4 vraagt een operationele koppeling. Wanneer beslist de klant daarover?

**Technisch, door te geven aan Idealis**

23. Wordt de preprod periodiek opnieuw opgebouwd vanuit productie? Het werkaccount is bij de rebuild van 7 augustus verdwenen. Als dat opnieuw kan gebeuren, plannen we het beter nu in. _(Stand 12 aug: uid 3759 werkt nog, dus sindsdien geen rebuild.)_

27. **Synchroniseert de preprod mee met productie, of is het een kopie van een moment?** Gemeten op 12 augustus: sinds 7 augustus 13u39 is er in geen enkel model nog een record aangemaakt of gewijzigd. Dat kan simpelweg de zomersluiting zijn, en het kan een kopie zijn die stilstaat. Die twee zien er van buitenaf identiek uit zolang de winkel dicht is, en dat verandert pas bij de heropening. De reden om het nu te vragen: als de kopie stilstaat, bouwen we op een aftakking waar de nieuwe verkopen nooit in aankomen, en dat merken we dan pas bij de operationele koppeling. Eén regel antwoord volstaat.

24. Klopt het dat de eerste maanden in de data (september tot december 2024, elf bonnen in totaal) implementatie-ruis zijn en dat de reële registratie in januari 2025 begint?

25. Van de 31.112 verkooporders staat een derde in `draft`. Zijn dat niet-uitgevoerde bestellingen, en overlappen de uitgevoerde met de kassaverkopen? Zo ja, dan mogen ze niet opgeteld worden.

**Bevestigend, geen vraag maar een melding**

26. De data is beter dan verwacht: negentien volle maanden op bonregelniveau, tot vandaag actueel, 1,56 miljoen regels op 331 producten. Het voorspelmodel op winkelverkoop kan daarmee vooruit. De volgorde verschuift wel: eerst het model op de winkel, daarna de consolidatie, want die kan nog niet.

---

## Blok 3, tijdens de uitvoering

> Vragen 28 tot 33 komen uit de scopeherziening van 12 augustus: de baklijst is geschrapt en het CFO-platform is het product geworden, met login, database en koppelingen. Vragen 28 en 32 blokkeren het bouwen.

**Blokkerend, schriftelijke bevestiging nodig**

28. **Fase 1 levert vanaf nu één product: het CFO-platform.** De baklijst en de beslislaag zijn uit de scope; het voorspelmodel blijft als vooruitblik binnen het platform. Daar komen een database, een login en de koppelingen bij. De raming gaat daarmee naar **11,5 tot 16,5 dagen**, tegenover vijf dagen voor de oorspronkelijke opzet zonder platform. Conform de wijzigingsprocedure graag één schriftelijke bevestiging van beide punten: dat de baklijst vervalt, en dat de dagen voor het platform goedgekeurd zijn.

32. **Waar komt de database te staan, en op wiens naam?** Voorstel: een beheerde Postgres in een EU-regio, op naam en rekening van de eindklant, met beheertoegang voor ons. De reden is overdraagbaarheid — bij oplevering dragen we een toegang over in plaats van een server. Dit blokkeert alles vanaf de database, dus het is de eerstvolgende beslissing die genomen moet worden. Er hoort een verwerkersovereenkomst met de leverancier bij. Sluit aan op de eerdere vragen 16 en 17.

**Voor het ontwerp van het platform**

29. **Wie gebruikt het platform, en hoeveel mensen?** Fase 1 gaat uit van een handvol benoemde gebruikers, twee rollen (lezer en beheerder), geen SSO en geen tweefactor. Alles daarboven is een eigen fase. Graag de namen en e-mailadressen zodra de omgeving er staat.

30. **Welke cijfers moeten er op het eerste scherm staan?** Onze aanname: omzet en stuks per dag, jaar-op-jaar vergelijking, top-producten, verdeling per kanaal, marge zodra die er is, en de vooruitblik. Als de eindklant een vast rapport gewend is dat er anders uitziet, is dat nu goedkoper te weten dan later.

31. **In een latere fase komt er een mobiele app.** Fase 1 bouwt die niet, maar bouwt wel zo dat ze later aan te haken is in plaats van te herbouwen: de berekening zit in de kern, niet in de schermen. Dat kost nu vrijwel niets. Ter info, geen vraag.

**Deliveroo, na het bericht van Sophie**

33. **Welke velden vragen we aan Deliveroo?** Sophie kan de historiek niet zelf uit het partnerportaal halen en heeft gevraagd om het contact met Alexander De Vil en Mathias Joosten. Belangrijk voor de bruikbaarheid: het rapport moet **per dag** zijn, niet per week of per maand. Een maandtotaal is voor een kanaalvergelijking bruikbaar, maar niet voor de vooruitblik. Concreet gevraagd:
    - datum (dagniveau), product of artikelnaam, aantal
    - bruto-orderbedrag en de **commissie of netto-uitbetaling** — zonder dat tweede is de marge per kanaal niet te berekenen, en dat is precies wat het platform moet tonen
    - liefst twaalf maanden of meer, zodat er een jaarcyclus in zit
    Zolang dat er niet is, blijft `deliveroo` een leeg kanaal dat in het platform zichtbaar is als onbeschikbaar, met de reden erbij. De dagen die aan de consolidatie hangen, blijven opgeschort conform artikel 4.

<!-- Nieuwe vragen hier verzamelen tot het volgende verzendmoment -->

**TGTG, na het onderzoek van 12 augustus**

34. **Eén handeling bij de bakkerij lost de TGTG-koppeling op.** Er bestaat geen partner-API voor een enkele winkel, maar TGTG verstuurt aan het begin van elke maand automatisch een e-mail met de verkoopcijfers, de commissie en het saldo. Kan Sophie in **MyStore → profielicoon → Finances → "Monthly sales overview email"** die e-mail aanzetten, met deze drie bijlagen aangevinkt: **Order Summaries** (verkoopoverzicht), **Invoices** (factuur) en **Account Statements** (rekeningoverzicht)? En kan er een doorstuurregel komen naar een adres dat wij aanleveren? Dan komt de maandelijkse data vanzelf binnen en hoeft niemand nog handmatig te exporteren.

    Waarom een doorstuurregel en niet een extra gebruiker in MyStore: een uitgenodigd teamlid krijgt standaard de rol Operator, en die mag de financiële gegevens niet zien. Een andere rol vergt een supportticket bij TGTG. De doorstuurregel is eenvoudiger en geeft ons geen toegang tot hun portaal.

    _Antwoord 17 aug, Lien via Kwinten: **de ingestmailbox-constructie komt er niet**, en TGTG mag desnoods zonder periodieke aanvoer. Blok 9 is daarmee geschrapt (ook vraag 38 vervalt). Gevolg, eerlijk genoteerd: het TGTG-kanaal bevriest op de geparste historiek t/m juli 2026 en veroudert vanaf dan zichtbaar — het platform toont per kanaal tot wanneer de data loopt, conform harde regel 8. Wil de klant TGTG later alsnog actueel, dan kan de maandmail alsnog aangezet worden en loopt het kanaal vanaf dat moment weer mee; er gaat níéts verloren dat niet later nog op te halen is (TGTG bewaart de documenten in MyStore). Kwinten heeft zijn bezwaar gemeld: dit kiest bewust voor lagere datakwaliteit._

35. **Ter info, geen vraag: wij gaan het TGTG-portaal niet automatisch uitlezen.** Dat is in strijd met de gebruiksvoorwaarden en het account van de bakkerij staat daarbij op het spel. De e-mailroute hierboven is het kanaal dat TGTG zelf aanbiedt.

**Deliveroo — DRINGEND, na het onderzoek van 12 augustus**

36. **De historiek is er wél, en Sophie kan er zelf bij. Maar het venster verdwijnt.** In Partner Hub zit onder **Reports** een rapportagesectie die precies levert wat we nodig hebben, zonder API en zonder goedkeuring van de accountmanagers:

    - **Reports → Items Sold** — categorie, artikel, aantal, prijs, subtotaal
    - **Reports → Orders** — per order, met datum én de kolommen `Deliveroo commission` en `VAT on Deliveroo commission`

    Beide gaan **twaalf maanden terug**, in blokken van maximaal negentig dagen per keer, en komen als CSV. Vier downloads per rapporttype dekken dus een volledig jaar.

    **Waarom dit dringend is en niet gewoon belangrijk:** dat venster van twaalf maanden schuift elke dag mee op. Wat er vandaag nog in zit, is over een maand weg — en dan is het nergens meer te halen, ook niet door Deliveroo zelf voor zover we konden nagaan. Elke week wachten is dus permanent dataverlies. Dit is op dit moment het meest urgente openstaande punt van het hele project.

    Concrete vraag aan Sophie: kan zij vandaag of morgen in Partner Hub die twee rapporten downloaden over de laatste twaalf maanden, in vier blokken van negentig dagen? Als dat lukt, hebben we de Deliveroo-historiek binnen zonder op iemand te wachten.

37. **Ter aanvulling op vraag 33:** de aanvraag bij Alexander De Vil en Mathias Joosten blijft nuttig, maar dan voor iets anders dan we dachten. Vraag hen of Deliveroo **verder dan twaalf maanden** terug kan leveren — dát is wat Sophie zelf niet kan. Voor de laatste twaalf maanden hebben we hen niet nodig.

38. **De wekelijkse factuur van Deliveroo komt per e-mail.** Kan die naar dezelfde ingestmailbox doorgestuurd worden als de TGTG-documenten (vraag 34)? Dan lopen beide kanalen vanaf dat moment vanzelf binnen. De factuur bevat de commissie per order, fees en rebates — precies wat de marge per kanaal nodig heeft.

39. **De API lost de historiek niet op**, ter info zodat er geen tijd in gaat zitten. De Order API van Deliveroo geeft niets ouder dan dertig dagen terug, en de payload bevat geen commissie en geen netto-uitbetaling. Ook middleware zoals Deliverect of Lightspeed lost dat niet op: die kunnen niet tonen wat de bron niet levert, en geen enkele biedt import van orders van vóór de aansluiting.

**Hosting, na het nieuwe feit van 12 augustus: Lien host zelf, met onderhoudsabonnement**

_Dit herziet vraag 32 en de vragen 16-17. Als Lien de software zelf host en er een betalend onderhoudsabonnement aan hangt, is infrastructuur op haar naam niet langer een overdrachtsprobleem maar het bedrijfsmodel. Dan verschuiven de vragen:_

40. **Bevestiging van het hostingmodel.** Renard wordt een project binnen Liens eigen Supabase-organisatie en haar Vercel-team, op haar naam en rekening, verrekend via het onderhoudsabonnement? Dan vervalt ons voorstel uit vraag 32 (infrastructuur op naam van de eindklant) en zetten wij alles op als multi-klant-structuur: één project per klant, strikt gescheiden.

41. **De juridische kant van dat model.** Lien wordt dan verwerker voor Renard: er hoort een verwerkersovereenkomst Lien↔Renard bij, plus de standaard-verwerkersovereenkomst met Supabase (EU-regio verplicht). En het abonnement heeft een exitregeling nodig: wat krijgt Renard mee als het stopt (databasedump, code, domein), binnen welke termijn. Dat is één paragraaf in haar abonnementsvoorwaarden, maar hij moet er vóór de livegang staan, niet erna.

42. **Wat wij nodig hebben om te bouwen:** een Supabase-project (EU-regio) binnen haar organisatie met de projectsleutels, en een uitnodiging tot haar Vercel-team of het projectrepo gekoppeld aan haar Vercel. De GitHub-repo staat nu op ons account; afspreken waar die uiteindelijk hoort te wonen (haar organisatie ligt voor de hand als zij het onderhoud verkoopt).

43. **Nieuw, na de meting van vraag 25: er blijkt een derde Odoo-kanaal te bestaan.** Naast de kassa lopen er bevestigde verkooporders (bestellingen/leveringen) voor € 1,8 miljoen, gemiddeld € 88 per order — een B2B-profiel, ~25% bovenop de kassaomzet, en aantoonbaar zonder overlap met de kassa. Dit zit nu níét in de scope van het platform. Moet dit kanaal erin als "bestellingen"? Het is dezelfde bron (Odoo), dus de meerkost is klein, maar het is een scopebeslissing en die nemen wij niet zelf. Tot dan tellen we het niet mee en toont het platform alleen kassa + TGTG + (straks) Deliveroo.

    _Karakterisering, gemeten 12 aug (alleen aggregaten, geen namen opgehaald):_ 7.482 unieke kopers, sterk geconcentreerd — de top-5 draagt 38% en **één koper alleen al 20% (€ 356.000)**. Alle grote kopers bestellen via het portaal. De mix is onmiskenbaar groothandel: 87.000 burger buns (met en zonder sesam), baguettes en halve baguettes in bulk, Boulot, Rustique — naast de croissants en cinnamon rolls. Piek op vrijdag en zaterdag, past bij horeca die voor het weekend inslaat. **Vraag voor Sophie: is die grootste afnemer een zusterbedrijf van Renard Foods, of een externe klant?** Dat bepaalt of dit kanaal in het dashboard als omzet of (deels) als interne levering telt._

---

## Blok 4, na de datacontrole van 12 augustus (avond)

> Deze vier komen uit metingen op de canonieke data, niet uit een vermoeden. De eerste twee bepalen wat de vooruitblik mag beweren; de derde is een voorstel om het onderhoud ervan bij de klant te leggen zonder dat iemand nog iets moet mailen.

44. **Wordt een deel van het assortiment maar op bepaalde dagen aangeboden?** Gemeten over de 529 open dagen: het grootste product van het assortiment (€ 308.000 omzet) verkoopt op 96 tot 100% van de dagen maandag tot vrijdag, maar op 7% van de zaterdagen en 1% van de zondagen. Dat ziet eruit als een product dat in het weekend niet in de winkel ligt. Een ander product doet € 91.000 op 62 dagen: elke open dag in januari, en daarna niets — een seizoensproduct. Dit is geen detail: voor de vooruitblik per product moeten we weten of een lege dag "niet verkocht" of "niet aangeboden" betekent. Twee vragen: (a) is er een vaste regel welke producten op welke dagen in de winkel liggen, en kan die als lijstje komen? (b) zijn er producten die alleen in een bepaald seizoen bestaan? Kan de bakker dat niet aanleveren, dan leiden wij het patroon uit de data af — dat kan, het is alleen minder betrouwbaar dan het gewoon te weten. Zie de beslissing van 12 aug over productbeschikbaarheid.

45. **De sluitingskalender, en dan vooral vooruit.** We hebben de sluitingsdagen van het verleden zelf gemeten (54 dagen in 19 maanden, met een drempelregel — zie `beslissingen.md`). Maar de vooruitblik heeft de sluitingen van de **komende** twaalf maanden nodig, en die staan in geen enkele dataset. Een voorspelling voor een dag waarop de zaak dicht is, is geen voorspelling maar ruis, en het is precies het soort fout dat het vertrouwen in het hele scherm breekt. Twee vragen: (a) kan de bakkerij de geplande sluitingen voor de komende twaalf maanden doorgeven, inclusief de zomersluiting? (b) klopt onze meting dat de zaak zeven dagen per week open is? De data zegt van wel — zondag doet gemiddeld € 11.077.

46. **Het voorstel om dat automatisch te laten lopen: een gedeelde agenda.** Handmatig doorgeven werkt één keer en daarna niet meer. Ons voorstel is dat de bakkerij één agenda aanmaakt — bijvoorbeeld "Renard – sluitingen" in de Google-agenda die ze al gebruiken — en die met ons deelt als **geheime iCal-link** (Agenda-instellingen → "Geheim adres in iCal-formaat"). De nachtelijke job leest die link en werkt de kalender bij. Geen API-sleutel nodig, geen toegang tot hun andere agenda's, en zij onderhouden het op hun telefoon in plaats van in een bestand dat iemand moet mailen. Drie afspraken horen erbij:
    - **Titels volgens een vaste conventie**, want vrije tekst is niet betrouwbaar te lezen: `DICHT: reden` voor een sluiting, `ANDERE UREN: 7-12` voor een afwijkende dag, `PROMO: omschrijving`, `EVENT: omschrijving` voor iets in de buurt dat de drukte beïnvloedt (braderie, markt, wegenwerken).
    - **Hele-dag-events**, en voor een periode één event over meerdere dagen in plaats van losse dagen. Een herhalende reeks lezen we bewust niet: die wordt gemeld en overgeslagen in plaats van half geïnterpreteerd.
    - **Wij nemen niets stilzwijgend aan.** Reikt de agenda niet verder dan een bepaalde datum, dan zegt het platform vanaf die datum dat de vooruitblik onbeschikbaar is, met die reden erbij. Een lege agenda mag nooit als "open" gelezen worden.

    Vraag: is dat werkbaar aan hun kant, en wie beheert die agenda? Als een Google-agenda niet kan, werkt elke iCal-bron (Outlook, Apple) even goed. **Wij bouwen dit spoor er alvast bij, als losse en optionele laag: gebruikt de klant het niet, dan verandert er niets aan de cijfers en blijft er niets van achter.**

47. **Schoolvakanties, en wie die aanlevert.** De kalenderlaag heeft een plek voor schoolvakanties maar die staat nog leeg, en voor een bakkerij in Elsene is dat een van de sterkste vraagsignalen die er zijn: andere ochtendspits, andere weekendpiek. Dit hoeft níet uit de agenda van de bakkerij te komen, want het is openbare informatie — de Vlaamse en de Franse Gemeenschap publiceren de data. Wij vullen dat zelf in. Eén vraag ter controle: volgt de klantenkring van de winkel het Franstalige of het Nederlandstalige schoolregime, of beide? In Elsene is dat niet vanzelfsprekend en de vakanties lopen niet gelijk. _Nazorg 13 aug: wij hebben beide regimes ingevuld (publieke data, aanname A20) en allebei door de backtest gehaald. Het **Franstalige** regime verklaart het koopgedrag duidelijk het best (fout op vakantiedagen van 7,8% naar 6,0%) en draait nu in de prognose. De vraag blijft staan als bevestiging, niet als blokkade._

---

## Blok 5, 13 augustus — Deliveroo: de API, en een datum

> Lien komt terug op de Deliveroo-API. Die is op 12 augustus uit het ontwerp geschrapt (`koppelingen.md`), maar die beslissing stond niet in `beslissingen.md` en is dus heropend zonder de onderbouwing. Ze staat er nu wel in. Deze twee vragen horen bij elkaar en kunnen in één antwoord.

48. **Waar is de Deliveroo-API voor bedoeld?** Niet "wel of geen API" — de vraag is wélk probleem hij moet oplossen, want dat bepaalt of hij het juiste gereedschap is. Drie mogelijke antwoorden, drie verschillende gesprekken:

    - **"Zodat Sophie niets handmatig hoeft te doen."** Dan dekt de wekelijkse factuurmail naar de ingestmailbox dat al (vraag 38), tegen een fractie van de kost. De API voegt hier niets toe.
    - **"Zodat de Deliveroo-cijfers dagvers zijn."** Dat is een reële eis, en dan hoort er een eigen fase bij met eigen dagen. Niet erbij in fase 1: de deadline van 27 augustus telt elf werkdagen tegen een resterende raming van 14–19.
    - **"Omdat asklien.ai een herbruikbare Deliveroo-koppeling wil hebben."** Volkomen legitiem — bij een volgende klant is dat een asset in plaats van maatwerk. Maar dan is het productontwikkeling voor asklien.ai en geen deliverable voor Renard Bakery, en hoort het apart afgesproken en apart begroot.

    **Wat de API in geen van de drie gevallen oplost, en dit is het kernpunt:** de Order API geeft niets terug dat ouder is dan **dertig dagen** — dat is een vangnet voor gemiste webhook-events, geen archief. Sluit je hem vandaag aan, dan dekt hij ongeveer 14 juli tot nu: een maand die de CSV-export uit Partner Hub al heeft. Het verlies zit aan het andere uiteinde, augustus 2025, dat nu uit het venster van twaalf maanden valt. Bovendien bevat de payload **geen commissie en geen netto-uitbetaling**, dus de marge per kanaal — het cijfer waarvoor dit platform bestaat — kan er sowieso niet uit komen. Middleware (Deliverect, Flipdish, Lightspeed) lost dat niet op: die kunnen niet tonen wat de webhook niet bevat, en geen van hen biedt import van orders van vóór de aansluiting.

    _Statusmelding bij dit antwoord: dit komt uit documentatieonderzoek van 12 augustus, niet uit een test tegen een draaiende API — we hebben geen toegang. Het staat in Deliveroo's eigen documentatie, maar het is geen eigen meting zoals de kassa-analyse dat wel was. Wil je zekerheid vóór je beslist, dan is dat één vraag aan Alexander De Vil of Mathias Joosten, en die kan mee met vraag 37 (die hen al vraagt of Deliveroo verder dan twaalf maanden terug kan leveren): **geeft de Order API orderdata ouder dan dertig dagen terug, ja of nee?**_

49. **Zet een datum op de Deliveroo-historiek, in plaats van open te wachten.** Voorstel: **is er op 20 augustus niets binnen, dan levert fase 1 op met Deliveroo als onbeschikbaar**, en blijven de dagen die aan de consolidatie hangen opgeschort conform artikel 4.

    Waarom een datum en niet "we zien wel": het venster van twaalf maanden schuift elke dag op, dus "we zien wel" kiest niets en verliest ondertussen elke dag een dag historiek. Dit is het enige punt op de hele lijst waar uitstel onherstelbaar is.

    **Wat er permanent verloren gaat als het er nooit komt** — niet "geen Deliveroo", maar een gat in het verleden dat nooit meer dichtgaat:
    - jaar-op-jaar per kanaal over de ontbrekende periode;
    - de prognose voor Deliveroo-producten, want die heeft historiek nodig — een kanaal zonder verleden krijgt geen voorspelling tot er een jaar nieuwe data ligt;
    - de kanaalvergelijking over een vol jaar.

    Komt er over drie maanden alsnog een download, dan loopt Deliveroo vanaf dát moment gewoon mee. Alleen het verleden is weg.

    **En één ding dat wij niet voor je kunnen beslissen.** `CLAUDE.md` noemt drie dingen die dit platform onderscheiden van de Odoo-rapportering die er al ligt: de kanalen die Odoo niet kent, de marge die Odoo niet berekent, en de prognose die Odoo niet heeft. De marge is op 12 augustus al een add-on geworden omdat die data niet bij de klant bestaat (van 425 producten hebben er 3 een kostprijs). Valt Deliveroo er ook uit, dan blijft over: TGTG als extra kanaal, plus de prognose. Dat is nog steeds echte waarde — de prognose staat op 8,2% WAPE _(correctienoot 18 aug: sinds de modelverbetering van 15 augustus is dat 7,8%; de vraag zelf lag toen al bij Lien en blijft verder ongewijzigd)_ en is met een backtest onderbouwd — maar het is smaller dan wat er verkocht is. Dat gesprek voer je beter nu dan op 27 augustus.

## Blok 6, 13 augustus — de marge-invoer bestaat nu

> _Nazorg 14 aug: de invoer is herbouwd tot een **kostenmodel** — zie vraag 51. Vraag 50 blijft staan; alleen het formulier is rijker geworden, de vijf minuten werk zijn dezelfde._

50. **Wie vult de tien categoriemarges in?** Vraag 19 vroeg om marges per product en dat bleek een onmogelijke oefening (3 van 425 producten hebben een kostprijs in Odoo). De herformulering van 12 augustus is nu gebouwd: op **Instellingen** kan een beheerder per productgroep een brutomarge invullen — de groepen staan er al, met hun aandeel in de omzet ernaast, zwaarste eerst — en **Margebewaking** rekent er meteen mee (gewogen marge, dekking, per groep; alles wat níét ingevuld is, telt eerlijk niet mee). Tien categorieën dekken 95% van de omzet; een schatting van de zaakvoerder volstaat om de orde van grootte te bewaken en is later per groep bij te stellen. Concreet: wie vult ze in, en wanneer? Vijf minuten werk zodra iemand de percentages kent.


## Blok 7, 14 augustus — kostenmodel, winkels en het wetgevend kader

51. **Het margeformulier is een kostenmodel geworden — wie stelt het menu samen?** Op Instellingen staat niet langer één brutomarge-veld per groep, maar een kostenopbouw naar het foodcost-denken uit de sector: de beheerder stelt zelf criteria samen (grondstoffen, verlies en verspilling, basisingrediënten — toevoegen, hernoemen en verwijderen kan vrij) en vult per productgroep per criterium een percentage van de omzet in. De brutomarge is dan 100 min de som, en Margebewaking toont de hele trap: omzet → kosten per criterium → marge. Eerder ingevulde brutomarges gaan niet verloren (ze verschijnen als "Totale kost"). Twee vragen: (a) volstaan de drie voorgestelde criteria als vertrekpunt voor de zaakvoerder, of denkt die in andere kostensoorten? (b) blijft het antwoord op vraag 50 (wie vult in, en wanneer) hetzelfde nu het invullen per criterium gaat?

52. **Bevestigt de bakkerij dat zij de bronbestanden zelf tien jaar bewaart?** De fiscale bewaarplicht (10 jaar sinds 2023) rust op de bakkerij en betreft de bronstukken — ook de Deliveroo-rapporten en TGTG-afrekeningen. Het platform is een afgeleide rapportagelaag en mag nooit het enige archief worden; de ingestmailbox is een kopie, geen archief. Eén bevestigingszin volstaat. Achtergrond in `docs/wetgevend-kader.md`.

53. **Heeft Renard een verbruikszaal die meer dan € 25.000 per jaar omzet?** Niet voor ons platform — dat valt buiten het GKS-regime — maar als het antwoord ja is, wordt hun kassa op termijn GKS 2.0-plichtig (realtime rapportering aan FOD Financiën) en kan het Odoo-exportformaat wijzigen. Dat willen we dan zien aankomen in plaats van merken. Zie `docs/wetgevend-kader.md` punt 3.

54. **Ter info, geen vraag: het platform kan nu meerdere winkels aan.** De klant wil schalen; vanaf vandaag is een tweede vestiging één configregel (welke kassa's/filialen bij welke winkel horen) in plaats van een verbouwing. Elke winkel krijgt dan eigen schermen én een eigen gebackteste prognose, het totaal blijft bestaan, en een winkel met te weinig historiek toont dat eerlijk in plaats van een ongefundeerde voorspelling. Vandaag verandert er niets: alles telt als één geheel tot iemand een indeling vastlegt (en vraag 18-nazorg bevestigt dat de huidige drie kassa's registers zijn).

## Blok 8, 14 augustus — scenario's op de prognose, en de grens van "actie"

Aanleiding: een externe audit van het platform (14 aug) plus het ontwerp voor de kalenderverversing. Twee dingen liggen buiten de huidige scope en horen dus hier, niet in de bouw.

55. **Wil je scenario's op de prognose in fase 1?** Het idee: de CFO kan op het prognosescherm aan de kalenderaannames draaien — toon deze week alsof het een vakantieweek is, alsof maandag een feestdag is, of met de vakantiecorrectie uit. Elk scenario is vooraf berekend door hetzelfde gebackteste model met een andere kalenderinvoer; de UI wisselt alleen tussen aangeleverde getallen, en het scenario is visueel duidelijk onderscheiden van de echte prognose, die altijd het anker blijft. Wat we bewust **niet** bouwen: vrije schuiven zoals "prijs +5%" of een factor met de hand verzetten — zonder gebackteste prijselasticiteit is dat een verzonnen cijfer op een scherm dat vertrouwen moet verdienen (harde regel 7). Omvang: ongeveer één dag. Bouwen in fase 1, of bewaren voor fase 2?

56. **Hoe ver mag "actie" op de schermen gaan?** We bouwen nu een briefing bovenaan elk scherm: per punt wat er opvalt, waarom, en wat er nodig is van wie — met een bedrag erbij alléén als de berekeningslaag dat kan staven. Dat is signalering, en het blijft binnen scope. De audit vraagt om verder te gaan: concrete productie-indicaties per categorie ("plan maandag lager"). Dat is de beslislaag die op 12 augustus uit fase 1 is geschrapt, en ze eerlijk bouwen vergt de kostenkant van te veel én te weinig bakken (het kostenmodel van vraag 51 is daarvoor de helft van de invoer). Blijft die geschrapt, of wordt dat de kern van fase 2? Zelfde vraag, kleiner: wil je ooit een werkstroom (aandachtspunten met eigenaar en status "opgelost") rond datakwaliteit, of volstaat de briefing?

## 14 augustus 2026 — de gebruikerslijst

Aanleiding: de database staat op het punt te draaien, en blok 12 (login op
Supabase Auth) is de eerstvolgende stap die niet zonder klantinvoer kan.

57. **Wie krijgt toegang tot het platform, en met welke rol?** Per persoon
    hebben we drie dingen nodig, en het derde wordt vaak vergeten:
    **naam**, **e-mailadres** en **rol**. De twee rollen uit scope D6 zijn
    *lezer* (ziet alles, wijzigt niets) en *beheerder* (beheert gebruikers,
    het kostenmodel van vraag 51 en de winkelindeling). Dat verschil is niet
    administratief: een beheerder kan de kostencriteria wijzigen en daarmee
    de marge die het hele platform toont. Drie punten erbij:

    (a) **Wie is de eerste beheerder?** Er moet er precies één zijn om mee te
    beginnen; die nodigt de rest uit. Zelfregistratie staat uit, dus zonder
    die eerste komt niemand binnen.

    (b) **Wat gebeurt er als iemand vertrekt?** Deze accounts zijn de enige
    persoonsgegevens in het systeem (`wetgevend-kader.md` §1). Daar hoort een
    bewaarregel bij: account weg bij uitdiensttreding. Eén zin volstaat, maar
    hij moet er zijn en hij hoort in het verwerkingsregister van de eindklant.

    (c) **Hoort Lien zelf op de lijst?** In het hostingmodel is zij verwerker;
    een eigen account is verdedigbaar voor ondersteuning, maar het is een
    keuze en geen vanzelfsprekendheid — en het hoort dan in de
    verwerkersovereenkomst benoemd te staan (vraag 41).

    We hebben deze lijst nodig vóór blok 12, niet erna. Zolang ze er niet is,
    draait de login op de huidige omgevingsgebaseerde laag en kan er niemand
    van de klant op.

## 18 augustus 2026 — de wijzigingsprocedure op onszelf toegepast

Aanleiding: de inspectieronde van 18 augustus. `scope.md` (derde herziening)
is bijgewerkt en daarbij bleek dat de eigen wijzigingsprocedure — elke
toevoeging genoteerd, geraamd, schriftelijk bevestigd — op een paar punten
niet gevolgd is. Dat repareren we door het alsnog voor te leggen, niet door
het stil te laten staan.

58. **Twee bevestigingen over de scope, vóór de aanvaarding op 27 augustus.**

    (a) **Sinds 12 augustus is er binnen de platformraming meer gebouwd dan
    de scope beschreef**: tweetaligheid NL/FR over het hele platform, de
    kostenmodel-invoer op Instellingen, de winkelindeling (een tweede
    vestiging is een configregel, geen verbouwing), de briefing bovenaan elk
    scherm, en de PDF-export van het CFO-rapport. Er is geen meerprijs — het
    zit in de gedraaide dagen — maar het hoort bevestigd te zijn zodat de
    oplevering nergens op een verrassing rust. Eén zin volstaat: "die vijf
    horen bij fase 1."

    (b) **Notificaties en de AI-uitleglaag: fase 1 of fase 2?** Het antwoord
    op vraag 7 (12 aug) zei dat beide wél in fase 1 zitten; `scope.md` zet ze
    onder "uitdrukkelijk NIET in fase 1", en er is nooit een raming voor
    voorgelegd of bevestigd. Dat verschil is tot vandaag onbeslecht gebleven.
    Ons voorstel: **fase 2** — de resterende dagen tot 27 augustus dragen ze
    niet, en half gebouwde notificaties zijn erger dan geen. Als ze toch in
    fase 1 moeten, dan hoort daar per de wijzigingsprocedure een raming in
    dagen bij en schuift er iets anders uit.

---

## 19 augustus 2026 — vijf voorstellen uit een externe review, alle vijf buiten fase 1

Kwinten heeft het platform door een externe reviewer laten halen. Die legde een echte fout bloot (de versheidsmelding rekende de zomersluiting als achterstand — gerepareerd) en gaf verder vijf voorstellen die **buiten `scope.md` vallen**. Ze staan hier omdat ze goede voorstellen zijn, niet omdat we ze bouwen. Harde regel 5: noteren, niet bouwen.

**Wat expliciet níét van toepassing is:** een multi-store managementlaag (winkelvergelijking, ranking, benchmark). Renard is op 12 augustus gemeten en bevestigd als **drie kassa's in één vestiging** — er is geen tweede winkel om tegen te vergelijken. Dit hoeft dus geen beslissing, het is een gegeven.

| | Voorstel | Waarom het nu niet gebouwd wordt | Wat het zou vragen |
|---|---|---|---|
| 59 | **"Wat opvalt" actiegericht maken**: per punt een eigenaar, een prioriteit, een euro-impact, een status en een deadline | Dit is de beslislaag, en die is in `CLAUDE.md` uitdrukkelijk uit fase 1 gehouden (het denkwerk staat in `model-ontwerp.md` omdat het de waarde van een latere fase bepaalt). Vandaag noemt de briefing wél al een eigenaar in woorden ("het platformbeheer", "de bakkerij, via Lien") | euro-impact per bevinding is een berekening, geen opmaak: ze hoort in de berekeningslaag en heeft een aanname per bevindingstype nodig |
| 60 | **Prognose doorvertalen naar productieadvies** per categorie (hoeveel viennoiserie, brood, lunch, patisserie) | Dit ís de baklijst, en die is op 12 augustus geschrapt. Bovendien: de productprognose staat op 20,1 % WAPE per product-dag en 66 % van de omzet is structureel gecensureerd — een productieadvies op die basis is een mening, geen advies (harde regel 7) | een productprognose die de censurering corrigeert, plus marges om een fout af te wegen |
| 61 | **Marge als hoofdverhaal**: bruto marge, netto kanaalbijdrage, food cost, waste-impact | De kostprijsdata bestaat niet bij de klant (S6, 12 augustus: marges zijn een add-on geworden). Het margescherm staat daarom eerlijk op onbeschikbaar. Wat wél kan zodra een beheerder kosten invult, wordt vanavond gebouwd | de kostencriteria per productgroep, ingevuld door de bakkerij |
| 62 | **Annotaties in de grafieken** ("vrijdag piekt structureel", "TGTG kost 33,1 % commissie") | Een annotatie is een bevinding, en bevindingen komen uit de berekeningslaag via het contract — nooit uit een component (harde regel 4). Het is dus geen opmaakklus maar contractwerk | per grafiek bepalen welke bevinding erbij hoort, en die meten |
| 63 | **Het rapport splitsen** in een executive one-pager en een volledige appendix | Klein en verdedigbaar, maar het is een uitbreiding van een deliverable die af is, acht werkdagen voor de deadline | een keuze over wat op die ene bladzijde hoort |

**De vraag aan Lien is smal:** hoort een van deze vijf nog vóór 27 augustus, of gaan ze naar de lijst voor fase 2? Bij twijfel: fase 2. Er is deze week geen bouwruimte die niet uit iets anders komt.

---

## 19 augustus 2026 (nacht) — één vraag met een datum eraan: de sluitingsdagen na 23 augustus

64. **Welke dagen is de bakkerij dicht tussen 24 augustus 2026 en eind 2027?** Kerstdag, nieuwjaar, Paasmaandag, 1 mei, O.-L.-H.-Hemelvaart, 11 en 21 juli, 15 augustus, 1 en 11 november — plus de wekelijkse sluitingsdag als die er is, en de jaarlijkse sluiting van 2027.

**Waarom dit een echte vraag is en geen formaliteit.** `config/sluitingsdagen.json` loopt tot en met 23 augustus 2026. Vanaf 24 augustus weet de prognose van geen enkele sluiting meer, en dan neemt ze aan dat de winkel open is. Dat staat ook zo op het scherm — het prognosescherm zegt letterlijk dat er voor die dagen geen sluiting bekend is en dat ze open veronderstelt — dus het platform liegt niet. Maar het betekent wel dat het scherm op 19 december 2026 een gewone vrijdagomzet op **25 december** zet, en eind december een gewone vrijdag op **1 januari**. Voor een CFO-platform is dat geen fout maar wel een cijfer waar je niets aan hebt, en het is het soort ding dat het vertrouwen in de rest van het scherm meeneemt.

**Waarom wij ze niet zelf invullen.** Dat de bakkerij op Kerstmis dicht is, lijkt vanzelfsprekend. Het is een aanname over de zaak, en die hoort volgens harde regel 6 bevestigd te worden en niet geraden — sommige bakkerijen zijn juist op feestdagen open, en juist bij Renard is 6 januari (galette) een van de drukste dagen van het jaar. Een verkeerd ingevulde sluitingsdag is bovendien erger dan een ontbrekende: een ontbrekende toont een cijfer met een zichtbaar voorbehoud, een verkeerde onderdrukt een dag die wél omzet had.

**Waarom het model dit niet zelf oplost.** De feestdagen staan wél in de kalender (`feestdag`, `brugdag`, `dag_voor_feestdag` zijn gevuld), maar ze corrigeren niets: het productiemodel draait op `KENMERKEN = ("schoolvakantie",)`. Dat is een gemeten keuze en geen vergetelheid — per-feestdagfactoren kúnnen niet, want elke feestdagnaam komt hoogstens twee keer voor in de anderhalf jaar kassahistoriek (Odoo begint in 2025), en een factor die je op twee waarnemingen past, kun je nergens tegen toetsen (harde regel 7). Zolang de historiek niet dieper is, is een handmatige sluitingslijst de enige eerlijke route.

**Wat we nodig hebben:** een lijstje datums, en per datum één zakelijk woord als reden ("Feestdag", "Jaarlijkse sluiting"). Dat woord komt letterlijk op het scherm, ook op het Franstalige scherm — het platform vertaalt handinvoer niet. Geen namen of persoonlijke omstandigheden: het bestand staat sinds 19 augustus in git en de reden belandt dus in de geschiedenis.

**Urgentie: middel, met een harde staart.** Het blokkeert de oplevering van 27 augustus niet — het scherm is eerlijk over wat het niet weet. Maar het is wel het eerste wat ná de oplevering zichtbaar misgaat, en dan is er niemand meer die het merkt. Bij voorkeur dus mee vóór de 27e, en anders als eerste punt van het onderhoud.

**Bijgewerkt 19 augustus 2026: de vorm van het antwoord is veranderd, de vraag niet.** Er hoeft geen lijstje meer heen en weer gemaild: het platform heeft nu een scherm **Sluitingsdagen** (zie vraag 65) dat de feestdagen van de komende twaalf maanden al toont en per dag alleen "open of dicht?" vraagt — twee klikken per rij, plus een vrije rij voor de jaarlijkse sluiting van 2027 en de vaste wekelijkse sluitingsdag als die er is. Wat wij nodig hebben is dus niet langer een lijstje maar een kwartiertje van iemand met een beheerdersaccount op dat scherm. Ook "open" aanklikken is waardevol: een bevestigd-open dag verliest zijn voorbehoud op het prognosescherm, en 6 januari (galette) is daar het schoolvoorbeeld van.

---

## 19 augustus 2026 (nacht) — vraag 65: mag de bakkerij haar sluitingsdagen zelf invoeren?

65. **Bouwen we een sluitingskalender op Instellingen, waar de beheerder zelf aanduidt wanneer de zaak dicht is? Raming 1,5 dag; een halve dag voor de versie zonder scherm.** Het volledige ontwerp staat in `docs/sluitingskalender-ontwerp.md`.

**Dit is de duurzame versie van vraag 64.** Die vraagt eenmalig om een lijstje datums, en dat lost het precies één jaar op — daarna komt dezelfde vraag terug bij iemand die dit project niet meer kent. Deze vraag gaat over de invoer zélf: één scherm waarop de bakkerij het voortaan zelf doet.

**Waarom het meer is dan een gemak.** Het prognosescherm zegt vandaag, letterlijk en terecht: *"staat er nog een sluiting op de planning, vul ze aan in de sluitingslijst en de prognose volgt."* Die sluitingslijst is een JSON-bestand in een git-repository. Het platform vertelt zijn lezer dus wat er moet gebeuren en biedt een handeling aan die een CFO per definitie niet kan uitvoeren. Het is eerlijk over het gat en tegelijk een doodlopende gang.

**Wat het oplevert, en dan alleen wat gratis meekomt** (het mechanisme bestaat al en wacht op data): geen omzetverwachting meer op een gesloten dag, en dus ook geen fout weektotaal; geen feestdag die zich twee dagen lang als "achterstand" meldt; de sluitingsmelding op het scherm die vandaag alleen werkt voor dagen die in de lijst staan; en het gegeven staat klaar voor fase 2, waar personeelsplanning en inkoop het nodig hebben. Wat er níét gratis bij zit en dus apart afgewogen hoort te worden: de periodevergelijking eerlijk maken wanneer er een sluiting in één van de twee periodes valt.

**Waarom het geen nieuwe complexiteit is.** Het platform heeft al precies deze keten in productie voor het kostenmodel: formulier op Instellingen → server-actie → één schrijffunctie in Postgres → de canoniekbouw leest het terug → contract → scherm. Dit is dezelfde keten met een andere tabel; de derde toepassing van iets wat er staat.

**De vondst die het volgens ons echt bruikbaar maakt:** het wordt geen leeg invoerscherm maar een bevestigingslijst. Het platform kent de Belgische feestdagen al voor elk jaar, dus het toont de komende twaalf maanden en vraagt per dag alleen "open of dicht?", met een vrije rij erbij voor de jaarlijkse sluiting of een verbouwing. Twee klikken per rij, één keer per jaar. En er komen drie toestanden in plaats van twee: bevestigd open, bevestigd dicht, en nog niet beantwoord — want onbekend is niet hetzelfde als open, en alleen bij die derde hoort een voorbehoud op het scherm. Dat "bevestigd open" is geen overbodige luxe: bij Renard is 6 januari juist een van de drukste dagen van het jaar.

**Wat er uitdrukkelijk niet in zit:** openingsuren, halve dagen, sluiting per kanaal, en algemene herhalingsregels. Wel één vaste wekelijkse sluitingsdag, omdat die als regel hoort en niet als lijst datums die weer afloopt.

**Onze inschatting van de volgorde.** Dit blokkeert de oplevering van 27 augustus niet, en het hoort dus niet vóór D1–D9. Maar als er ná de aanvaarding budget is voor één ding, is dit het eerste dat we zouden doen — het is het enige openstaande punt waarvan we de datum kunnen noemen waarop het zichtbaar misgaat, en dat is 19 december 2026.

**Bijgewerkt 19 augustus 2026: gebouwd, op beslissing van Kwinten, vooruitlopend op je antwoord.** De wijzigingsprocedure vraagt normaal eerst een schriftelijke bevestiging; hier woog de harde datum zwaarder dan de procedure, en die afweging is dezelfde dag genomen, gebouwd, getest en gedocumenteerd. Het scherm staat live (menu-item "Sluitingsdagen", boven Prognose), het werkt end-to-end tegen de database, en de eerdere lijst uit het bestand is eenmalig overgenomen zodat de kalender niet leeg begint. De vraag verschuift daarmee van "mag dit gebouwd worden?" naar **een bevestiging achteraf**: akkoord dat dit binnen de opdracht valt (1 dag bouwtijd, onder de raming van 1,5), of hoort het wat jou betreft buiten de afrekening? En los daarvan blijft vraag 64 gewoon staan — de datums zelf — nu als twee klikken per rij op het nieuwe scherm.

---

## 25 augustus 2026 — vraag 66: één proefexport van drie dagen uit Partner Hub, vóór de volledige download

**De vraag, in één handeling:** kan Sophie in Partner Hub → Reports **één bereik van drie dagen** trekken, van **beide** rapporttypes (Items Sold én Orders), en die twee CSV's doorsturen? Drie dagen, niet meer.

**Waarom dit apart gevraagd wordt, en vóór S1 afgerond is.** S1 vraagt de volledige twaalf maanden, en die vraag blijft onverkort staan — elke dag uitstel is een dag historiek die permanent weg is. Maar de vorm van de export bepaalt drie dingen die we nu niet weten, en één ervan bepaalt haar eigen werk:

1. Splitst Items Sold binnen één bereik **per dag** uit, of telt het over de periode op? Aggregeert het, dan moeten de rapporten per kalenderdag gedraaid worden — dat zijn ~365 downloads in plaats van 4, en dat wil ze weten vóór ze eraan begint en niet erna.
2. Dragen Items Sold en Orders een **gemeenschappelijke order-sleutel**? Die bepaalt of de commissie per artikel toegewezen kan worden (en de marge per product dus verdedigbaar is) of alleen per dag. Het verschil in bouwtijd is 0,5 tegen 1 à 1,5 dag.
3. Welke datumnotatie gebruikt het portaal? Partner Hub is Engelstalig, en `05/03` is 5 maart of 3 mei. Van de 365 dagen in een jaar zijn er 132 waarop een omwisseling een andere, even geldige datum oplevert — een fout die geen enkele parser uit zichzelf ziet.

De vorm van een export verandert niet met de lengte van het bereik, dus drie dagen volstaan. Het kost haar dezelfde handeling als één van de vier blokken.

**Wat wij intussen gedaan hebben.** Het deel van de parser dat niet van de exportvorm afhangt, staat er sinds 25 augustus: de foutklasse, de mappenconventie in code, de controle op dag/maand-omwisseling, en een `make deliveroo` die na elke download meldt of beide rapporttypes er zijn en waar de gaten in de twaalf maanden zitten. Het lezen zelf wacht bewust op echte bestanden; een parser op een bedachte CSV bouw je twee keer. Volledige vervolglijst in `docs/plan-deliveroo-parser.md`.

**Waar de bestanden heen moeten:** één submap per download, met het bereik in de mapnaam — `2025-08-25_2025-11-22/items-sold.csv` en `.../orders.csv`. Die mapnaam is geen administratie: het is het enige waarmee een omgewisselde datum te betrappen valt.

---

## 28 augustus 2026 — er is Deliveroo-data, en ze is anders dan verwacht

Op 27 augustus stuurde Mathias Joosten (Deliveroo) twee bestanden door, via Lien: `Renard Bakery - Blad1.pdf` en `Renard Bakery - Order Volume.pdf`. Ze zijn gelezen en nagerekend. Hieronder staat wat erin zit, wat er niet in zit, en de drie vragen die daaruit volgen.

**Dit komt langs een andere weg dan vraag 66 veronderstelde.** Die vraag gaat over een download die Sophie zelf uit Partner Hub trekt. Deze bestanden komen rechtstreeks van Deliveroo, en Mathias schrijft er expliciet bij: *"If not, please let me know what needs to be added or changed."* Dat is een openstaand aanbod, en het is op dit moment het goedkoopste pad naar wat we missen.

### Wat erin zit

Dertien maanden, **2025-08 tot en met 2026-08**, per maand, per artikel, per restaurant: de verkoopwaarde en het aantal stuks. Het tweede bestand geeft per restaurant per maand het aantal bestellingen en dezelfde verkoopwaarde. De twee documenten zijn onafhankelijk van elkaar nagerekend en sluiten op één uitzondering na (zie vraag 69) tot op de euro.

| | |
|---|---|
| Verkoopwaarde 13 maanden | € 864.391,95 |
| Waarvan 12 volle maanden (2025-08 t/m 2026-07) | € 857.042,40 |
| Artikelen | 295.445 |
| Bestellingen | 33.060 |
| Verschillende artikelen | 288 |

Ter verhouding: de winkelomzet uit Odoo over hetzelfde venster van twaalf maanden is € 4.320.789 exclusief btw. Deliveroo is dus grofweg een vijfde van de winkel — een orde van grootte groter dan TGTG, dat op € 106.416 over zeven jaar staat. Het is meteen het grootste kanaal dat het platform vandaag niet toont.

### Wat er niet in zit, en wat dat kost

1. **Geen dagniveau.** Alles is per maand opgeteld. Het kanaal kan daarmee wel in het kanaaloverzicht en in de maandcijfers, maar niet in de prognose en niet in een dagvergelijking. Het canonieke model draagt een datum per regel; een maand is die datum niet.
2. **Geen commissie en geen netto-uitbetaling.** Dit is de belangrijkste. Wat er staat is de verkoopwaarde vóór inhouding. Zonder de commissie blijft de marge op Deliveroo onbeschikbaar — en dan tonen we haar als onbeschikbaar mét reden, niet als schatting. Bij TGTG kennen we die wig wél, uit de maandfactuur.
3. **Geen btw-uitsplitsing.** De verkoopwaarde is wat de klant betaalt. Het canonieke veld heet `omzet_excl_btw`. Bij een bakkerij lopen 6 % (brood, gebak) en 21 % (dranken) door elkaar, dus dit is niet met één deling op te lossen. Dit is dezelfde onbeantwoorde vraag als bij TGTG, waar ze al als voorbehoud op het scherm staat.

### Vraag 67 — het bestand achter de print

**Kan Mathias hetzelfde overzicht als Excel of CSV sturen, in plaats van als PDF?**

Beide bestanden zijn afdrukken van een Excel-draaitabel — het tabblad heet nog `Blad1`. Een afdruk knipt: waar een getal niet in de kolom paste, is het laatste cijfer weggevallen. Concreet zijn drie aantallen afgekapt (`1,08` waar `1.080` hoort te staan, `1,68` waar `1.680` hoort, `1,33` waar `1.330` hoort) en in één maand ook de totaalregel zelf.

Wij hebben die vier met zekerheid kunnen terugrekenen, omdat het document zijn eigen maandtotalen draagt en er per maand precies één sluitende lezing overbleef. Maar dat werkt alleen zolang het om een handvol cellen gaat, en het is een omweg om een probleem op te lossen dat in het bronbestand niet bestaat. Eén antwoord van Mathias maakt de hele terugrekening overbodig.

**Dit is wel de kleine vraag, niet de grote.** De Excel repareert wat er mis is aan de bestanden die we al hebben; ze verandert niets aan wat er ontbreekt (dagniveau en commissie). De grote vraag staat verderop, bij "Wat wij aan Mathias zouden vragen": de twee Partner Hub-rapporten waar onze parser al op gebouwd is. Wordt er maar één ding gevraagd, vraag dan die twee.

### Vraag 68 — welke vestigingen zijn dit, en wat is hun verband met de drie kassa's?

In de data staan drie namen, en ze lossen elkaar af:

| Naam | Loopt van | Verkoopwaarde |
|---|---|---|
| Renard Bakery | 2025-08 t/m 2026-07 | € 815.162,54 |
| Renard Bakery Ixelles | vanaf 2026-07 | € 49.099,31 |
| Renard Bakery Uccle | vanaf 2026-08 | € 130,10 |

De meest voor de hand liggende lezing is dat de oorspronkelijke, naamloze Deliveroo-vermelding in juli 2026 hernoemd is naar Ixelles, en dat Ukkel er in augustus als tweede vermelding bij gekomen is — Ukkel staat pas op vijf bestellingen, dus dat is een start, geen vestiging met historiek. Maar dat is een lezing, geen gegeven.

Wat wij nodig hebben om het goed te modelleren:

- **Zijn de drie kassa's in Odoo (Kassa 1, 2 en 3) drie registers in één zaak, of drie vestigingen?** Ze draaien alle drie vanaf januari 2025 en zijn ongeveer even groot (€ 2,36 M / € 1,95 M / € 2,43 M). Deze vraag staat al open als vraag 18; de Deliveroo-namen maken haar dringender, want als het vestigingen zijn moeten de twee bronnen op elkaar gelegd worden.
- **Welke Deliveroo-vermelding hoort bij welke vestiging?**
- **En het punt dat Kwinten op 28 augustus aan Lien voorlegde:** de Renard-groep heeft meerdere winkels. Zitten daar zaken tussen die geen bakkerij zijn, dan mag hun omzet hier niet in. Op dit moment kunnen wij dat aan de data niet zien.

### Vraag 69 — de twee documenten spreken elkaar één keer tegen

In **juni 2026** zegt de artikellijst € 74.840,73 en het bestellingenoverzicht € 74.846. Een verschil van € 5,27 op € 74.800, dus 0,007 %.

Dat is geen leesfout van ons: onze som is exact gelijk aan de totaalregel die in de artikellijst zélf staat. De twee documenten van Deliveroo zijn het dus onderling oneens. Alle twaalf andere maanden komen wel overeen.

Het bedrag is verwaarloosbaar, de oorzaak niet: het betekent dat de twee rapporten niet op precies dezelfde filter draaien. Vóór we er een marge op bouwen, willen we weten welk rapport leidend is en waar het verschil vandaan komt. Dit is bij uitstek een vraag voor Mathias, die bij de bron kan kijken.

### Wat wij aan Mathias zouden vragen, in één bericht

Hij vraagt er zelf om, dus dit is het moment. En we hoeven het niet in eigen woorden te omschrijven: **er bestaan twee standaardrapporten in Partner Hub die precies zijn wat we nodig hebben, en onze code is er al op gebouwd.**

Vraag hem die twee, bij naam, als CSV, over de laatste twaalf maanden:

1. **`Items Sold`** — per dag, per artikel: categorie, artikel, aantal, prijs, subtotaal.
2. **`Orders`** — per bestelling, met de kolommen `Deliveroo commission` en `VAT on Deliveroo commission`.

Die twee vullen elkaar aan en geen van beide volstaat alleen: Items Sold weet wat er verkocht is maar niet wat het gekost heeft, Orders weet wat Deliveroo inhield maar niet waarop. Samen geven ze de netto-omzet per product per dag, en dat is het enige waarmee de marge op dit kanaal verdedigbaar wordt.

Daarnaast, in volgorde van belang:

3. **Dragen die twee rapporten een gemeenschappelijke order-sleutel?** Dit is vraag 66, en ze staat nog steeds. Mét sleutel kan de commissie per artikel toegewezen worden en is de marge per product verdedigbaar; zonder kan het alleen per dag, en is ze per product een benadering. Het verschil in bouwtijd is een halve tegen anderhalve dag.
4. **Een vestigingskenmerk per regel**, zodat de vermeldingen uit vraag 68 niet uit de naam gereconstrueerd hoeven te worden.
5. **De verklaring van het verschil in juni** (vraag 69).

**Waarom dit de goedkoopste weg is.** `bakkerij/sources/deliveroo_parse.py` staat sinds 25 augustus klaar en is op precies deze twee rapporten voorzien: `parse_items_sold` en `parse_orders` nemen de tekst van een CSV, en de datastructuren eronder (`Artikelregel`, `Orderregel`) dragen de velden hierboven al. Wat nog ontbreekt is het lezen zelf, en dat is bewust uitgesteld tot er een echt bestand ligt — een parser op een bedachte CSV bouw je twee keer.

Komt er iets anders dan deze twee rapporten, dan is het niet zo dat het onbruikbaar is, maar dan wordt het werk dat er ligt niet gebruikt en begint het opnieuw. Dat is de reden om het bij naam te vragen in plaats van te omschrijven wat we willen.

### Wat dit betekent voor vraag 66, en voor de API

Vraag 66 (de proefexport van drie dagen uit Partner Hub) **blijft staan, maar wordt tweede keus.** Levert Mathias dag- en commissiegegevens, dan is Partner Hub overbodig. Levert hij dat niet, dan is Partner Hub de enige bron die de commissie draagt, en dan is die vraag weer de eerste.

**De API blijft geen weg**, en dat is op 28 augustus opnieuw nagegaan bij de bron. Deliveroo biedt partners drie API-suites — Order, Menu en Site. Alle drie zijn operationeel bedoeld: bestellingen in real time, menu's bijwerken, openingsuren zetten. Er is **geen rapportage-, financiële, afrekenings- of historiek-API**. Wat wij nodig hebben — historiek en commissie — bestaat er domweg niet in. Dat bevestigt de beslissing van 12 augustus; er is niets veranderd door de overname door DoorDash.
