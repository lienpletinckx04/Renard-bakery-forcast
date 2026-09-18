-- 012 | De schrijfroute voor de sluitingskalender: één functie, één transactie.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- Migratie 011 zet de sluitingskalender in de database maar geeft niemand
-- schrijfrecht, en dat is met opzet: het platform op Vercel praat via
-- PostgREST, en PostgREST kent geen meerstapstransactie. Een scherm dat
-- eerst de oude rijen wist en daarna de nieuwe invoegt, kan tussen die twee
-- verzoeken falen — en dan is de sluitingskalender leeg en voorspelt het
-- platform omzet op elke dichte dag. Eén functieaanroep is in Postgres één
-- transactie: alles of niets, zonder dat de aanroeper iets van transacties
-- hoeft te weten. Zelfde argument en zelfde patroon als bewaar_kostenmodel
-- (009); dit is de derde toepassing van die keten.
--
-- WAAROM EEN FUNCTIE EN NIET GEWOON GRANTS
--
-- Een insert-grant op de tabel geeft de service-rol de macht om rijen te
-- schrijven in elke vorm die het schema toelaat. Deze functie is nauwer: ze
-- aanvaardt één document, toetst het in zijn geheel, en vervangt de hele
-- kalender in één beweging. De vorm van het document is daarmee op één
-- plek vastgelegd, aan de kant die hem ook afdwingt.
--
-- `security definer` hoort daarbij: de functie draait met de rechten van de
-- eigenaar, zodat de aanroeper zelf geen tabelrechten nodig heeft.
-- `set search_path = ''` sluit de bekende val van definer-functies (een
-- aanroeper die zijn eigen `public` vóór de echte zet); alle tabellen
-- hieronder staan daarom volledig gekwalificeerd. Types en ingebouwde
-- functies blijven werken: `pg_catalog` wordt altijd impliciet gezocht.
--
-- WAT DE FUNCTIE NIET DOET
--
-- Ze beslist niet wat een sluiting betekent. Het uitrollen van een periode
-- naar dagen, het samenvoegen met agenda en bestand, en het overslaan van
-- dichte dagen in het prognosevenster gebeurt in de berekeningslaag
-- (scripts/canoniek_bouw.py, bakkerij/canoniek.py). Deze functie bewaart
-- uitspraken, meer niet.

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
    -- Wie schrijft, tekent. Zelfde regel als bewaar_kostenmodel.
    if door is null or btrim(door) = '' then
        raise exception 'bewaar_sluitingskalender: "door" is leeg; elke '
            'wijziging draagt de naam van wie hem deed (kolom bewaard_door).';
    end if;

    if jsonb_typeof(kalender -> 'dagen') is distinct from 'array'
       or jsonb_typeof(kalender -> 'regels') is distinct from 'array' then
        raise exception 'bewaar_sluitingskalender: het document heeft de vorm '
            '{"dagen": [...], "regels": [...]}; een van beide lijsten ontbreekt.';
    end if;

    -- Vangrails die het schema niet kan zien. De grenzen spiegelen
    -- bakkerij/sluitingsdagen.py (REDEN_MAX = 120) en de gedachte achter
    -- MAX_PERIODES daar: ruim boven elk realistisch aantal (feestdagen plus
    -- sluitingsweken over meerdere jaren), en laag genoeg om een geplakt
    -- document met duizenden regels te weigeren. Toestand, bron, weekdag en
    -- de volgorde van vanaf/tot toetst het schema van 011 zelf.
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

    -- Twee uitspraken over dezelfde dag is er één te veel, en de primaire
    -- sleutel zou dat pas melden in de taal van een constraint. Hier staat
    -- de reden in mensentaal.
    if (select count(*) from jsonb_array_elements(kalender -> 'dagen') as e(waarde))
       <> (select count(distinct e.waarde ->> 'datum')
           from jsonb_array_elements(kalender -> 'dagen') as e(waarde)) then
        raise exception 'bewaar_sluitingskalender: dezelfde datum staat er '
            'meer dan één keer in; één uitspraak per dag.';
    end if;

    -- Alles weg, dan alles erin: het document ís de kalender. Een gerichte
    -- update zou moeten weten wat er veranderd is, en dat weet alleen het
    -- scherm — en het scherm is precies de plek die we niet vertrouwen met
    -- die verantwoordelijkheid. Binnen één functieaanroep is dit één
    -- transactie: faalt een insert (bijvoorbeeld op een check van 011), dan
    -- staat de oude kalender er nog.
    delete from public.sluitingsdag;
    delete from public.sluitingsregel;

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

comment on function public.bewaar_sluitingskalender(jsonb, text) is
    'Bewaart de volledige sluitingskalender (uitspraken per dag + wekelijkse '
    'regels) in één transactie: alles weg, dan alles erin. Enige schrijfroute '
    'voor de gehoste omgeving, die via PostgREST werkt en dus geen '
    'meerstapstransactie kan. Beslist niets over de prognose; het overslaan '
    'van dichte dagen gebeurt in bakkerij/canoniek.py.';

-- Publiek uitvoerrecht is de standaard voor een nieuwe functie, en bij
-- `security definer` is dat precies wat je niet wil: dan mag `anon` — de
-- publiceerbare sleutel, die in elke JavaScript-bundel zit — de
-- sluitingskalender overschrijven. Eerst alles weg, dan één rol erbij.
revoke all on function public.bewaar_sluitingskalender(jsonb, text) from public;
revoke all on function public.bewaar_sluitingskalender(jsonb, text) from anon, authenticated;
grant execute on function public.bewaar_sluitingskalender(jsonb, text) to service_role;
