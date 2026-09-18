-- 011 | De sluitingskalender: toekomstige sluitingen en bevestigde open dagen,
--       beheerd door de klant.
--
-- Vervangt de rol van config/sluitingsdagen.json als levende invoer. Dat
-- bestand werkte, maar het is een JSON-bestand in een git-repository, en de
-- zin op het prognosescherm — "vul de sluitingslijst aan en de prognose
-- volgt" — vroeg daarmee een handeling die een CFO per definitie niet kan
-- uitvoeren. Het bestand blijft bestaan als eenmalige invoer en als
-- historisch record (make db-sluitingen), precies zoals make db-kostenmodel
-- dat voor de kosten deed. Het volledige ontwerp: docs/sluitingskalender-ontwerp.md.
--
-- DRIE TOESTANDEN, TWEE IN DE TABEL
--
-- Het scherm kent per dag drie toestanden: bevestigd dicht, bevestigd open,
-- en nog niet beantwoord. Alleen de eerste twee zijn een uitspraak, en alleen
-- uitspraken worden bewaard: een dag die in geen enkele rij staat, ís de
-- derde toestand. Een expliciete rij "onbekend" zou dezelfde informatie
-- dubbel opslaan en kan dan van de werkelijkheid gaan afwijken.
--
-- "Bevestigd open" is echte informatie en geen vulsel: bij Renard is
-- 6 januari (galette) een van de drukste dagen van het jaar, en dat moet
-- iemand kunnen zeggen zonder dat het platform de feestdag als sluiting
-- behandelt. De prognose voorspelt een bevestigd-open dag gewoon; wat
-- verdwijnt is het voorbehoud "geen sluiting bekend" voor die dag.

create table if not exists public.sluitingsdag (
    datum           date primary key,
    toestand        text not null
                    check (toestand in ('dicht', 'open')),
    reden           text not null default '',
    -- Waar de uitspraak vandaan komt: een bevestigde feestdagkandidaat, een
    -- eigen periode (jaarlijkse sluiting, verbouwing), of de eenmalige
    -- overname uit config/sluitingsdagen.json. Het scherm groepeert erop.
    bron            text not null
                    check (bron in ('feestdag', 'periode', 'bestand')),
    bewaard_door    text not null,
    bewaard_op      timestamptz not null default now()
);

comment on table public.sluitingsdag is
    'Eén uitspraak van de beheerder per dag: de zaak is die dag dicht of '
    'juist bevestigd open. Een dag zonder rij is onbekend, en dat is een '
    'derde toestand en geen open. Beheerinvoer, geen brondata; de reden komt '
    'op het scherm en hoort dus zakelijk te blijven (geen namen, geen '
    'persoonlijke omstandigheden).';

comment on column public.sluitingsdag.toestand is
    'dicht = de prognose slaat de dag over; open = de dag wordt gewoon '
    'voorspeld en het voorbehoud "geen sluiting bekend" vervalt.';

create table if not exists public.sluitingsregel (
    -- 0 = maandag, zoals dim_kalender.weekdag en bakkerij/taal.dagnummer.
    weekdag         smallint not null
                    check (weekdag between 0 and 6),
    vanaf           date not null,
    -- Leeg = geldt tot nader order. Een vaste sluitingsdag als losse datums
    -- opslaan loopt per definitie een keer af — precies de fout die deze
    -- migratie repareert.
    tot             date,
    reden           text not null default '',
    bewaard_door    text not null,
    bewaard_op      timestamptz not null default now(),
    primary key (weekdag, vanaf),
    constraint sluitingsregel_tot_na_vanaf check (
        tot is null or tot >= vanaf
    )
);

comment on table public.sluitingsregel is
    'Een vaste wekelijkse sluitingsdag als regel: "elke maandag dicht, vanaf '
    'datum X", met een einddatum die leeg mag blijven. De meting kent dit '
    'patroon al voor het verleden (winkel_open volgt uit de kassa); de regel '
    'voegt toe dat het ook voor de toekomst geldt, en dat is precies het '
    'stuk dat de meting niet kan.';

-- Zelfde toegangsregels als het kostenmodel (005): alleen ingelogde
-- gebruikers lezen; schrijven loopt via de service-rol van de
-- berekeningslaag, en uitsluitend via de functie van migratie 012. Er zijn
-- daarom bewust GEEN insert-, update- of delete-policies. Dat is geen omissie.
alter table public.sluitingsdag enable row level security;
alter table public.sluitingsdag force row level security;
alter table public.sluitingsregel enable row level security;
alter table public.sluitingsregel force row level security;

drop policy if exists "authenticated leest sluitingsdag" on public.sluitingsdag;
create policy "authenticated leest sluitingsdag" on public.sluitingsdag
    for select to authenticated using (true);

drop policy if exists "authenticated leest sluitingsregel" on public.sluitingsregel;
create policy "authenticated leest sluitingsregel" on public.sluitingsregel
    for select to authenticated using (true);

revoke all on public.sluitingsdag from anon, authenticated;
revoke all on public.sluitingsregel from anon, authenticated;
grant select on public.sluitingsdag to authenticated;
grant select on public.sluitingsregel to authenticated;

-- De rechten voor service_role horen in dezelfde migratie als de tabel
-- (db/README.md, regel 4; 008 was de reparatie achteraf). Alleen select:
-- schrijven kan uitsluitend via bewaar_sluitingskalender (012), nooit
-- rechtstreeks op de tabel.
grant select on public.sluitingsdag   to service_role;
grant select on public.sluitingsregel to service_role;
