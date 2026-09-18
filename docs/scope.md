# Scope fase 1

> Dit document is de spiegel van de overeenkomst. Als de overeenkomst iets anders zegt, wint de overeenkomst en wordt dit document aangepast, niet omgekeerd. Elke wijziging hier krijgt een datum en een reden.
>
> Status: **CONCEPT, derde herziening 18 augustus 2026.**
>
> **De baklijst is geschrapt.** De versie van 7 augustus leverde een baklijst met een dashboard erbij; de versie van 12 augustus leverde beide als twee sporen. Dit document vervangt allebei: fase 1 levert **één product, een CFO-platform**, met eigen toegang, een eigen database en koppelingen naar de bronsystemen. Het voorspelmodel blijft, maar als prognose binnen dat platform en niet als losse baklijst. Beslist door de opdrachtgever op 12 augustus, zie `beslissingen.md`.
>
> **Derde herziening, 18 augustus.** Dit document liep zes dagen achter op vier beslissingen die elders al genomen en genoteerd waren; ze staan nu ook hier, want dit is het contractuele spiegeldocument. (1) **Marges zijn een add-on geworden, geen fase 1** — de kostprijsdata bestaat niet bij de klant (vraag 19, herzien 12 aug); het margescherm staat in fase 1 in de onbeschikbaar-staat met die reden, en de invoer (het kostenmodel) is gebouwd zodat de klant hem kan vullen zodra hij wil. (2) **TGTG bevriest op de historiek t/m juli 2026** — de ingestmailbox is op 17 aug geschrapt op vraag van de opdrachtgever (blok 9); het platform toont per kanaal tot wanneer de data loopt. (3) **Het hostingmodel is beslist** (vraag 40): Renard is een project binnen de Supabase-organisatie en het Vercel-team van asklien.ai, verrekend via het onderhoudsabonnement — niet op naam van de eindklant, zoals de eerdere tekst hier voorstelde. (4) **De prognose per product staat niet op een scherm** — zie D8 hieronder; dat stond al zo in `oplevering.md` en staat nu ook hier.

## Wat we bouwen

Een financieel stuurplatform voor de bakkerij, waarop de zaakvoerder en de CFO zien wat er verkocht wordt, tegen welke marge, via welk kanaal, en wat er de komende dagen aankomt.

Het platform staat niet op een laptop en is geen rapport dat iemand doorstuurt. Het is een toepassing met een login, een database die dagelijks bijwerkt uit de bronsystemen, en een presentatielaag die in de huisstijl van het merk staat. In een latere fase komt daar een mobiele app op, en daar wordt nu al voor gebouwd.

Wat het uitdrukkelijk **niet** is: een tweede versie van de Odoo-rapportering. Het onderscheid zit in de kanalen die Odoo niet kent (TGTG, Deliveroo), in de marge die Odoo niet berekent, en in de prognose die Odoo niet heeft. Twee van die drie zijn sinds 12 augustus smaller dan gehoopt: de marge wacht op invoer van de klant (add-on), en Deliveroo wacht op de export (vraag 36/49). Wat overblijft is TGTG als extra kanaal plus de gebackteste prognose — dat gesprek is in vraag 49 expliciet benoemd.

## De lagen

```
BRONNEN            Odoo (XML-RPC)   TGTG (pdf-dump)   Deliveroo (export)
      |
INLAADLAAG         ophalen, normaliseren naar het canonieke datamodel, herbruikbaar en herhaalbaar
      |
DATABASE           Postgres. Feiten per dag, per product, per kanaal. Bron van waarheid voor alles erboven
      |
BEREKENING         nachtelijk: aggregaties, jaar-op-jaar, marge, en de prognose
      |
API / CONTRACT     genummerde, gedocumenteerde JSON-antwoorden. Klein en voorgeaggregeerd
      |
TOEGANG            login, sessies, rollen
      |
PRESENTATIE        web-UI in de huisstijl.  (fase 2: mobiele app op dezelfde API)
```

De regel die deze opbouw draagt: **de UI rekent nooit.** Alles wat een scherm toont, is in de berekeningslaag uitgerekend en via het contract opgehaald. Dat is wat de app later mogelijk maakt zonder verbouwing, en het is ook wat maakt dat een cijfer op het scherm hetzelfde cijfer is als in een export.

## Wat er geleverd wordt

| # | Deliverable | Klaar wanneer |
|---|---|---|
| D1 | **Data-audit** | **Geleverd 7 aug, hercontrole 12 aug.** Alle blokken beantwoord met gemeten cijfers |
| D2 | **Inlaadlaag** | Odoo en TGTG landen in het canonieke datamodel, met tests. Deliveroo zodra de export er is |
| D3 | **Database** | Postgres met het datamodel, migraties in de repo, herbouwbaar met één commando |
| D4 | **Nachtelijke berekening** | Eén run bouwt alle afgeleide tabellen opnieuw op uit de feiten. Draaiboek erbij |
| D5 | **API en contract** | Elk scherm leest uit een genummerd JSON-contract, met tests op de vorm |
| D6 | **Toegang** | Login met benoemde gebruikers, sessies, en twee rollen: lezer en beheerder |
| D7 | **Web-UI** | Kerncijfers, tijdreeks, periodevergelijking, top-producten, kanaalverdeling, prognose. In de huisstijl. Het margescherm bestaat maar staat in de onbeschikbaar-staat tot de klant het kostenmodel invult (herzien 18 aug; marges zijn een add-on) |
| D8 | **Prognose** | Dagprognose met onzekerheidsband plus prognose per categorie, met baselines, rolling-origin backtest en een eerlijk rapport over wat ze wel en niet kan. **Per product per dag is een backtestbevinding (20,2% WAPE), geen scherm**: zonder marges is er geen beslissing die dat cijfer draagt (herzien 18 aug; zo stond het al in `oplevering.md`) |
| D9 | **Opleverdocument** | Waar komt elk cijfer vandaan, wat toont het platform niet, en hoe wordt het beheerd |

## Waar de database hangt

**Beslist (vraag 40, bevestigd 12 augustus; project aangemaakt 14 augustus).** Supabase, project binnen de organisatie van asklien.ai, regio `eu-north-1` (Stockholm, EU), naast een Vercel-project in haar team. Op naam en rekening van asklien.ai, verrekend via het onderhoudsabonnement aan de eindklant. Het eerdere voorstel hieronder — infrastructuur op naam van de eindklant — is daarmee vervallen; de juridische kant van het gekozen model (verwerkersovereenkomst Lien↔Renard, exitregeling in het abonnement) staat in vraag 41 en is nog te regelen vóór de livegang.

De afweging van 12 augustus, ter referentie:

| | Beheerde omgeving (Supabase of gelijkwaardig) | Eigen kleine server |
|---|---|---|
| Postgres | inbegrepen | zelf te installeren |
| Login | inbegrepen | zelf te bouwen |
| Nachtelijke taak | cron of edge function | cron |
| Kost | maandelijks abonnement | enkele euro's per maand |
| Opzetwerk | een halve dag | anderhalve dag |
| Beheer nadien | door de leverancier | door ons of door de klant |

**Dit raakt een eerdere beslissing en dat moet expliciet.** Op 7 augustus is vastgelegd dat klantdata op één machine blijft en niet naar een gehoste omgeving gaat. Een platform met een login kan daar per definitie niet aan voldoen: de cijfers moeten staan waar de gebruiker ze kan bereiken. Die beslissing wordt hiermee herzien, met drie voorwaarden:

1. De omgeving staat in een EU-regio.
2. Er is een verwerkersovereenkomst met de leverancier. De infrastructuur staat op naam van asklien.ai (vraag 40, herzien 18 aug — het oorspronkelijke "op naam van de eindklant" is vervangen door het abonnementsmodel), met de exitregeling van vraag 41 als voorwaarde vóór de livegang.
3. Wat er in de database komt, blijft geaggregeerde productverkoop. **Geen klantgegevens uit Odoo**, precies zoals de extractie ze vandaag al nooit opvraagt.

Let op: zodra er benoemde gebruikers inloggen, verwerken we wél persoonsgegevens — die van de gebruikers, niet die van de klanten van de bakkerij. Dat is klein maar het bestaat, en het hoort in het verwerkingsregister van de eindklant.

## Toegang

Fase 1 gaat uit van een handvol benoemde gebruikers, geen zelfregistratie, geen SSO.

- E-mail plus wachtwoord, wachtwoordherstel per mail
- Twee rollen: **lezer** (ziet alles, wijzigt niets) en **beheerder** (beheert gebruikers en instellingen zoals marges)
- Sessies verlopen; uitloggen kan
- Elke aanmelding wordt gelogd, zodat achteraf te zien is wie wat wanneer bekeken heeft

Alles daarboven — SSO, tweefactor, fijnmazige rechten per scherm, meerdere vestigingen met eigen gebruikers — is een eigen fase.

## De koppelingen

| Bron | Hoe | Frequentie | Stand |
|---|---|---|---|
| **Odoo** | XML-RPC, altijd een volledig extract met een poortwachter op `write_date` (beslist 17 aug: een dag die half opnieuw wordt opgehaald en geüpsert zou het dagtotaal stil corrumperen, zie `beslissingen.md`) | nachtelijk | Toegang werkt op preprod. Productie geblokkeerd op een betalende licentie (G6) |
| **TGTG** | geen API. Pdf-dump uit het partnerportaal, geparst | **bevroren op de historiek t/m juli 2026** (blok 9 geschrapt op vraag van de opdrachtgever, 17 aug); het platform toont per kanaal tot wanneer de data loopt | **Binnen**: zeven jaar, 250 pdf's |
| **Deliveroo** | export uit het partnerportaal in fase 1; API pas als er een reden voor is | eenmalig twaalf maanden, daarna te bekijken | **Niets ontvangen** (G4, vraag 36/49 — het twaalfmaandsvenster schuift dagelijks op) |
| **Weer** | Open-Meteo, geen sleutel nodig | — | fase 2 |

Over TGTG: er ís geen publieke API, dus dit blijft handwerk aan de kant van de bakker. Dat is geen tekortkoming van het platform maar een eigenschap van het kanaal, en het hoort zo in het opleverdocument te staan.

Over Deliveroo: het traject dat in het gesprek van 7 augustus beschreven is — partnergoedkeuring, Engelstalig, kostprijs — gaat over de **API**. Voor fase 1 volstaat een export uit het partnerportaal, en die kan de bakker zelf downloaden zonder goedkeuringstraject. Dat is de vraag die gesteld moet worden vóór iemand aan een integratie begint.

## Alle drie de kassa's

**Herzien op 12 augustus 2026 na meting. De vorige tekst hier zei dat alleen de kassa van de bakkerij in scope zat en dat de andere twee vermoedelijk andere concepten van Renard Foods waren. Dat is weerlegd.**

De vier toetsen zijn uitgevoerd (`scripts/kassa_analyse.py`, data-audit addendum 3) en wijzen alle vier dezelfde kant op: de drie kassa's verkopen hetzelfde bakkerijassortiment in vrijwel dezelfde verhoudingen, met een vrijwel gelijke bongrootte (mediaan € 7,15 / € 7,50 / € 7,95) en een tot op het procentpunt identiek uurprofiel. Op 530 van de 539 verkoopdagen waren er twee of meer tegelijk actief binnen hetzelfde uur, op 509 dagen alle drie. Het zijn drie fysieke registers naast elkaar in één vestiging.

**Gevolg voor de scope: alle drie tellen mee en worden opgeteld.** Filteren op één kassa zou ongeveer tweederde van de bakkerijomzet weggooien — het omgekeerde van wat de vorige tekst voorschreef. `filiaal_id` blijft als dimensie in het datamodel bestaan, zodat een tweede vestiging later een rij is en geen verbouwing, en zodat uitsplitsen een rapportagekeuze blijft.

**Vraag 18 is gesloten.** De opdrachtgever heeft op 12 augustus 2026 bevestigd: drie kassa's, één winkel. Dit is geen werkhypothese meer en wordt niet opnieuw in twijfel getrokken. Eén waarschuwing die uit de meting volgt: het derde register kwam pas half januari 2025 in gebruik (17 dagen zonder rijen, waarvan 14 aaneensluitend aan de start). De dagtotalen zijn daar volledig — het volume zat op de andere twee — maar een rapportage *per kassa over tijd* zou daar veertien valse nullen tonen.

## Wat er uitdrukkelijk NIET in fase 1 zit

- **De baklijst en de beslislaag.** Geschrapt op 12 augustus. Het denkwerk blijft in `model-ontwerp.md` staan omdat het de waarde van een latere fase bepaalt, maar het wordt in fase 1 niet gebouwd.
- **De mobiele applicatie.** Fase 1 bouwt de API waar ze op aansluit, niet de app.
- **Notificaties en herinneringen.**
- **AI-uitleglaag** die de cijfers in natuurlijke taal duidt.
- **Deliveroo-integratie via API.** Fase 1 werkt op export.
- **TGTG-automatisering.** Er is geen API; de dump blijft handwerk.
- **Weer- en locatiedata.**
- **Koppeling met het bestelsysteem.**
- **Meerdere vestigingen** met eigen gebruikers en eigen cijfers.
- **SSO, tweefactor, fijnmazige rechten.**
- **Hertraining, onderhoud, monitoring.** Eigen afspraak, eigen tarief.
- **Opleiding van de eindklant.**
- **Boekhoudkundige rapportering.** Het platform toont verkoop en marge uit operationele data. Het is geen vervanging van de boekhouding en sluit niet aan op een resultatenrekening.

## De poorten

| | Poort | Blokkeert | Stand 18 aug |
|---|---|---|---|
| G1 | Brutomarge of kostprijs per productgroep | elke margeweergave in D7 | **Gesloten als add-on** (12 aug, herziening vraag 19): de data bestaat niet bij de klant. De invoer (het kostenmodel op Instellingen) staat klaar; het margescherm toont onbeschikbaar tot iemand hem vult (vraag 50/51) |
| G2 | Welke kassa is de bakkerij | het hele datamodel | **Gesloten 12 aug**: drie registers in één vestiging, gemeten en bevestigd. Alle drie tellen mee |
| G3 | TGTG-export | kanaal `tgtg`, restwaarde | **Binnen en geparst 12 aug**: 250 pdf's, kanaal draait. Bevroren t/m juli 2026 sinds het schrappen van blok 9 (17 aug) |
| G4 | Deliveroo-export | kanaal `deliveroo`, volledig kanaaloverzicht | **Open — het urgentste punt van het project** (S1, vraag 36/49): het twaalfmaandsvenster schuift dagelijks op |
| G5 | Synchroniseert de preprod met productie | de nachtelijke koppeling | **Open.** Vraag 27, aanname A14; beantwoordt zichzelf na de heropening (23 aug) |
| G6 | Betalende Odoo-licentie voor productie | oplevering op echte data | **Open.** Vraag 22 |
| G7 | Waar de database komt te staan, op wiens naam | D3 en alles erboven | **Beslist en aangemaakt** (vraag 40, project 14 aug). Opgevolgd door S11: het databasewachtwoord, de enige resterende blokkade van de databasetrack |
| G8 | Wie krijgt toegang, en hoeveel mensen | D6 | **Open.** Vraag 29/57 (S13): de gebruikerslijst |

Van de acht poorten staan er nog vier open; de actuele blokkadelijst met eigenaars staat in `todo.md` (S-nummers), en dat is de enige lijst die bijgehouden wordt.

## Raming

**Dit is de aanvangsraming van 12 augustus**, ter bevestiging voorgelegd in vraag 28 en bevestigd. Ze wordt hier niet bijgewerkt; de actuele reststand per blok staat in `todo.md`.

| Onderdeel | Dagen |
|---|---|
| D2 inlaadlaag, inclusief het parsen van 250 TGTG-pdf's | 2 tot 3 |
| D3 database en migraties | 1 |
| D4 nachtelijke berekening | 1 tot 2 |
| D5 API en contract | 1 tot 2 |
| D6 toegang en rollen | 1 |
| D7 web-UI in de huisstijl | 3 tot 4 |
| D8 prognose met backtest | 2 tot 3 |
| D9 opleverdocument | 0,5 |
| **Totaal** | **11,5 tot 16,5 dagen** |

Dat is een raming en geen vaste prijs. De bandbreedte wordt smaller zodra G7 beslist is en de eerste TGTG-pdf's geparst zijn: die twee dragen de meeste onzekerheid.

Ter vergelijking: de oorspronkelijke opzet van 7 augustus ging uit van vijf dagen voor een baklijst zonder platform. Dit is een ander product en een andere orde van grootte, en dat hoort schriftelijk bevestigd te zijn vóór er gebouwd wordt.

## Aannames waarop de raming rust

1. Werkende toegang tot Odoo. **Bevestigd op preprod, niet op productie (G6).**
2. Negentien maanden historiek op dag- en productniveau. **Bevestigd, gemeten.**
3. ~~Eén kassa in scope~~ **Gemeten en weerlegd op 12 aug (addendum 3 data-audit): alle drie de kassa's verkopen hetzelfde assortiment en tellen op tot één geheel. Vraag 18 is daarmee beantwoord; alleen de naamgeving (registers of vestigingen) staat nog open.**
4. De TGTG-pdf's hebben over de hele reeks dezelfde opbouw. **Gemeten en bevestigd 12 aug**: 250 pdf's, drie formaatvarianten, nul onleesbaar (aanname A16).
5. Marges per productgroep worden aangeleverd, of er wordt schriftelijk een benadering afgesproken. **Vervallen als fase-1-aanname (12 aug): marges zijn een add-on geworden (G1).**
6. Er is één contactpersoon die inhoudelijke vragen binnen één werkdag beantwoordt.
7. De omgeving draait in fase 1 zonder eis van hoge beschikbaarheid, met een handvol gebruikers en zonder SSO.
8. ~~De infrastructuur staat op naam en rekening van de eindklant~~ **Herzien (vraag 40): op naam van asklien.ai, via het onderhoudsabonnement, met de exitregeling van vraag 41 als voorwaarde.**

## Wijzigingsprocedure

1. Elke toevoeging wordt genoteerd in `vragen-aan-lien.md`.
2. Ze krijgt een inschatting in dagen.
3. Ze wordt schriftelijk bevestigd vóór er een regel code voor geschreven wordt.

"Kan je dat er even bijnemen" is geen bevestiging. Een bericht in de groep waarin staat wat het is en hoeveel dagen het kost, wel.

**De tweede herziening viel zelf onder die procedure**, in twee richtingen: de baklijst valt weg en het platform komt erbij. Vraag 28 vroeg om één bevestiging van beide, en die is er.

**Twee dingen staan nog open onder deze procedure, eerlijk genoteerd op 18 augustus:**

1. **Er is sinds 12 augustus meer gebouwd dan dit document beschrijft**: tweetaligheid NL/FR over het hele platform, de kostenmodel-invoer op Instellingen, de winkelindeling (meerdere vestigingen als config in plaats van verbouwing), de briefing bovenaan elk scherm, en de PDF-export van het CFO-rapport. Geen ervan is apart in dagen voorgelegd en schriftelijk bevestigd — ze zijn binnen de platformraming gebouwd. Vraag 58 legt ze alsnog ter bevestiging voor, zodat de aanvaarding op 27 augustus nergens op een verrassing rust.
2. **Vraag 7 en dit document spreken elkaar tegen over notificaties en de AI-uitleglaag.** Het antwoord van 12 augustus zegt dat beide wél in fase 1 zitten; de lijst "uitdrukkelijk NIET" hierboven zegt van niet, en er is geen raming en geen bevestiging die ze dekt. Dat verschil is nooit beslecht. Ook dat zit in vraag 58 — met ons voorstel: fase 2, want acht resterende werkdagen (18 aug, deadline-dag meegerekend; `todo.md` rekent het voor) dragen ze niet.

## Oplevering en aanvaarding

Fase 1 is aanvaard wanneer D1 tot en met D9 geleverd zijn zoals hierboven omschreven, draaiend op echte data, bereikbaar via een login.

Twee dingen staan hier expliciet omdat het de punten zijn waarop dit soort opdrachten in een conflict eindigt:

**Een geblokkeerd cijfer wordt getoond als onbeschikbaar, met de reden.** Niet geschat, niet stilzwijgend weggelaten. Een CFO-platform dat een marge toont die niemand heeft aangeleverd, is erger dan een platform dat geen marge toont.

**Aanvaarding van de prognose hangt niet af van de vraag of ze goed genoeg is naar de smaak van de eindklant.** Als de data de voorspelling niet draagt, is een eerlijk backtest-rapport dat dat aantoont de geleverde waarde.

---
*Aangemaakt 7 augustus 2026. Eerste herziening 12 augustus: CFO-platform toegevoegd naast de baklijst. Tweede herziening 12 augustus: baklijst geschrapt, platform is het product, database en toegang toegevoegd. Derde herziening 18 augustus: marges add-on, TGTG bevroren, hostingmodel vraag 40 verwerkt, D8 gelijkgetrokken met het opleverdocument, poortentabel geactualiseerd, en de onbevestigde uitbreidingen expliciet gemaakt (vraag 58).*
