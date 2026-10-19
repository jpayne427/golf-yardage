-- ShipStiffs: a captain's PIN tier.
-- Paste this whole script into Supabase > SQL Editor > Run. Safe to run again.
-- Run event-pins.sql first (this builds on it).
--
-- Three tiers of PIN:
--   trip PIN       ('pin:<event>')      keeps score, sets up matches and games        level 1
--   captain's PIN  ('captain:<event>')  everything above, plus the captain-only edits  level 2
--   organizer PIN  ('admin_pin')        everything, every event                        level 3
--
-- Captain-only edits (enforced here, not just in the app):
--   - deleting a match
--   - a match's result override, lock, or stroke overrides (matches.manual / locked / strokes)
--   - course cards and tees (the courses collection)
--   - handicap allowances (setup.allowances)
--   - a player's course handicap override for a round (cards.ch)
--
-- Set each event's captain PIN from the app (Setup > Event PIN, needs the organizer PIN),
-- or here:  select public.set_pin('<organizer pin>', '<new captain pin>', 'bandon-2026', 'captain');

-- 0 = no, 1 = trip PIN, 2 = captain's PIN, 3 = organizer PIN
create or replace function private.pin_level(p_pin text, p_event text) returns int
language sql stable security definer set search_path = private as $fn$
  select coalesce((
    select max(case when k = 'admin_pin' then 3 when k like 'captain:%' then 2 else 1 end)
    from private.settings
    where coalesce(p_pin, '') <> '' and lower(v) = lower(trim(p_pin))
      and (k = 'admin_pin'
           or (p_event is null and (k = 'pin' or k like 'pin:%' or k like 'captain:%'))
           or k = 'captain:' || p_event
           or k = coalesce((select k2.k from private.settings k2 where k2.k = 'pin:' || p_event), 'pin'))
  ), 0)
$fn$;

create or replace function private.pin_ok(p_pin text, p_event text) returns boolean
language sql stable security definer set search_path = private as $fn$
  select private.pin_level(p_pin, p_event) >= 1
$fn$;

-- The app asks this once when a phone unlocks, to know which buttons to show.
create or replace function public.pin_level(p_pin text, p_event text default null) returns int
language sql stable security definer set search_path = private as $fn$
  select private.pin_level(p_pin, p_event)
$fn$;
grant execute on function public.pin_level(text, text) to anon, authenticated;

create or replace function public.write_doc(p_pin text, p_collection text, p_id text, p_data jsonb, p_mode text)
returns void language plpgsql security definer set search_path = public, private as $fn$
declare
  lvl int := private.pin_level(p_pin, private.event_of(p_collection));
  kind text := case when position('.' in p_collection) > 0 then split_part(p_collection, '.', 2) else p_collection end;
begin
  if lvl < 1 then
    raise exception 'wrong pin' using errcode = '28000';
  end if;
  if lvl < 2 then
    if (kind = 'matches' and (p_mode = 'delete' or p_data ?| array['manual', 'locked', 'strokes']))
       or kind = 'courses'
       or (kind = 'setup' and p_mode <> 'set' and p_data ? 'allowances')
       or (kind = 'cards' and p_data ? 'ch') then
      raise exception 'captain only' using errcode = '42501';
    end if;
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

-- Set an event's trip PIN or captain's PIN. Needs the organizer PIN.
create or replace function public.set_pin(p_admin text, p_new text, p_event text, p_role text default 'pin') returns text
language plpgsql security definer set search_path = private as $fn$
declare admin text := (select v from private.settings where k = 'admin_pin');
begin
  if admin is null or admin = 'CHANGE-ME' then return 'not_set_up'; end if;
  if lower(coalesce(p_admin, '')) is distinct from lower(admin) then return 'wrong_admin'; end if;
  if length(trim(coalesce(p_new, ''))) < 4 then return 'too_short'; end if;
  if p_role not in ('pin', 'captain') then return 'bad_role'; end if;
  if coalesce(p_event, '') = '' then return 'no_event'; end if;
  insert into private.settings (k, v) values (p_role || ':' || p_event, trim(p_new))
    on conflict (k) do update set v = excluded.v;
  return 'ok';
end
$fn$;
grant execute on function public.set_pin(text, text, text, text) to anon, authenticated;
