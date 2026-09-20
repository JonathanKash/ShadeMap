# Turning on rider photo uploads (Supabase setup)

The map has a built-in "Add a photo of this stop" button in every popup. It stays hidden until
someone connects a free Supabase project. Until then the map behaves exactly as before.

What a visitor does: tap a stop, tap **Add a photo of this stop**, pick or take a photo, confirm
the date and time they took it, optionally add a note, tick the consent box, and send. Nothing
appears on the map until an admin approves it.

## One-time setup (about 10 minutes, one person)

1. Go to https://supabase.com, sign in, and click **New project**. Any name and region, pick a
   database password and keep it somewhere safe. Wait about 2 minutes for it to finish.
2. Open **SQL Editor**, click **New query**, paste the whole of `supabase/setup.sql`, and click
   **Run**. It should say "Success. No rows returned." It is safe to run again.
3. Open **Project Settings, API** and copy two values:
   - **Project URL**, for example `https://abcdefgh.supabase.co`
   - **anon public** key (a long string starting `eyJ`)
4. Paste them into `docs/config.js`:

   ```js
   supabaseUrl: "https://abcdefgh.supabase.co",
   supabaseAnonKey: "eyJ...",
   ```

   Commit and push to `main`. GitHub Pages republishes in about a minute and the button appears.
   The anon key is designed to be public, and `setup.sql` limits what it can do. **Never** paste
   the `service_role` key anywhere in this repo.
5. Test it from a phone: submit a photo for any stop, then follow "Approve a photo" below.

## Approve a photo (the review step)

Every submission starts as **pending** and is invisible on the map.

1. In Supabase open **SQL Editor** and run this to list what is waiting. Replace `YOUR-REF` with
   the part before `.supabase.co` in the project URL:

   ```sql
   select id, created_at, stop_id, taken_date, taken_time, time_bucket, note,
          'https://YOUR-REF.supabase.co/storage/v1/object/public/stop-photos/' || photo_path as photo_url
   from stop_reports where approved = false order by created_at;
   ```

2. Open each `photo_url` in a browser and look at it. Approve only photos that show a real bus
   stop, with **no recognizable faces, no license plates, nothing offensive**, and a note that is
   fine to publish.
3. To approve, run (use the `id` from the list):

   ```sql
   update stop_reports set approved = true where id = 'PASTE-ID-HERE';
   ```

   The photo shows in that stop's popup the next time someone opens it. No republish needed.
4. To reject, delete the row, and the photo too if you like (Storage, `stop-photos`):

   ```sql
   delete from stop_reports where id = 'PASTE-ID-HERE';
   ```

   You can also do all of this by hand in **Table Editor, stop_reports** (tick the `approved`
   box on a row).

## What is stored and what is protected

- **Photos:** JPEG only, at most 5 MB, resized to 1280 px in the visitor's browser. The browser
  re-encodes each photo, which removes the GPS location and other metadata a phone embeds. We
  tested this: an upload built with GPS data arrived with none.
- **Reports:** stop id, photo file name, the date and time the visitor says it was taken, a
  time-of-day label (morning, midday, afternoon, evening, night), an optional note of at most
  280 characters, and the approved flag. No names, emails, or accounts are collected.
- **What the public key can do:** upload a new photo file, add a report that is always pending,
  and read reports that are approved. It cannot approve, edit, or delete anything, and it cannot
  list the photo bucket.
- **Known limits, stated plainly:**
  - Photos are stored in a public bucket so approved ones load by URL. A pending photo is only
    reachable if someone knows its random file name, which only the uploader does, but it is not
    locked down the way a private bucket would be.
  - Protection against spam is light: a hidden bot-trap field and a 30 second wait between sends
    per browser. A determined person could still flood the queue. If that happens, tighten it in
    Supabase or turn the feature off by emptying the two values in `docs/config.js`.
  - The date and time are what the visitor says. We do not verify them.
  - A failed second step can leave an orphan photo in the bucket with no report. Harmless, but you
    can delete it in Storage.
  - The free tier pauses a project after a week with no activity. Open the dashboard to wake it.

## Turn it off

Set `supabaseUrl` and `supabaseAnonKey` in `docs/config.js` back to empty strings and push.
The buttons and gallery disappear and the map returns to its original behavior.

## For developers

- Form, upload, and gallery code: `docs/report.js`. Styles: `docs/report.css`.
- `src/make_map.py` adds the button and gallery slot to every popup and loads the scripts.
- The photo feature talks to Supabase with plain `fetch` (no libraries): `POST /storage/v1/object`
  for the photo, `POST /rest/v1/stop_reports` for the report, `GET /rest/v1/stop_reports?approved=eq.true`
  for the gallery.
