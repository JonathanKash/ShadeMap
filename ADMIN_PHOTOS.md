# Adding stop photos (admin guide)

**Most people should use the rider photo button in the app.** Open a stop, tap the add photo
button, and a maintainer approves it before it appears (setup and review steps are in
`SUPABASE_SETUP.md`). This guide is for the other route: photos the team adds by hand, which
show up in the popups of the **classic map** (`classic.html`), not in the app view. There is no
server and no login system, so nothing here costs money.

## Add or replace a photo by hand

1. **Take the photo.** Daylight, the whole stop in frame (pole, bench, shelter or bare
   pavement), phone held sideways if you can. Do not include people's faces.
2. **Find the stop's id.** Open `outputs/priority_near_far_campus.csv` (the two top 10 lists)
   or `outputs/scored_stops.csv` on GitHub and read the `stop_id` column. Example: stop `807`
   is University Village South Apartments.
3. **Name the file after the id:** `807.jpg`. Also accepted: `.jpeg`, `.png`, `.webp`. One
   photo per stop.
4. **Upload it.** On the repo page on GitHub go to `docs/photos/`, click **Add file**, then
   **Upload files**, drag the photo in, and click **Commit changes** (commit to `main`).
   - **First upload ever:** the `docs/photos/` folder does not exist yet. Click **Add file**,
     then **Create new file**, type `docs/photos/README.txt` as the name, write anything in
     it, and commit. That creates the folder. Then upload photos into it as above.
5. **Finish the upload (required).** Uploading the file is not enough: someone with the project
   on their computer runs the command below. It shrinks the photo, removes the GPS location
   your phone stored inside it, and updates `outputs/stop_photos.csv`, the list the classic map
   reads. There is no automatic step for this yet, so until the command runs the photo sits in
   the folder and the map does not show it.

To remove a photo, delete the file from `docs/photos/` and run the command again.

## Finish the upload

```
.venv/bin/python src/photos.py --resize
.venv/bin/python src/make_map.py          # rebuilds docs/classic.html so the popups pick up the photo
git add docs/photos outputs/stop_photos.csv docs/classic.html && git commit -m "Update stop photos" && git push
```

`src/photos.py` also prints which of the top 20 stops still have no photo, and flags files
with a wrong name, a stop id that does not exist, or a file that is not a real image.

## What the script does to every photo

- Scales it to at most 1280 px on the long side, so the map loads on a phone.
- Removes EXIF metadata, which includes the GPS position and time of the photo.
- Applies the phone's rotation first, so portrait photos are not sideways.
- Leaves an already small, clean photo untouched, so re-running never changes it.

## For whoever maintains the map code (`src/make_map.py`)

`outputs/stop_photos.csv` lists the stops that have a photo (`stop_id, file, stop_name,
rank`). It is only the header line until the first upload. To show photos, read it in
`make_map.py` and add an image to the popup when the stop has one. Photos are served from
`photos/` next to `classic.html`:

```python
# once, near the top of make_map.py
photos = pd.read_csv(ROOT / "outputs" / "stop_photos.csv", dtype={"stop_id": str})
PHOTO_FILE = dict(zip(photos.stop_id, photos.file))

# inside popup_html(r, ranked), just before the final closing </div> of the return value
img = PHOTO_FILE.get(str(r["stop_id"]))
photo = (f'<img src="photos/{escape(img)}" alt="Photo of {name}" loading="lazy" '
         f'style="width:100%;margin-top:6px;border-radius:4px">') if img else ""
# then add   f'{photo}'   as the last piece of the returned string, after the green cover line
```

Because the file list comes from the CSV, popups never link to a missing image. Credit
line for photos taken by the team: "Photo: ShadeMap team". For any photo from someone else,
get their permission and credit them.

## Handling a shelter report (community corrections)

Every stop popup has a **Shelter info wrong? Tell us** link. It opens a prefilled GitHub
issue with the stop name, its id, and what the map currently says. Popups for stops not
known to be sheltered also say **Want a shelter here?** with the City of Gainesville request
portal (myGNV, mygnv.org) and the RTS phone number from RTS's own GTFS feed. The map makes
no promise about what the city will do with a request.

When someone reports a stop:

1. **Check it.** Look at the attached photo, or visit. Do not accept a report you cannot
   back up. A wrong shelter status is worse than an unknown one.
2. **Add one row** to `outputs/shelter_overrides.csv`:
   ```
   stop_id,status,source,date
   1254,sheltered,"photo from issue #12, checked against Street View",2026-09-21
   ```
   `status` is exactly `sheltered`, `none` or `unknown`. `source` is required and says how it
   was verified. If a stop appears twice the newest row wins.
3. **Rebuild** (needs the venv from `requirements.txt`; scores and the map read the new value):
   ```
   cd src && ../.venv/bin/python context.py && cd ..
   .venv/bin/python src/score.py && .venv/bin/python src/make_map.py
   .venv/bin/python src/make_app_data.py
   ```
   The app view (`docs/app.html`, the default page) reads `docs/app_data.json`, so skip the last
   line and it will keep showing the old shelter status.
4. Commit `outputs/shelter_overrides.csv`, `outputs/stops_context.csv`, the scored files,
   `docs/classic.html` and `docs/app_data.json`, then close the issue and thank the reporter.

`context.py` stops with an error on a row with no source, a bad status, or a stop id that
does not exist, so a typo cannot silently change the data.
