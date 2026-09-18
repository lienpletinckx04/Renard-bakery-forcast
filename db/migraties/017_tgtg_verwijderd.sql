-- 017: Too Good To Go uit scope. Kanaal volledig verwijderd, historische
-- data inbegrepen.
--
-- Beslissing van de opdrachtgever (18 september 2026, zie dagboek.md): TGTG
-- draagt niets meer bij en wordt niet gebruikt. Dit is geen deactivatie maar
-- een uitdrukkelijk gevraagde volledige verwijdering, inclusief de
-- historische omzet -- 1.872 rijen in fact_verkoop (4 juli 2019 t/m 31 juli
-- 2026, € 106.415,75) en alle 83 rijen in fact_kanaalkost. Gemeten vóór
-- verwijdering; zie dagboek.md voor de exacte cijfers.
--
-- Idempotent: een tweede keer draaien verwijdert nul rijen, en de
-- constraint-vervanging is een no-op als 'tgtg' al niet meer toegelaten is.

delete from public.fact_verkoop where kanaal = 'tgtg';
delete from public.fact_kanaalkost where kanaal = 'tgtg';

alter table public.fact_verkoop
    drop constraint if exists fact_verkoop_kanaal_check;
alter table public.fact_verkoop
    add constraint fact_verkoop_kanaal_check check (kanaal in ('winkel', 'deliveroo', 'overig'));

alter table public.fact_kanaalkost
    drop constraint if exists fact_kanaalkost_kanaal_check;
alter table public.fact_kanaalkost
    add constraint fact_kanaalkost_kanaal_check check (kanaal in ('winkel', 'deliveroo', 'overig'));
