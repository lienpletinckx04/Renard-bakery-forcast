-- 015 | De postbus voor bronbestanden: een export die een mens downloadt, komt
--       via het platform in de database in plaats van op een schijf.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- Deliveroo geeft ons geen weg om de historiek automatisch op te halen. De
-- Order API is op 12 augustus 2026 uit het ontwerp geschrapt en die
-- beslissing staat: toegang op uitnodiging, dertig dagen historiek, en geen
-- commissie in wat ze teruggeeft — precies de drie dingen die we nodig
-- hebben (docs/plan-deliveroo-parser.md, "Wat er bewust niet gebeurt").
-- De historiek komt dus als export uit Partner Hub, gedownload door een
-- mens, en het venster van twaalf maanden schuift elke dag op: wat eruit
-- valt is nergens meer te halen.
--
-- Tot nu toe landde zo'n export op de schijf, onder
-- `data/raw/Deliveroo/<bereik>/`. Dat werkt op de laptop van wie het
-- uitzoekt, en nergens anders. Het platform draait op Vercel, en daar is
-- geen schijf die iets onthoudt: wat een verzoek wegschrijft, is bij het
-- volgende verzoek weg. De uitweg die zich aanbiedt — de server een bestand
-- in de git-repository laten schrijven — lost niets op: dat maakt van een
-- upload een commit, van de repo een gegevensopslag, en van elke oplading
-- een bouw. Wie het bestand wil bewaren op de enige plek die in de gehoste
-- omgeving blijft bestaan, komt bij de database uit.
--
-- Dit is de tegenhanger van dezelfde beweging bij het kostenmodel (009) en
-- de sluitingskalender (011/012): invoer die eerst een bestand in de repo
-- was, wordt iets dat de beheerder zelf kan doen. Het verschil is dat het
-- hier niet om een formulier gaat maar om een bestand.
--
-- DE BEWUSTE AFWIJKING VAN 002
--
-- `002_feiten.sql` legt vast dat ruwe bonregels en het verzekeringsextract
-- lokaal blijven, en noemt daarvoor twee redenen: privacy en kosten
-- ("miljoenen ruwe rijen in Postgres is precies wat het prijskaartje laat
-- ontsporen"). Die regel wordt hier niet stilzwijgend omzeild, hij wordt
-- verantwoord.
--
-- Het kostenargument gaat over miljoenen ruwe regels die per stuk bevraagd
-- worden. Hier gaat het om een handvol exports van enkele honderden
-- kilobytes. Elke export is precies één rij, en die rij wordt nooit per
-- regel bevraagd: de inlaadlaag haalt het bestand in zijn geheel op,
-- ontleedt het buiten de database, en schrijft het resultaat naar de
-- feitentabellen van 002. Er wordt in deze tabel dus nooit gerekend,
-- gejoind of geaggregeerd. Het is een postbus, geen feitentabel.
--
-- Om dat zo te houden staat er een harde grens op de grootte: 10 MB per
-- bestand, in een check op de kolom. Zonder die grens is "postbus" een
-- belofte in commentaar; met die grens is het een eigenschap van het schema.
-- Een jaar Deliveroo-export in vier blokken van 90 dagen zit daar met ruime
-- marge onder.
--
-- Het privacyargument raakt deze tabel niet anders dan de rest: de export
-- die hier binnenkomt is een rapport per artikel en per bestelling, geen
-- klantenlijst, en de harde grens uit scope.md blijft gelden — geen
-- klantvelden, niet in het schema en niet in wat de inlaadlaag eruit
-- overneemt.
--
-- WAT ER BEWUST NIET IN ZIT
--
-- Geen ontlede inhoud. Deze tabel bewaart het bestand zoals het aankwam en
-- niets daarnaast: geen kolommen, geen bereik, geen rapporttype. Wat er in
-- het bestand staat, weet `bakkerij/sources/deliveroo_parse.py`, en die
-- kennis hoort daar en niet op twee plekken. De drie verwerkt-kolommen
-- hieronder zijn het enige spoor van de verwerking, en ze zeggen alleen
-- óf en wanneer, nooit wat.
--
-- Geen tweede bron. `bron` staat vandaag op één waarde, inline in een check.
-- Wie er later een bij zet, doet dat in een eigen migratie in de stijl van
-- 013: constraint droppen, ruimer opnieuw zetten. Toegepaste migraties zijn
-- onveranderlijk (de checksum-vangrail in `bakkerij/db/migratie.py`), dus
-- een lijst die groeit hoort per definitie in een nieuw bestand.
--
-- Geen verwijderroute. Een export weggooien is een handeling met gevolgen —
-- het venster van twaalf maanden komt niet terug — en die hoort niet in een
-- functie te zitten die dagelijks draait.

create table if not exists public.bron_upload (
    upload_id       bigint generated always as identity primary key,
    -- Vandaag één waarde, inline. Zie "Geen tweede bron" hierboven.
    bron            text not null
                    check (bron in ('deliveroo')),
    bestandsnaam    text not null,
    mediatype       text not null,
    inhoud          bytea not null,
    -- De grens die van deze tabel een postbus houdt in plaats van een
    -- opslagplaats. Berekend uit het gedecodeerde bestand, nooit
    -- overgenomen van de aanroeper.
    bytes           integer not null
                    check (bytes > 0 and bytes <= 10485760),
    sha256          text not null
                    check (sha256 ~ '^[0-9a-f]{64}$'),
    geladen_door    text not null,
    geladen_op      timestamptz not null default now(),
    -- Leeg zolang de inlaadlaag het bestand nog niet heeft aangeraakt. Dat
    -- is een echte toestand en geen ontbrekende waarde.
    verwerkt_op     timestamptz,
    verwerkt_status text
                    check (verwerkt_status in ('gelukt', 'mislukt')),
    verwerkt_reden  text not null default '',
    -- Hetzelfde bestand twee keer opladen is een vergissing van de mens, geen
    -- tweede export. Zonder deze constraint staan er dan twee rijen die de
    -- inlaadlaag allebei verwerkt, en telt een blok van 90 dagen dubbel mee.
    -- De naam staat er expliciet omdat de functie hieronder ernaar verwijst.
    constraint bron_upload_bron_sha256_uniek unique (bron, sha256)
);

comment on table public.bron_upload is
    'Postbus voor bronbestanden die een mens downloadt en via het platform '
    'oplaadt, omdat de gehoste omgeving geen schijf heeft die iets onthoudt. '
    'Eén rij per bestand, nooit per regel bevraagd, hoogstens 10 MB per stuk; '
    'de ontleding gebeurt buiten de database en het resultaat gaat naar de '
    'feitentabellen van 002_feiten.sql. Bewuste afwijking van de regel daar '
    'dat ruwe invoer lokaal blijft — die regel gaat over miljoenen rijen.';

comment on column public.bron_upload.upload_id is
    'Technische sleutel, door de database toegekend; de aanroeper kiest hem nooit zelf.';
comment on column public.bron_upload.bron is
    'Van welk platform de export komt; bepaalt welke parser hem straks leest.';
comment on column public.bron_upload.bestandsnaam is
    'De naam zoals het bestand bij de beheerder heette, bewaard zodat een mens '
    'een oplading kan terugvinden zonder de inhoud te openen.';
comment on column public.bron_upload.mediatype is
    'Het door de browser gemelde type van het bestand, bewaard zoals het '
    'aankwam en niet als bewijs van de vorm gebruikt.';
comment on column public.bron_upload.inhoud is
    'Het bestand zelf, byte voor byte zoals het is opgeladen en niet ontleed.';
comment on column public.bron_upload.bytes is
    'De lengte van het gedecodeerde bestand in bytes, door de database zelf '
    'gemeten en begrensd op 10 MB.';
comment on column public.bron_upload.sha256 is
    'De hexadecimale SHA-256-afdruk die de inlaadkant bij het bestand meestuurde; '
    'ze dient om dezelfde export twee keer opladen te herkennen.';
comment on column public.bron_upload.geladen_door is
    'De naam van wie het bestand oplaadde; elke oplading draagt een naam.';
comment on column public.bron_upload.geladen_op is
    'Wanneer het bestand in de postbus kwam.';
comment on column public.bron_upload.verwerkt_op is
    'Wanneer de inlaadlaag dit bestand heeft verwerkt; leeg betekent nog niet verwerkt.';
comment on column public.bron_upload.verwerkt_status is
    'Of die verwerking lukte of mislukte; leeg zolang er niets geprobeerd is.';
comment on column public.bron_upload.verwerkt_reden is
    'Toelichting bij een mislukte verwerking, in mensentaal en leeg als er niets te melden valt.';

-- De enige vraag die de inlaadlaag stelt, staat hier letterlijk in: geef mij
-- de nog niet verwerkte bestanden van deze bron, oudste eerst. Een index op
-- de volle tabel zou meegroeien met de historiek terwijl het antwoord juist
-- krimpt naarmate er meer verwerkt is; deze index draagt alleen de wachtrij.
create index if not exists bron_upload_onverwerkt_idx
    on public.bron_upload (bron, geladen_op)
    where verwerkt_op is null;

-- --------------------------------------------------------------------------
-- De schrijfroute
-- --------------------------------------------------------------------------
-- Zelfde argument als bij 009 en 012: het platform praat via PostgREST, en
-- PostgREST kent geen meerstapstransactie. Eén functieaanroep is in Postgres
-- één transactie, en de vorm van het document ligt daarmee vast aan de kant
-- die hem ook afdwingt. `security definer` zodat de aanroeper zelf geen
-- tabelrechten nodig heeft; `set search_path = ''` sluit de bekende val van
-- definer-functies, dus alle tabellen hieronder staan volledig gekwalificeerd.
--
-- GEEN DELETE, EN DAT IS HET VERSCHIL MET 009 EN 012
--
-- Die twee vervangen een instelling: het document ís het kostenmodel, het
-- document ís de kalender, en dan is "alles weg, dan alles erin" de enige
-- eerlijke schrijfwijze. Een postbus werkt andersom — ze stapelt. Elke
-- export is een eigen ding dat naast de vorige komt te liggen, en een
-- oplading die de vorige zou wissen, wist een venster van twaalf maanden dat
-- niet terugkomt. Er staat hier dus bewust geen delete, en dat is geen
-- vergetelheid. Wie hier ooit toch een delete of update nodig heeft, schrijft
-- `where true`: de gehoste verbinding laadt pg-safeupdate en weigert een
-- kale delete, ook binnenin een definer-functie (zie 014).
--
-- OVER DE AFDRUK
--
-- De meegegeven sha256 wordt bewaard maar hier NIET nagerekend. Nakijken zou
-- `digest()` vragen, en die functie komt uit pgcrypto — een extensie die in
-- dit project nergens wordt aangezet. Er een extensie bij verzinnen om één
-- controle te kunnen doen, is een zwaarder besluit dan de controle waard is:
-- een extensie is schema-brede toestand die elke omgeving moet dragen, en
-- die keuze hoort niet in een migratie die eigenlijk over een postbus gaat.
-- De afdruk wordt daarom aan de inlaadkant berekend, waar het bestand toch al
-- volledig in het geheugen zit en `hashlib.sha256` gratis is — dezelfde
-- functie die `bakkerij/db/migratie.py` al voor de migratiechecksums gebruikt.
-- Wat de kolom hier doet is dan ook niet bewijzen dat het bestand gaaf is,
-- maar herkennen dat het er al staat: op die afdruk staat de uniciteit, en
-- twee keer dezelfde export opladen levert daardoor geen tweede rij op.
-- Wat de database wél zelf meet, is de lengte: `bytes` komt uit
-- `octet_length()` van het gedecodeerde resultaat en nooit uit het document,
-- want een lengte die de aanroeper meestuurt bewijst alleen wat de aanroeper
-- dacht.

create or replace function public.bewaar_bron_upload(upload jsonb, door text)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    inhoud_bytes bytea;
    aantal_bytes integer;
    aantal_rijen integer;
begin
    -- Wie oplaadt, tekent. Zelfde regel als bewaar_sluitingskalender.
    if door is null or btrim(door) = '' then
        raise exception 'bewaar_bron_upload: "door" is leeg; elke oplading '
            'draagt de naam van wie hem deed (kolom geladen_door).';
    end if;

    if upload is null
       or btrim(coalesce(upload ->> 'bron', '')) = ''
       or btrim(coalesce(upload ->> 'bestandsnaam', '')) = ''
       or btrim(coalesce(upload ->> 'mediatype', '')) = ''
       or btrim(coalesce(upload ->> 'sha256', '')) = ''
       or coalesce(upload ->> 'inhoud_base64', '') = '' then
        raise exception 'bewaar_bron_upload: het document heeft de vorm '
            '{"bron", "bestandsnaam", "mediatype", "sha256", "inhoud_base64"}; '
            'een van die vijf ontbreekt of is leeg.';
    end if;

    inhoud_bytes := decode(upload ->> 'inhoud_base64', 'base64');
    aantal_bytes := octet_length(inhoud_bytes);

    -- De check op de kolom vangt dit ook, maar in de taal van een constraint.
    -- Hier staat de reden in mensentaal, en dat is wat de beheerder leest.
    if aantal_bytes = 0 then
        raise exception 'bewaar_bron_upload: het bestand is leeg na decoderen; '
            'er is niets aangekomen om te bewaren.';
    end if;
    if aantal_bytes > 10485760 then
        raise exception 'bewaar_bron_upload: het bestand is % bytes; deze '
            'postbus draagt hoogstens 10 MB per bestand.', aantal_bytes;
    end if;

    -- Dezelfde export twee keer opladen is geen fout maar een niets-gebeurd:
    -- de beheerder heeft dan tweemaal op dezelfde knop gedrukt, en een
    -- foutmelding daarop zou hem laten zoeken naar iets dat er niet is. Het
    -- antwoord 0 zegt precies wat er gebeurde.
    insert into public.bron_upload
        (bron, bestandsnaam, mediatype, inhoud, bytes, sha256, geladen_door)
    values (btrim(upload ->> 'bron'),
            btrim(regexp_replace(upload ->> 'bestandsnaam', '\s+', ' ', 'g')),
            btrim(upload ->> 'mediatype'),
            inhoud_bytes,
            aantal_bytes,
            lower(btrim(upload ->> 'sha256')),
            btrim(door))
    on conflict on constraint bron_upload_bron_sha256_uniek do nothing;

    get diagnostics aantal_rijen = row_count;
    return aantal_rijen;
end;
$$;

comment on function public.bewaar_bron_upload(jsonb, text) is
    'Legt één opgeladen bronbestand in de postbus public.bron_upload en geeft '
    'het aantal ingevoegde rijen terug: 1 bij een nieuw bestand, 0 als '
    'dezelfde afdruk er voor die bron al ligt. Enige schrijfroute voor de '
    'gehoste omgeving, die via PostgREST werkt en dus geen meerstapstransactie '
    'kan. Stapelt en vervangt niet, ontleedt niets, en meet de lengte zelf.';

-- Zelfde toegangsregels als 011: alleen ingelogde gebruikers lezen, en
-- schrijven loopt uitsluitend via de functie hierboven. Er is daarom bewust
-- GEEN insert-, update- of delete-policy. Dat is geen omissie.
alter table public.bron_upload enable row level security;
alter table public.bron_upload force row level security;

drop policy if exists "authenticated leest bron_upload" on public.bron_upload;
create policy "authenticated leest bron_upload" on public.bron_upload
    for select to authenticated using (true);

revoke all on public.bron_upload from anon, authenticated;
grant select on public.bron_upload to authenticated;

-- De rechten voor service_role horen in dezelfde migratie als de tabel
-- (db/README.md, regel 4). Alleen select: schrijven kan uitsluitend via
-- bewaar_bron_upload, nooit rechtstreeks op de tabel.
--
-- Deze tabel heeft als enige een identity-kolom, en een rol die er
-- rechtstreeks in zou invoegen heeft daarvoor ook usage op de bijbehorende
-- sequence nodig. Die grant staat hier bewust NIET: er voegt niemand
-- rechtstreeks in. De functie draait als security definer, dus met de rechten
-- van de eigenaar, en die heeft de sequence al. Wie de grant er ooit "voor de
-- zekerheid" bij zet, geeft service_role precies de macht die de functie juist
-- inperkt.
grant select on public.bron_upload to service_role;

-- Publiek uitvoerrecht is de standaard voor een nieuwe functie, en bij
-- `security definer` is dat precies wat je niet wil: dan mag `anon` — de
-- publiceerbare sleutel, die in elke JavaScript-bundel zit — de postbus
-- vullen. Eerst alles weg, dan één rol erbij.
revoke all on function public.bewaar_bron_upload(jsonb, text) from public;
revoke all on function public.bewaar_bron_upload(jsonb, text) from anon, authenticated;
grant execute on function public.bewaar_bron_upload(jsonb, text) to service_role;
