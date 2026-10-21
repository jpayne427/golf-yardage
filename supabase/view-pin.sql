-- ShipStiffs: an optional view PIN per event (a private event).
-- Paste this whole script into Supabase > SQL Editor > Run. Safe to run again.
-- Run event-pins.sql and captain-pin.sql first (this builds on them).
--
-- With a view PIN set ('view:<event>' in private.settings), that event's scores, players and
-- matches can't be read at all without a PIN: the trip PIN, captain's PIN, organizer PIN or the
-- view PIN all open it. Events without a view PIN stay readable by anyone with the link, as before.
--
-- How it's enforced: row level security on public.docs only lets the public read rows of events
-- that have no view PIN. A private event's rows come through public.read_event(pin, event), which
-- checks the PIN first. Live updates (realtime) can't deliver private rows, so the app polls a
-- private event every few seconds instead.
--
-- Set or clear from the app (Setup > Event PINs, needs the organizer PIN), or here:
--   select public.set_pin('<organizer pin>', '<new view pin>', 'bandon-2026', 'view');
--   select public.set_pin('<organizer pin>', '', 'bandon-2026', 'view');   -- back to public

create or replace function private.view_ok(p_pin text, p_event text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select private.pin_level(p_pin, p_event) >= 1
      or exists (select 1 from private.settings
                 where k = 'view:' || p_event and coalesce(p_pin, '') <> '' and lower(v) = lower(trim(p_pin)))
$fn$;

-- True when the event this collection belongs to has no view PIN (readable by anyone).
create or replace function public.event_open(p_collection text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select not exists (select 1 from private.settings where k = 'view:' || private.event_of(p_collection))
$fn$;
grant execute on function public.event_open(text) to anon, authenticated;

create or replace function public.event_locked(p_event text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select exists (select 1 from private.settings where k = 'view:' || p_event)
$fn$;
grant execute on function public.event_locked(text) to anon, authenticated;

create or replace function public.view_ok(p_pin text, p_event text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select private.view_ok(p_pin, p_event)
$fn$;
grant execute on function public.view_ok(text, text) to anon, authenticated;

-- Everything in one event, for a phone that has a PIN that opens it.
create or replace function public.read_event(p_pin text, p_event text)
returns table (collection text, id text, data jsonb)
language plpgsql stable security definer set search_path = public, private as $fn$
begin
  if not private.view_ok(p_pin, p_event) then
    raise exception 'wrong pin' using errcode = '28000';
  end if;
  return query select d.collection, d.id, d.data from public.docs d where private.event_of(d.collection) = p_event;
end
$fn$;
grant execute on function public.read_event(text, text) to anon, authenticated;

-- Public reads only for events without a view PIN. Writes still go through write_doc.
alter table public.docs enable row level security;
drop policy if exists docs_public_read on public.docs;
create policy docs_public_read on public.docs for select to anon, authenticated using (public.event_open(collection));
grant select on public.docs to anon, authenticated;

-- set_pin now also takes role 'view'; an empty new PIN for 'view' removes it (the event goes public again).
create or replace function public.set_pin(p_admin text, p_new text, p_event text, p_role text default 'pin') returns text
language plpgsql security definer set search_path = private as $fn$
declare admin text := (select v from private.settings where k = 'admin_pin');
begin
  if admin is null or admin = 'CHANGE-ME' then return 'not_set_up'; end if;
  if lower(coalesce(p_admin, '')) is distinct from lower(admin) then return 'wrong_admin'; end if;
  if p_role not in ('pin', 'captain', 'view') then return 'bad_role'; end if;
  if coalesce(p_event, '') = '' then return 'no_event'; end if;
  if p_role = 'view' and length(trim(coalesce(p_new, ''))) = 0 then
    delete from private.settings where k = 'view:' || p_event;
    return 'cleared';
  end if;
  if length(trim(coalesce(p_new, ''))) < 4 then return 'too_short'; end if;
  insert into private.settings (k, v) values (p_role || ':' || p_event, trim(p_new))
    on conflict (k) do update set v = excluded.v;
  return 'ok';
end
$fn$;
grant execute on function public.set_pin(text, text, text, text) to anon, authenticated;
