# De sluitingskalender: van een JSON-bestand naar een scherm

_Ontwerp, geschreven 19 augustus 2026 (nachtsessie). **Gebouwd op 19 augustus 2026**, op beslissing van Kwinten, vooruitlopend op het antwoord op vraag 65 — de harde datum van 19 december woog zwaarder dan de procedure, en vraag 65 is daarmee een bevestiging achteraf geworden. De bouw volgde dit document; de afwijkingen staan in de dagboekentry van 19 augustus (o.a.: het scherm werd een eigen menu-item boven Prognose in plaats van een blok op Instellingen, de uitspraken leest het scherm live uit de database in plaats van uit het contract, en migratie 014 repareerde een pg-safeupdate-weigering die ook het kostenmodel bleek te raken)._

## De aanleiding, in één gemeten zin

Op **19 december 2026** zet dit platform een gewone vrijdagomzet op **25 december**.

Dat is geen vermoeden. Het is nagerekend met de echte sluitingslijst en een kalender rond die datum:

```
prognosevenster vanaf 2026-12-20, horizon 7:
   VOORSPELD: 2026-12-21 (maandag)
   ...
   VOORSPELD: 2026-12-25 (vrijdag)     <- Kerstmis
   VOORSPELD: 2026-12-26 (zaterdag)
   VOORSPELD: 2026-12-27 (zondag)
   gepland gesloten: ()
```

Hetzelfde geldt voor 1 januari, Paasmaandag, 1 mei, 11 juli, 15 augustus en 1 november 2027.

## Waarom het vandaag zo werkt, en waarom dat geen bug is

Drie feiten, alle drie geverifieerd in de code:

1. **De kalender wéét dat 25 december een feestdag is.** `bakkerij/features/calendar.py` haalt de Belgische feestdagen uit de `holidays`-bibliotheek, voor elk jaar, onbeperkt vooruit. `feestdag`, `feestdagnaam`, `dag_voor_feestdag` en `brugdag` staan gevuld in elke kalenderrij.
2. **Het model gebruikt dat niet.** `bakkerij/model/productie.py` draait op `KENMERKEN = ("schoolvakantie",)`. Feestdag staat er bewust niet in, en dat is een gemeten keuze en geen vergetelheid: elke feestdagnaam komt hoogstens twee keer voor in de anderhalf jaar kassahistoriek (Odoo begint in 2025), en een factor die je op twee waarnemingen past, kun je nergens tegen toetsen. Harde regel 7 houdt hem daarom buiten.
3. **Het prognosevenster slaat alleen dagen over die gemeten-dicht zijn of vooraf als dicht zijn aangekondigd.** Aankondigen gebeurt via `config/sluitingsdagen.json`, en die lijst loopt tot en met **23 augustus 2026**.

Het platform liegt hier dus niet. Het zégt het zelfs, letterlijk, op het prognosescherm:

> "De sluitingslijst reikt tot 23 augustus 2026. Voor de dagen in dit venster daarná is geen sluiting bekend, en daar neemt de prognose aan dat de winkel open is. Dat is een aanname en geen meting: **staat er nog een sluiting op de planning, vul ze aan in de sluitingslijst en de prognose volgt.**"

En daar zit het eigenlijke probleem. **Die laatste zin is een instructie aan een CFO om een JSON-bestand in een git-repository te bewerken.** Het platform doet precies wat harde regel 8 vraagt — het toont het gat met de reden — en biedt vervolgens een oplossing aan die zijn lezer per definitie niet kan uitvoeren. Dat is geen eerlijkheid meer, dat is een doodlopende gang.

## Wat het oplost, en op welke niveaus

De vraag was of dit "op veel niveaus handig" is. Dat is het, maar niet overal even gratis. Eerlijk gescheiden:

**Wat meteen meekomt, zonder één regel extra werk** — het mechanisme bestaat al en wacht alleen op data:

| Niveau | Wat er verandert |
|---|---|
| **Prognose** | Geen omzetverwachting meer op een dag dat de zaak dicht is. Dat scheelt niet alleen een fout cijfer maar ook een fout weektotaal: vandaag telt 25 december gewoon mee in de som van zeven dagen |
| **Achterstandsmelding** | Een aangekondigde sluiting is geen achterstand. Dat onderscheid werkt al (`gepland_dicht` voedt `bakkerij/kwaliteit.py`), maar het werkt alleen voor dagen die in de lijst staan. Zonder onderhoud meldt élke toekomstige feestdag zich een dag of twee als achterstand, en dat is precies de alarmvermoeidheid die dit project overal elders bestrijdt |
| **De sluitingsstand op het scherm** | "De bakkerij is gesloten, eerste open dag is X" werkt vandaag alleen tijdens een sluiting die in de lijst staat |
| **Backtest en weekdaggemiddelden** | Voor het verleden al gedekt door de meting; met bekende toekomstige sluitingen blijft dat zo zodra die dagen verleden worden |
| **Fase 2** | Personeelsplanning, inkoop en de app hebben dit gegeven nodig. Het staat er dan al |

**Wat er níét gratis bij zit** en wat dus apart afgewogen moet worden:

- **Periodevergelijking.** Een week met een sluiting naast een week zonder is een oneerlijke vergelijking. Het platform kan dat pas zeggen als de vergelijkingslaag de sluitingen meeweegt. Dat is echt werk en hoort in een aparte afweging — noteren, niet meenemen.
- **Een briefingpunt** in de trant van "volgende week bent u twee dagen dicht, daarom ligt het weektotaal lager dan een gewone week". Klein, en het blijft binnen de grens van signalering (geen advies). Kandidaat voor daarna, niet nu.

## Het ontwerp

### Het dragende argument: dit is geen nieuw mechanisme

Het platform heeft al één beheerinvoer die precies deze vorm heeft, en die is af, getest en in productie: **het kostenmodel**. De keten daarvan is:

```
formulier op Instellingen (beheerder)
  -> server-actie valideert            (app/(dash)/instellingen/acties.ts)
  -> één security-definer-functie      (migratie 009, één verzoek = één transactie)
  -> tabellen in Postgres              (migratie 005)
  -> de canoniekbouw leest ze terug
  -> contract opnieuw -> scherm
```

De sluitingskalender is dezelfde keten met een andere tabel. Geen nieuw patroon, geen nieuwe bibliotheek, geen nieuwe laag. Dat is meteen het antwoord op de vraag of dit verse complexiteit introduceert: nee, het is de derde toepassing van iets wat er staat.

Waarom in de database en niet in het JSON-bestand: om exact dezelfde reden als bij het kostenmodel. Het platform op Vercel heeft geen git-toegang en geen Postgres-wachtwoord; het schrijft via PostgREST. Een formulier dat een bestand in de repo moet wijzigen, kan gehost niet bestaan. `config/sluitingsdagen.json` blijft wél staan als eenmalige invoer en als historisch record, precies zoals `make db-kostenmodel` dat voor de kosten deed.

### De vondst die het verschil maakt: bevestigen in plaats van invullen

Een leeg invoerscherm met een datumkiezer is een klus, en klussen gebeuren niet. Maar het platform **weet de kandidaten al**: de `holidays`-bibliotheek levert elke Belgische feestdag voor elk jaar.

Het scherm wordt daarom geen invoerformulier maar een **bevestigingslijst**:

```
SLUITINGSDAGEN — de komende twaalf maanden

  vr 25 dec 2026   Kerstmis              [ open ]  [ dicht ]  [ ? ]
  vr  1 jan 2027   Nieuwjaar             [ open ]  [ dicht ]  [ ? ]
  ma  5 apr 2027   Paasmaandag           [ open ]  [ dicht ]  [ ? ]
  za  1 mei 2027   Dag van de Arbeid     [ open ]  [ dicht ]  [ ? ]
  ...

  + een eigen periode toevoegen (jaarlijkse sluiting, verbouwing)
```

Twee klikken per rij, één keer per jaar. Dat is een handeling die wél gebeurt.

### Drie toestanden, niet twee

Dit is de kern, en het is een rechtstreekse toepassing van harde regel 8: **onbekend is niet hetzelfde als open.**

| Toestand | Wat de prognose doet | Wat het scherm zegt |
|---|---|---|
| `dicht` | slaat de dag over | "gesloten: Kerstmis" |
| `open` | voorspelt normaal | niets — dit is de gewone toestand |
| `onbekend` | voorspelt normaal | het huidige voorbehoud, maar nu **alleen voor deze dagen** |

Vandaag valt alles wat na 23 augustus komt in de derde categorie, en het voorbehoud geldt daarom voor het hele venster. Zodra een beheerder de feestdagen bevestigt, verdwijnt dat voorbehoud voor de bevestigde dagen en blijft het staan voor de rest. Het scherm wordt dus preciezer naarmate er meer bekend is — en het blijft eerlijk zolang er iets ontbreekt.

Let op wat dit níét doet: `open` is een bevestiging, geen aanname. Een bevestigde open feestdag is waardevolle informatie — bij Renard is 6 januari (galette) juist een van de drukste dagen van het jaar, en dat moet iemand kunnen zeggen zonder dat het platform het als sluiting behandelt.

### Een vaste sluitingsdag is een regel, geen lijst

Veel bakkerijen zijn één vaste dag per week dicht. Dat als losse datums opslaan loopt per definitie een keer af — precies de fout die we nu repareren. Het hoort als regel: *"elke maandag dicht, vanaf datum X"*, met een einddatum die leeg mag blijven.

De meting weet dit vandaag al voor het verleden (`winkel_open` volgt uit de kassa). De regel voegt toe dat het ook voor de tóekomst geldt, en dat is precies het stuk dat de meting niet kan.

### Wat er níét in moet

- **Geen openingsuren.** Het hele platform is dag-grofmazig. Een bakkerij die op 24 december om twaalf uur sluit, is een andere datavorm en een ander gesprek.
- **Geen halve dagen** om dezelfde reden.
- **Geen sluiting per kanaal.** TGTG is bevroren en Deliveroo bestaat nog niet als kanaal; dit gaat over de winkel.
- **Geen algemene herhalingsregels** (elke derde dinsdag, enzovoort). Eén wekelijkse sluitingsdag dekt de werkelijkheid; alles daarboven is een agenda-engine bouwen.
- **Geen vervanging van het agendaspoor.** De iCal-koppeling (vraag 46) blijft de aangewezen route zodra de bakkerij een echte agenda deelt; deze invoer is wat er moet zijn zolang die er niet is. De canoniekbouw kent de volgorde al: de agenda gaat vóór de handinvoer.

## Bouwplan

In deze volgorde; elke stap is los af en los te toetsen.

| | Stap | Raming |
|---|---|---|
| 1 | **Migratie 011**: tabel `sluitingsdag` (datum, toestand, reden, bron) en `sluitingsregel` (weekdag, vanaf, tot). RLS zoals de rest, `service_role` géén tabelrechten | 0,25 d |
| 2 | **Migratie 012**: één `security definer`-schrijffunctie, één verzoek is één transactie — exact het patroon van 009, met dezelfde test tegen een echte Postgres | 0,25 d |
| 3 | **De canoniekbouw leest de database** onder `CONTRACT_BRON=db`, met `config/sluitingsdagen.json` als eenmalige invoer en lokale terugval. De samenvoeging (agenda > database > bestand) staat al in `verwerk_sluitingen` | 0,25 d |
| 4 | **Het scherm**: bevestigingslijst op Instellingen, uit de `holidays`-kandidaten plus een vrije rij. Beheerder-only, tweetalig, huisstijl | 0,5 d |
| 5 | **De derde toestand in het contract**: het voorbehoud in `_kalenderreden` per dag in plaats van over het hele venster | 0,25 d |
| | **Totaal** | **1,5 dag** |

**De kleinste versie die al waarde heeft** is stap 1 tot en met 3 plus een eenmalige invoer via `make`: dan staan de sluitingen in de database en klopt de prognose, ook al moet een ontwikkelaar ze er nog in zetten. Dat is een halve dag en het haalt de fout van 25 december weg. Stap 4 is wat het duurzaam maakt — zonder scherm is het over een jaar weer verlopen.

## Scope

Dit valt buiten `scope.md`. Volgens de wijzigingsprocedure daar: noteren, ramen, schriftelijk laten bevestigen, en pas dán bouwen. Dat is vraag 65.

Twee dingen om eerlijk bij die vraag te zeggen:

- **Het blokkeert de oplevering van 27 augustus niet.** Het platform is vandaag eerlijk over wat het niet weet.
- **Het is wel het eerste wat ná de oplevering zichtbaar misgaat**, op een moment dat er niemand meer meekijkt. En de goedkope tussenoplossing — vraag 64, de sluitingsdagen één keer met de hand opvragen en invullen — lost het voor precies één jaar op, waarna dezelfde vraag terugkomt bij iemand die het project niet meer kent.
