-- ShadeMap: community-reported missing bus stops.
-- Paste this whole file into Supabase, SQL Editor, New query, and click Run
-- (same as setup.sql, and safe to run more than once).
--
-- Public (anon key) may: submit one suggestion row, always pending.
-- Public may read only suggestions an admin approved.
-- Public may not approve, edit, or delete anything.

create table if not exists public.stop_suggestions (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  lat         double precision not null check (lat between 29.0 and 30.4),
  lon         double precision not null check (lon between -83.0 and -81.6),
  note        text not null check (char_length(note) between 3 and 280),
  routes      text check (routes is null or char_length(routes) <= 60),
  approved    boolean not null default false
);

alter table public.stop_suggestions enable row level security;

revoke all on public.stop_suggestions from anon;
grant insert (lat, lon, note, routes) on public.stop_suggestions to anon;
grant select on public.stop_suggestions to anon;

drop policy if exists "anyone can suggest a missing stop" on public.stop_suggestions;
create policy "anyone can suggest a missing stop"
  on public.stop_suggestions for insert to anon
  with check (approved = false);

drop policy if exists "anyone can read approved suggestions" on public.stop_suggestions;
create policy "anyone can read approved suggestions"
  on public.stop_suggestions for select to anon
  using (approved = true);

-- Review queue, same style as photos:
--   select id, created_at, lat, lon, note, routes from stop_suggestions
--     where approved = false order by created_at;
--   update stop_suggestions set approved = true where id = 'PASTE-ID';
--   delete from stop_suggestions where id = 'PASTE-ID';
