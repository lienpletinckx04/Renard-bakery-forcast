-- 003 | De dodemansknop van de ETL.
--
-- stack.md, "Twee risico's": de nachtelijke run is de zwakste schakel. De
-- planner van GitHub Actions is best effort en kan tientallen minuten later
-- vuren. Voor een dagelijks CFO-overzicht is dat aanvaardbaar -- maar alleen
-- als het platform kan tonen wanneer de cijfers voor het laatst ververst zijn.
--
-- "Een dashboard zonder datum is een dashboard dat je niet kan vertrouwen."
--
-- Deze tabel is de databasekant van wat `bakkerij/kwaliteit.py` lokaal al
-- doet. De ETL schrijft hier één rij per run: wanneer ze begon, wanneer ze
-- eindigde, of het goed ging, en hoeveel rijen ze wegschreef.
--
-- Let op de asymmetrie, want daar zit de hele werking in: `gestart_op` wordt
-- geschreven aan het BEGIN van de run, `geeindigd_op` aan het eind. Een run
-- die halverwege sterft laat dus een rij achter met `geeindigd_op is null` en
-- status 'bezig'. Dat is precies het signaal dat een dodemansknop moet geven:
-- niet de afwezigheid van een rij (die kan ook betekenen dat de cron nooit
-- gevuurd heeft), maar een run die begon en nooit afmaakte.

create table if not exists public.etl_run (
    id            bigint generated always as identity primary key,
    bron          text        not null,
    gestart_op    timestamptz not null default now(),
    geeindigd_op  timestamptz,
    status        text        not null default 'bezig'
                              check (status in ('bezig', 'goed', 'fout')),
    rijen         bigint,
    melding       text,

    -- Een run die klaar is, heeft een eindtijd. Een run die bezig is, niet.
    -- Deze constraint maakt het onmogelijk om per ongeluk een 'goed' weg te
    -- schrijven zonder eindtijd -- en dat is nu net de waarde die het
    -- platform toont.
    constraint etl_run_eindtijd_hoort_bij_status check (
        (status = 'bezig' and geeindigd_op is null)
        or (status <> 'bezig' and geeindigd_op is not null)
    )
);

-- De query die het platform doet is altijd dezelfde: wat is de jongste
-- geslaagde run per bron. Daar hoort deze index bij.
create index if not exists etl_run_bron_tijd_idx
    on public.etl_run (bron, gestart_op desc);

comment on table public.etl_run is
    'Eén rij per ETL-run. Een rij met geeindigd_op null en status bezig is een run die nooit afmaakte.';

comment on column public.etl_run.melding is
    'Foutmelding zonder data. Nooit rijen, nooit klantvelden -- deze kolom is leesbaar voor elke ingelogde gebruiker.';

alter table public.etl_run enable row level security;
alter table public.etl_run force row level security;

drop policy if exists "authenticated leest etl_run" on public.etl_run;
create policy "authenticated leest etl_run" on public.etl_run
    for select to authenticated using (true);

revoke all on public.etl_run from anon, authenticated;
grant select on public.etl_run to authenticated;
