# db/migraties — lees dit vóór je het volgende vrije nummer schrijft

De migratiediscipline staat volledig in `bakkerij/db/migratie.py` (de runner)
en verspreid in `docs/stack.md` en `docs/beheerdraaiboek.md`; dit bestand is
de samenvatting op de plek waar je kijkt vóór je een migratie toevoegt.

## De regels

1. **Nummering is sluitend en oplopend**: een nieuwe migratie krijgt het
   volgende vrije nummer, `<nnn>_<naam>.sql`, geen gaten, geen dubbele
   nummers. De runner weigert een duplicaat.
2. **Een toegepaste migratie wijzigt nooit meer.** De runner bewaart per
   migratie een checksum in `schema_migraties` en weigert een bestand dat
   achteraf is aangepast. Iets rechtzetten = een nieuwe migratie.
3. **Elke migratie is op zichzelf herhaalbaar**: `create table if not exists`,
   `create index if not exists`, `drop policy if exists` vóór elke
   `create policy`, genoemde constraints met `drop constraint if exists`.
   Tweede keer draaien is een lege run.
4. **RLS en rechten horen in dezelfde migratie als de tabel.** Een tabel
   zonder policy is met de publiceerbare sleutel leesbaar of erger; de les
   van `schema_migraties` zelf (RLS vergeten, gerepareerd 18 aug 2026) staat
   in `007` en in `docs/beslissingen.md`.
5. **Nooit data in deze map.** `*.sql` betekent in dit project "datadump" en
   is overal gitignored; déze map is de enige uitzondering (zie `.gitignore`)
   omdat hier uitsluitend schemadefinitie staat. Dat zo houden is wat de
   uitzondering rechtvaardigt.

## Draaien

```bash
make db-droog     # toont wat er zou draaien; geen verbinding, geen sleutels
make db-migreer   # past toe; vergt SUPABASE_DB_URL in .env (pooler, 5432)
```

De runner draait elke migratie in een eigen transactie en schrijft de
boekhouding in `schema_migraties`. CI draait `make db-droog` bij elke push,
zodat een kapotte nummering of checksum niet tot de eerstvolgende echte
migratie onzichtbaar blijft.
