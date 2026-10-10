-- ShipStiffs: a separate PIN for each event.
-- Paste this whole script into Supabase > SQL Editor > Run. Safe to run again.
--
-- Each event's PIN is stored as 'pin:<event>' in private.settings (e.g. 'pin:bandon-2026',
-- 'pin:redtail'). An event without its own PIN falls back to the old shared 'pin'.
-- The organizer PIN ('admin_pin') unlocks every event.
-- Running this copies the current shared PIN to Bandon and RedTail, so nothing
-- changes until you set a new PIN in an event's Setup tab.

insert into private.settings (k, v)
  select 'pin:' || e, v from private.settings, unnest(array['bandon-2026', 'redtail']) e where k = 'pin'
  on conflict (k) do nothing;

-- Which event a collection belongs to: 'redtail.cards' -> 'redtail'; un-prefixed -> Bandon.
create or replace function private.event_of(p_collection text) returns text
language sql immutable as $fn$
  select case when position('.' in p_collection) > 0 then split_part(p_collection, '.', 1) else 'bandon-2026' end
$fn$;

-- True when p_pin opens p_event (or, with no event given, any event).
create or replace function private.pin_ok(p_pin text, p_event text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select coalesce(p_pin, '') <> '' and exists (
    select 1 from private.settings
    where lower(v) = lower(trim(p_pin))
      and (k = 'admin_pin'
           or (p_event is null and (k = 'pin' or k like 'pin:%'))
           or k = coalesce((select k2.k from private.settings k2 where k2.k = 'pin:' || p_event), 'pin'))
  )
$fn$;

drop function if exists public.check_pin(text);
create or replace function public.check_pin(p_pin text, p_event text default null) returns boolean
language sql stable security definer set search_path = private as $fn$
  select private.pin_ok(p_pin, p_event)
$fn$;
grant execute on function public.check_pin(text, text) to anon, authenticated;

create or replace function public.write_doc(p_pin text, p_collection text, p_id text, p_data jsonb, p_mode text)
returns void language plpgsql security definer set search_path = public, private as $fn$
begin
  if not private.pin_ok(p_pin, private.event_of(p_collection)) then
    raise exception 'wrong pin' using errcode = '28000';
  end if;
  if p_mode = 'delete' then
    delete from public.docs where collection = p_collection and id = p_id;
  elsif p_mode = 'set' then
    insert into public.docs (collection, id, data) values (p_collection, p_id, p_data)
      on conflict (collection, id) do update set data = excluded.data, updated_at = now();
  else
    insert into public.docs (collection, id, data) values (p_collection, p_id, p_data)
      on conflict (collection, id) do update
      set data = public.jsonb_deep_merge(public.docs.data, excluded.data), updated_at = now();
  end if;
end
$fn$;

-- Change one event's PIN (or the shared fallback PIN when no event is given).
drop function if exists public.change_pin(text, text);
create or replace function public.change_pin(p_admin text, p_new text, p_event text default null) returns text
language plpgsql security definer set search_path = private as $fn$
declare admin text := (select v from private.settings where k = 'admin_pin');
begin
  if admin is null or admin = 'CHANGE-ME' then return 'not_set_up'; end if;
  if lower(coalesce(p_admin, '')) is distinct from lower(admin) then return 'wrong_admin'; end if;
  if length(trim(coalesce(p_new, ''))) < 4 then return 'too_short'; end if;
  insert into private.settings (k, v) values (coalesce('pin:' || p_event, 'pin'), trim(p_new))
    on conflict (k) do update set v = excluded.v;
  return 'ok';
end
$fn$;
grant execute on function public.change_pin(text, text, text) to anon, authenticated;
