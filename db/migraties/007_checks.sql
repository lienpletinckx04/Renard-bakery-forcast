-- 007: check-constraints die in 003 en 006 ontbraken.
--
-- Elke vergelijkbare kolom in dit schema legt zijn toegestane waarden vast
-- (kanaal in 002, status in 003, maand-formaat in 002). De sleutel van
-- contract_antwoord -- scherm x taal x winkel -- deed dat niet, terwijl het
-- platform er letterlijk op opvraagt: een typefout in de schermnaam of een
-- half ingevoerde derde taal levert een rij die niemand ooit leest, en een
-- scherm dat "draai de nachtelijke sync" zegt terwijl de sync net geslaagd
-- is. Zelfde verhaal voor etl_run.bron: een verschreven bronnaam laat de
-- poortwachter stilzwijgend niets vinden en de sync elke nacht volledig
-- draaien.
--
-- Een nieuwe migratie en geen wijziging aan 003/006: toegepaste migraties
-- zijn onveranderlijk (de checksum-vangrail in bakkerij/db/migratie.py).
--
-- De constraints krijgen een naam en een drop-vooraf zodat dit bestand, net
-- als de policies elders, op zichzelf herhaalbaar is.

alter table public.contract_antwoord
    drop constraint if exists contract_antwoord_scherm_bekend;
alter table public.contract_antwoord
    add constraint contract_antwoord_scherm_bekend check (scherm in
        ('overzicht', 'kanalen', 'producten', 'marge', 'prognose', 'stand', 'winkels'));

alter table public.contract_antwoord
    drop constraint if exists contract_antwoord_taal_bekend;
alter table public.contract_antwoord
    add constraint contract_antwoord_taal_bekend check (taal in ('nl', 'fr'));

alter table public.etl_run
    drop constraint if exists etl_run_bron_bekend;
alter table public.etl_run
    add constraint etl_run_bron_bekend check (bron in
        ('nachtelijke-sync', 'canoniek', 'contract'));
