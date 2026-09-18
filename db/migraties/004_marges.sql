-- 004 | De door de beheerder ingevulde brutomarges per productgroep.
--
-- Dit is de databasevorm van `data/config/marges.json`: de enige invoer in het
-- platform die niet uit een bronsysteem komt maar uit een formulier
-- (Instellingen -> Brutomarge per productgroep). Zolang S2 open staat, leeft
-- de invoer in dat bestand; zodra de database er is, neemt deze tabel het
-- 1-op-1 over en leest de berekening hieruit. Odoo heeft geen kostprijzen
-- (1.556.054 van de 1.556.770 bonregels op nul), dus zonder deze invoer
-- bestaat er geen marge (vraag 19).
--
-- Percentage als numeric, nooit double precision: een marge van 62,5% die als
-- float rondreist, is op het scherm een keer 62,499...

create table if not exists public.marge_instelling (
    groep           text        primary key,
    brutomarge_pct  numeric(5, 2) not null
                    check (brutomarge_pct >= 0 and brutomarge_pct <= 100),
    ingevuld_door   text        not null,
    ingevuld_op     timestamptz not null
);

comment on table public.marge_instelling is
    'Brutomarge per productgroep, ingevuld door een beheerder. Geen brondata.';

-- RLS in dezelfde migratie als de tabel, zoals overal (zie 001 voor waarom).
-- Ook hier geen insert/update/delete-policies: het wegschrijven loopt via de
-- rechtstreekse Postgres-verbinding van de server, nooit via PostgREST.
alter table public.marge_instelling enable row level security;
alter table public.marge_instelling force row level security;

drop policy if exists "authenticated leest marge_instelling" on public.marge_instelling;
create policy "authenticated leest marge_instelling" on public.marge_instelling
    for select to authenticated using (true);

revoke all on public.marge_instelling from anon, authenticated;
grant select on public.marge_instelling to authenticated;
