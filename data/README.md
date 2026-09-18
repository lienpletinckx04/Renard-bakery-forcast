# data/

Deze map is volledig gitignored en blijft dat.

```
raw/         Exports zoals ontvangen. Nooit bewerken, nooit overschrijven.
interim/     Tussenstappen. Weggooibaar, altijd opnieuw te maken uit raw/.
processed/   Genormaliseerd naar het canonieke datamodel uit CLAUDE.md.
```

## Regels

1. **`raw/` is heilig.** Wat de klant stuurt, blijft zoals het is, met de originele bestandsnaam plus een datum. Elke bewerking is een script dat van raw naar interim gaat. Dat is het verschil tussen een resultaat dat je kan herhalen en een resultaat dat je kan verdedigen.
2. **Niets uit deze map gaat naar een LLM-context.** Kolomnamen, aantallen, datumbereiken en aggregaten mogen. Rijen niet.
3. **Niets uit deze map gaat naar een cloudschijf, een gedeelde map of een andere repository.**
4. **Bij oplevering** wordt afgesproken wat er met deze data gebeurt: verwijderen of overdragen. Dat gebeurt schriftelijk, en de bevestiging gaat in `docs/beslissingen.md`.

## Naamgeving

```
raw/2026-08-12_odoo_verkopen_2024-01-01_2026-08-11.csv
raw/2026-08-14_deliveroo_export_handmatig.csv
```

Datum van ontvangst voorop, bron, dan de inhoud met het bereik. Zes weken later weet je dan nog welk bestand welk is, en dat scheelt meer tijd dan het kost.
