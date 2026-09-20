-- ShadeMap community photo reports: one-time Supabase setup.
-- Paste this whole file into Supabase, SQL Editor, New query, and click Run.
-- It is safe to run more than once.
--
-- What the public (anon key) can do after this:
--   * upload one JPEG photo, and add a report row that is always "pending"
--   * read only reports that an admin has approved
-- What the public cannot do: approve, edit, or delete anything, or list the bucket.

-- 1. Reports table ---------------------------------------------------------------
create table if not exists public.stop_reports (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  stop_id     text not null check (char_length(stop_id) between 1 and 20),
  photo_path  text not null check (photo_path ~ '^[0-9a-f-]{36}\.jpg$'),
  taken_date  date not null check (taken_date between current_date - 366 and current_date + 1),
  taken_time  time not null,
  time_bucket text not null check (time_bucket in ('morning', 'midday', 'afternoon', 'evening', 'night')),
  note        text check (note is null or char_length(note) <= 280),
  approved    boolean not null default false
);

alter table public.stop_reports enable row level security;

-- The public may only insert the columns below, so "approved" can never be set by a visitor.
revoke all on public.stop_reports from anon;
grant insert (stop_id, photo_path, taken_date, taken_time, time_bucket, note) on public.stop_reports to anon;
grant select on public.stop_reports to anon;

drop policy if exists "anyone can submit a pending report" on public.stop_reports;
create policy "anyone can submit a pending report"
  on public.stop_reports for insert to anon
  with check (approved = false);

drop policy if exists "anyone can read approved reports" on public.stop_reports;
create policy "anyone can read approved reports"
  on public.stop_reports for select to anon
  using (approved = true);

-- 2. Photo bucket ----------------------------------------------------------------
-- Public bucket so approved photos load by URL. Uploads are limited to 5 MB JPEGs
-- (the map page converts every photo to JPEG and strips its location data first).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('stop-photos', 'stop-photos', true, 5242880, array['image/jpeg'])
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- The public may upload a new file with a random UUID name. There is no select policy,
-- so nobody can list the bucket, and existing files cannot be replaced or deleted.
drop policy if exists "anyone can upload a photo" on storage.objects;
create policy "anyone can upload a photo"
  on storage.objects for insert to anon
  with check (bucket_id = 'stop-photos' and name ~ '^[0-9a-f-]{36}\.jpg$');
