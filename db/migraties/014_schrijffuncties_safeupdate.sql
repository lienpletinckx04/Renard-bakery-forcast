-- 014 | De twee schrijffuncties herdefinieerd: `delete ... where true` in
--       plaats van een kaal `delete`, want de gehoste route weigert dat.
--
-- WAT ER GEMETEN IS (19 aug 2026)
--
-- De eerste opslag vanaf het scherm Sluitingsdagen kwam terug met
-- `400 Bad Request {"code":"21000","message":"DELETE requires a WHERE
-- clause"}`. Supabase laadt op de PostgREST-verbinding de bibliotheek
-- pg-safeupdate, die elk delete zonder where-clausule weigert — óók
-- binnenin een security definer-functie, want de bibliotheek werkt per
-- sessie en niet per aanroeper. Een lokale Postgres (en de CI-container)
-- laadt die bibliotheek niet; daarom waren alle tests groen terwijl de
-- gehoste route stuk was.
--
-- Daarna nagemeten met een leeg model tegen de lege kostentabellen:
-- `bewaar_kostenmodel` (009) weigert op de gehoste route om exact dezelfde
-- reden. Dat was een latente productiebug: de eerste beheerder die het
-- kostenmodel via het formulier op Instellingen had opgeslagen, had "de
-- database weigerde de wijziging" gekregen. Nooit opgevallen, want de
-- kostentabellen zijn nog leeg — er heeft nog nooit iemand opgeslagen.
--
-- DE REPARATIE
--
-- `where true` is semantisch identiek aan geen clausule en stelt
-- pg-safeupdate tevreden: de bibliotheek eist een where, niet een
-- selectieve. De bedoeling van beide functies blijft onverkort "alles weg,
-- dan alles erin, in één transactie".
--
-- Een nieuwe migratie en geen wijziging aan 009/012: toegepaste migraties
-- zijn onveranderlijk (de checksum-vangrail in bakkerij/db/migratie.py).
-- Beide functies staan hier volledig opnieuw; het commentaar in de body is
-- ingekort, de volle onderbouwing staat in 009 en 012 en blijft daar gelden.

create or replace function public.bewaar_kostenmodel(model jsonb, door text)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    aantal_criteria integer;
    aantal_waarden  integer;
begin
    if door is null or btrim(door) = '' then
        raise exception
            'bewaar_kostenmodel: "door" is leeg; elke wijziging draagt de naam '
            'van wie hem deed (kolom bewaard_door).';
    end if;

    if model is null
       or jsonb_typeof(model -> 'criteria') is distinct from 'array'
       or jsonb_typeof(model -> 'waarden') is distinct from 'object' then
        raise exception
            'bewaar_kostenmodel: het model mist "criteria" (lijst) of '
            '"waarden" (object van groep -> criterium -> percentage).';
    end if;

    select count(*) into aantal_criteria
    from jsonb_array_elements(model -> 'criteria');
    if aantal_criteria > 12 then
        raise exception
            'bewaar_kostenmodel: % criteria; het kostenmodel draagt er '
            'hoogstens 12.', aantal_criteria;
    end if;

    if exists (
        select 1
        from jsonb_array_elements(model -> 'criteria') as e(waarde)
        where btrim(coalesce(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g'), '')) = ''
           or length(btrim(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g'))) > 60
    ) then
        raise exception
            'bewaar_kostenmodel: een criteriumnaam is leeg of langer dan 60 '
            'tekens.';
    end if;

    if exists (
        select 1 from jsonb_each(model -> 'waarden') as g
        where btrim(g.key) = ''
    ) then
        raise exception
            'bewaar_kostenmodel: een productgroep zonder naam kan geen kosten '
            'dragen.';
    end if;

    -- Alles weg, dan alles erin (zie 009). `where true` voor pg-safeupdate.
    delete from public.kosten_waarde where true;
    delete from public.kosten_criterium where true;

    insert into public.kosten_criterium (naam, omschrijving, volgorde, bewaard_door)
    select btrim(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g')),
           btrim(coalesce(e.waarde ->> 'omschrijving', '')),
           e.nr::integer,
           btrim(door)
    from jsonb_array_elements(model -> 'criteria')
             with ordinality as e(waarde, nr);

    insert into public.kosten_waarde (groep, criterium, pct, bewaard_door)
    select btrim(g.key),
           btrim(regexp_replace(k.key, '\s+', ' ', 'g')),
           (k.value #>> '{}')::numeric,
           btrim(door)
    from jsonb_each(model -> 'waarden') as g
             cross join lateral jsonb_each(g.value) as k;

    select count(*) into aantal_waarden from public.kosten_waarde;
    return aantal_waarden;
end;
$$;

create or replace function public.bewaar_sluitingskalender(kalender jsonb, door text)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    aantal_dagen  integer;
    aantal_regels integer;
begin
    if door is null or btrim(door) = '' then
        raise exception 'bewaar_sluitingskalender: "door" is leeg; elke '
            'wijziging draagt de naam van wie hem deed (kolom bewaard_door).';
    end if;

    if jsonb_typeof(kalender -> 'dagen') is distinct from 'array'
       or jsonb_typeof(kalender -> 'regels') is distinct from 'array' then
        raise exception 'bewaar_sluitingskalender: het document heeft de vorm '
            '{"dagen": [...], "regels": [...]}; een van beide lijsten ontbreekt.';
    end if;

    if jsonb_array_length(kalender -> 'dagen') > 1000 then
        raise exception 'bewaar_sluitingskalender: meer dan 1000 dagen; dat '
            'is geen sluitingskalender meer maar een vergissing.';
    end if;
    if jsonb_array_length(kalender -> 'regels') > 20 then
        raise exception 'bewaar_sluitingskalender: meer dan 20 wekelijkse '
            'regels; er zijn maar zeven weekdagen.';
    end if;

    if exists (
        select 1
        from jsonb_array_elements(kalender -> 'dagen') as e(waarde)
        where length(btrim(coalesce(e.waarde ->> 'reden', ''))) > 120
    ) or exists (
        select 1
        from jsonb_array_elements(kalender -> 'regels') as e(waarde)
        where length(btrim(coalesce(e.waarde ->> 'reden', ''))) > 120
    ) then
        raise exception 'bewaar_sluitingskalender: een reden is langer dan '
            '120 tekens; ze komt op een scherm terecht.';
    end if;

    if (select count(*) from jsonb_array_elements(kalender -> 'dagen') as e(waarde))
       <> (select count(distinct e.waarde ->> 'datum')
           from jsonb_array_elements(kalender -> 'dagen') as e(waarde)) then
        raise exception 'bewaar_sluitingskalender: dezelfde datum staat er '
            'meer dan één keer in; één uitspraak per dag.';
    end if;

    -- Alles weg, dan alles erin (zie 012). `where true` voor pg-safeupdate.
    delete from public.sluitingsdag where true;
    delete from public.sluitingsregel where true;

    insert into public.sluitingsdag (datum, toestand, reden, bron, bewaard_door)
    select (e.waarde ->> 'datum')::date,
           btrim(e.waarde ->> 'toestand'),
           btrim(regexp_replace(coalesce(e.waarde ->> 'reden', ''), '\s+', ' ', 'g')),
           btrim(e.waarde ->> 'bron'),
           btrim(door)
    from jsonb_array_elements(kalender -> 'dagen') as e(waarde);

    insert into public.sluitingsregel (weekdag, vanaf, tot, reden, bewaard_door)
    select (e.waarde ->> 'weekdag')::smallint,
           (e.waarde ->> 'vanaf')::date,
           (e.waarde ->> 'tot')::date,
           btrim(regexp_replace(coalesce(e.waarde ->> 'reden', ''), '\s+', ' ', 'g')),
           btrim(door)
    from jsonb_array_elements(kalender -> 'regels') as e(waarde);

    select count(*) into aantal_dagen  from public.sluitingsdag;
    select count(*) into aantal_regels from public.sluitingsregel;
    return aantal_dagen + aantal_regels;
end;
$$;

-- De rechten opnieuw, ook al vervangt `create or replace` de functie zonder
-- de grants te raken: dit bestand hoort net als 009/012 op zichzelf te staan.
revoke all on function public.bewaar_kostenmodel(jsonb, text) from public;
revoke all on function public.bewaar_kostenmodel(jsonb, text) from anon, authenticated;
grant execute on function public.bewaar_kostenmodel(jsonb, text) to service_role;

revoke all on function public.bewaar_sluitingskalender(jsonb, text) from public;
revoke all on function public.bewaar_sluitingskalender(jsonb, text) from anon, authenticated;
grant execute on function public.bewaar_sluitingskalender(jsonb, text) to service_role;
