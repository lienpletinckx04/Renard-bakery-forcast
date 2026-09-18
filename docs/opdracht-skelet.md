# Opdracht: het skelet van het platform

> **Uitgevoerd op 12 augustus 2026 — historisch document, niet meer volgen.** De route heet inmiddels `/prognose` (niet `/vooruitblik`), `platform/mock/` is verwijderd (14 aug), en `platform/proxy.ts` bestaat en draagt de toegangsbewaking.

_Compacte bouwopdracht, 12 augustus 2026. Bedoeld om in één keer uitgevoerd te worden, zonder dat de uitvoerder de rest van dit dossier moet lezen._

## Wat je bouwt

Het **skelet** van een CFO-platform voor een bakkerij: navigatie, layout, huisstijl, en alle schermen aanwezig maar leeg, gevoed door voorbeelddata uit een vaste JSON.

## Wat je niet bouwt

- **Geen echte data.** Er is geen databaseverbinding in deze opdracht. Alle cijfers komen uit `mock/` en zijn verzonnen.
- **Geen berekeningen.** Geen enkele som in de frontend. Geen `reduce` over cijfers, geen percentages uitrekenen, geen totalen optellen. Wat getoond wordt, staat al uitgerekend in de JSON. Dit is de belangrijkste regel van deze opdracht: de echte berekening gebeurt straks in een Python-laag, en alles wat de frontend zelf uitrekent, wijkt daar later van af.
- **Geen authenticatie-implementatie.** Wel een inlogscherm dat er staat en naar het dashboard doorstuurt.
- **Geen eigen kleuren, geen eigen lettertype, geen eigen iconenset.**
- **Geen extra schermen** die niet in de lijst hieronder staan.

## Stack

Versies exact pinnen. Ze zijn op 12 augustus 2026 geverifieerd; zie `stack.md` voor de onderbouwing.

| Pakket | Versie |
|---|---|
| `next` | **16.3.0**, App Router |
| `react` / `react-dom` | 19.x |
| `typescript` | 5.x |

Drie dingen waar handleidingen op internet je op het verkeerde been zetten:

- **Next 16 heeft `middleware.ts` hernoemd naar `proxy.ts`**, draaiend op de Node-runtime. In dit skelet is er nog geen authenticatie, dus je hebt hem nog niet nodig — maak hem niet aan
- Voeg **geen Supabase-pakketten** toe in deze opdracht. Er is geen database en geen login; alles komt uit `mock/`
- Voeg **geen grafiekbibliotheek** toe. Zie hieronder

Verder:

- **Tailwind** voor opmaak, met de tokens hieronder als thema
- **Geen zware grafiekbibliotheek.** De grafieken in dit skelet zijn eenvoudige inline SVG-componenten (lijn, staaf, sparkline). Reden: het platform toont weinig grafiektypes, de huisstijl is strak omlijnd, en een bibliotheek erbij halen levert vooral gevecht met haar standaardkleuren op.
- **Inter Tight** als lettertype, lokaal meegeleverd (variabel, gewicht 300–700). Niet via een externe CDN inladen.

## Huisstijl, niet onderhandelbaar

Uit de logogids van de klant.

```
--beige      #F4EDE6   het dragende vlak, achtergrond van de app
--bordeaux   #A6192E   merkaccent: koppen, actieve navigatie, eerste reeks in een grafiek
--geel       #F2F0A1   zacht accent, markeringen
--warmgrijs  #C9C0AF   lijnen, randen, rustige vlakken
--zwart      #000000   ALLE tekst en ALLE cijfers
--wit        #FFFFFF   kaarten en panelen op het beige vlak
```

Vier regels die het uiterlijk bepalen:

1. **Alle cijfers staan in zwart.** Ook stijgingen en dalingen. Een daling toont zich als `−4,2%` met een pijl omlaag, niet als een rood getal. Reden: het merk is rood, en in een financiële tool leest rood als verlies. Die twee kunnen niet naast elkaar bestaan.
2. **Bordeaux is identiteit, nooit betekenis.** Het is de kleur van het merk, niet van "slecht".
3. **Rustig en ruim.** Veel witruimte, dunne lijnen (1px in warmgrijs), geen kaders om alles heen, geen schaduwen, geen afgeronde hoeken groter dan 4px.
4. **Typografie doet het werk**, niet kleur: hiërarchie via gewicht en grootte van Inter Tight. Wijd gespatieerde kapitalen voor labels boven kerncijfers, zoals in het logo.

Donkere modus: **niet** in dit skelet. Het platform is een licht, beige product.

## Schermen

| Route | Naam | Inhoud |
|---|---|---|
| `/login` | Aanmelden | E-mail, wachtwoord, knop. Stuurt door naar `/`. Geen echte controle |
| `/` | Overzicht | Vier kerncijfers, omzetverloop over tijd, jaar-op-jaarvergelijking |
| `/kanalen` | Kanalen | Winkel, Too Good To Go, Deliveroo naast elkaar: aandeel, verloop |
| `/producten` | Producten | Tabel van top-producten en een verdeling per productgroep |
| `/marge` | Marge | Marge per kanaal en per groep. **Staat standaard in de onbeschikbaar-toestand** |
| `/vooruitblik` | Vooruitblik | Voorspelling per dag met een bandbreedte |
| `/instellingen` | Instellingen | Marges per productgroep invoeren, gebruikersbeheer. Formulieren zonder werking |

Navigatie links of bovenaan, met het woordmerk. Actief item in bordeaux.

## De onbeschikbaar-toestand

Dit is een eersteklas onderdeel van het ontwerp en geen randgeval. Verschillende cijfers zijn nog niet beschikbaar omdat de klant ze nog moet aanleveren of omdat een koppeling nog niet bestaat.

Zo'n cijfer wordt **nooit** getoond als nul, als streepje of als lege plek. Het krijgt een eigen weergave: het vak blijft staan, met een korte uitleg waarom er niets staat en wie erop wacht.

```
MARGE PER KANAAL
Nog niet beschikbaar
De brutomarges per productgroep zijn opgevraagd bij de bakkerij.
```

Bouw hiervoor één component, `Onbeschikbaar`, met een reden als eigenschap. Marge en Deliveroo gebruiken hem in het skelet.

## Vorm van de gegevens

Elk scherm haalt één JSON op, uit `mock/<scherm>.json`. De vorm ligt vast, want de echte API gaat straks exact dit teruggeven:

```json
{
  "versie": 1,
  "bijgewerkt_op": "2026-08-12T04:00:00+02:00",
  "bron": ["odoo", "tgtg"],
  "onbeschikbaar": [
    { "veld": "marge", "reden": "brutomarges nog niet aangeleverd" }
  ],
  "data": {}
}
```

Regels:
- `data` bevat uitsluitend **kant-en-klare** waarden. Geen ruwe reeksen waar de frontend nog iets uit moet halen.
- Alle bedragen zijn strings in centen of met twee decimalen — nooit een floating point getal waar de frontend nog mee rekent.
- `onbeschikbaar` stuurt rechtstreeks de `Onbeschikbaar`-component aan.
- `bijgewerkt_op` staat zichtbaar in de voettekst van elk scherm. Een dashboard zonder datum is een dashboard dat je niet kan vertrouwen.

Verzin voorbeelddata die plausibel is voor een bakkerij: dagomzetten in de orde van € 1.000 tot € 2.500, producten als `Croissant`, `Pain au chocolat`, `Desembrood`, `Pistolet`, `Cappuccino`. Gebruik **geen** echte cijfers uit dit dossier.

## Mappenstructuur

```
platform/
  app/
    (auth)/login/page.tsx
    (dash)/layout.tsx          navigatie + voettekst met bijgewerkt_op
    (dash)/page.tsx            overzicht
    (dash)/kanalen/page.tsx
    (dash)/producten/page.tsx
    (dash)/marge/page.tsx
    (dash)/vooruitblik/page.tsx
    (dash)/instellingen/page.tsx
  components/
    Kerncijfer.tsx             label in kapitalen + groot zwart getal + verschil met pijl
    Kaart.tsx                  wit paneel op beige
    Onbeschikbaar.tsx
    Lijngrafiek.tsx            inline SVG
    Staafgrafiek.tsx           inline SVG
    Tabel.tsx
    Navigatie.tsx
  lib/
    contract.ts                TypeScript-types van de JSON hierboven
    format.ts                  getallen en datums in Belgisch Nederlands
  mock/
    overzicht.json  kanalen.json  producten.json  marge.json  vooruitblik.json
```

`platform/` komt in de bestaande repo naast `bakkerij/` (de Python-kant). Raak niets aan buiten `platform/`.

## Opmaakregels voor cijfers

Belgisch Nederlands: `€ 1.234,56`, `12,3 %`, datums als `12 aug 2026`. Duizendtalpunt, decimale komma. Zet dit in `format.ts` en gebruik het overal — nooit `toLocaleString` los in een component.

## Klaar wanneer

- `npm run build` slaagt zonder waarschuwingen
- Alle zeven routes renderen, elk met voorbeelddata uit `mock/`
- Marge en Deliveroo tonen de `Onbeschikbaar`-component
- Geen enkele berekening in de frontend: geen `reduce`, geen `Math.round` op bedragen, geen percentages uitrekenen
- Geen kleur buiten de zes tokens
- Geen externe netwerkverzoeken, ook niet voor lettertypen
- Alle zichtbare tekst in het Nederlands

## Wat er daarna gebeurt (niet in deze opdracht)

De `mock/`-bestanden worden vervangen door echte API-antwoorden met exact dezelfde vorm. Daarom is de vorm hierboven bindend en de inhoud niet.
