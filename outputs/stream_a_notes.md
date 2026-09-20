# Stream A notes (LST, for the README methods and limitations sections)

Regenerate: `.venv/Scripts/python src/lst.py`. Downloads are cached in `data/`, a
rerun with the cache present takes seconds.

## Read the CSV with string ids

`pd.read_csv("outputs/stop_lst.csv", dtype={"stop_id": str})`, same reason as B's file.

## Method (for the README)

- Land surface temperature from Landsat 8 and 9 Collection 2 Level-2 (`lwir11`
  band, 30 m), fetched from the Microsoft Planetary Computer STAC API. No manual
  downloads, no auth. Source: https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2
- 37 scenes, June 2 to September 15, 2026, scene cloud cover up to 90 percent.
  Every pixel is masked individually with the `qa_pixel` band (fill, dilated cloud,
  cirrus, cloud, cloud shadow), then the per-pixel median across all scenes is taken.
  Scene-level cloud percentage barely matters with per-pixel masking, which is why
  cloudy scenes are kept, each contributes its clear pixels.
- Scale factor 0.00341802 and offset 149.0 were read from the STAC asset metadata
  at runtime and match the published USGS constants, then Kelvin to Celsius.
- Each stop gets a 100 m buffer built in EPSG:6440 (Florida North, meters), zonal
  mean and max against the composite. Median buffer holds 35 pixels.
- Composite sanity: county median 33.2 C, 1st to 99th percentile 23 to 43 C, which
  is the expected envelope for a Florida summer mid-morning overpass.

## Limitations (state these plainly)

- 42 of 971 stops (4.3 percent) have `pixel_count = 0` and null temperatures. This
  is not cloud. The Landsat Collection 2 ST product has a known structural gap where
  its ASTER GED emissivity auxiliary layer has holes, and one such hole covers a
  patch of west-central Gainesville (Westgate area and nearby). Raw `lwir11` is
  nodata there on every scene, including a 7 percent cloud day. Show these stops as
  "no data" rather than scoring them as cool.
- Landsat overpasses Gainesville around 10:30 am local. Values underestimate the
  mid-afternoon peak a rider actually feels. The ranking is relative across stops,
  so the ordering is still meaningful; do not present the Celsius values as
  afternoon temperatures.
- 30 m pixels smear a bus stop with its immediate surroundings. The 100 m buffer is
  a deliberate neighborhood average, not the temperature of the concrete pad.
- Median composite over a season, not a single heat event. Steadier and more
  defensible, but it will not show the worst single day.

## Gap-fill for the 42 no-data stops (opt-in, `outputs/stop_lst_gapfill.csv`)

The 42 stops in the emissivity hole now have estimated temperatures. Method: the
`trad` thermal radiance band has no emissivity dependency and covers 99.8 percent
of the county, so a median brightness temperature composite was built from the
same 37 scenes (Planck constants read from each scene's MTL metadata), then a
linear fit of ST against BT over the 929 stops that have both (r2 0.76, RMSE
1.45 C) predicts ST where the product is blank. The file has the contract columns
plus `method`, `fit_r2`, `fit_rmse_c`. If used, say in the README that 42 stops
carry estimated values with about 1.5 C uncertainty, which moves percentile ranks
only modestly. If not used, keep showing them as no data. C's call; the main
`stop_lst.csv` is untouched.

Regenerate: `.venv/Scripts/python src/lst.py gapfill`.

## Ranking robustness (for the README, and for judge questions)

Tested by splitting the summer into two independent halves (odd vs even solar
days), rebuilding the composite from each, and re-ranking.

- The LST layer alone is noisy at single-stop precision: Spearman 0.38 between
  halves, top-decile overlap 24 percent. Temperature differences between
  Gainesville stops are a few degrees, close to what one summer of 30 m Landsat
  can resolve. A single clear day is worse (Spearman 0.65 against the full
  composite). This is why the composite exists and why the score uses LST
  percentile rather than raw degrees.
- The final ranking is much steadier because trips, shelter, and equity are
  deterministic: rebuilding the full score with each half-composite keeps 13 to
  15 of the official top 20 in the top 20, and each noisy half still correlates
  0.71 to 0.75 with the full composite.
- Suggested framing: present the top 20 as a set of priority stops, not as a
  precise ordinal ranking. Say plainly that positions within the list can swap
  under measurement noise, but membership in the list is stable.

## Canopy proxy (opt-in, `outputs/stop_canopy.csv`)

Sentinel-2 L2A at 10 m, 17 summer scenes, SCL cloud mask, median NDVI composite.
The processing-baseline DN offset of 1000 was removed before the ratio (MPC
serves unharmonized values). Per stop, in the same 100 m buffer: `mean_ndvi` and
`pct_green` (share of pixels with NDVI above 0.4, a canopy-or-dense-vegetation
fraction). All 971 stops covered. Greener buffers run cooler (r = -0.55 against
mean LST), which cross-validates both layers. Intended for map popups ("bare
surroundings" vs "tree cover nearby"), especially where OSM shelter status is
unknown. The score formula is frozen; this is context, not an input.

Regenerate: `.venv/Scripts/python src/lst.py canopy`. Source:
https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a

## ECOSTRESS afternoon heat (narrative only, no per-stop file)

We pulled all 20 unique afternoon (12:00 to 17:00 EDT) ECOSTRESS ECO_L2T_LSTE
overpasses of Gainesville for summer 2026 from the LP DAAC cloud. Only 3 were
usable after cloud screening: Florida summer afternoons are almost always
cloudy, and the remaining overpasses were too contaminated to rank individual
stops (rank agreement with the Landsat layer stayed near 0.2, so a per-stop
afternoon CSV was deliberately not shipped). What the clearest afternoon does
support, for the README and the demo script:

- On August 14, 2026 at 2:52 PM, the median surface in the Gainesville tile
  was 44.3 C and a quarter of the area exceeded 50 C (ECOSTRESS, 70 m, 88
  percent cloud-free).
- The morning Landsat composite median is 33.2 C. Mid-morning satellite values
  understate what an afternoon rider stands on by roughly 10 C.
- Use this as one or two sentences of context. Do not present afternoon values
  per stop; we tested that and the data cannot support it. Saying we checked is
  itself credible.

Source: NASA ECOSTRESS ECO_L2T_LSTE v2 via NASA Earthdata / LP DAAC.
Regenerate: `.venv/Scripts/python src/lst.py eco` (needs an Earthdata login;
tiles are cached in data/ecostress/).

## Nearest sheltered stop per route (opt-in, `outputs/nearest_shelter.csv`)

For every stop-route pair: the closest OSM-sheltered stop on the same route,
straight-line distance, walk minutes at 80 m per minute, and a
`no_shelter_within_5min` flag. Regenerate: `.venv/Scripts/python
src/nearest_shelter.py` (new Stream A file, reads B's outputs only).

Headline numbers: 57 percent of the 1434 stop-route pairs have no sheltered
stop within a 5 minute walk on their route. Route 7 is 99 percent flagged,
Route 6 is 98 percent. Caveat to state wherever this is shown: OSM shelter
coverage is partial (370 stops unknown), so "no sheltered stop nearby" means
"none that OSM knows of" and the flag is an upper bound.

Suggested popup or panel text for a flagged stop:

  No sheltered stop within a 5 minute walk on this route (per OpenStreetMap).
  To ask for a shelter here: report it in the myGNV portal (myGNV.org or the
  myGNV app), or contact RTS Customer Service at 352-334-2600 (Rosa Parks
  Downtown Station, Mon-Fri 8 am to 4 pm) or via the contact form at
  go-rts.com. RTS says stop improvements weigh "safety and accessibility
  concerns first and then how many people use the stop", which is what this
  map measures. Public input also goes to the RTS Citizens Advisory Board.

Sources: go-rts.com FAQ and contact pages, gainesvillefl.gov RTS pages,
myGNV portal. Wiring this into the map is C's surface; if it does not make
the freeze it is a clean post-hackathon "how it could be extended" item,
which the track judging asks about anyway.

## Shade-need identifier (opt-in, `outputs/shade_need.csv`)

A second top 20 that answers a different question than the main score. The
main score multiplies by trip volume, so it answers "where does a shelter
help the most riders" and campus dominates. This one answers "where is the
wait itself worst," built deliberately for social benefit:

    shade_need = lst_percentile * (1 - pct_green / 100)
                 * shelter_factor * social_vulnerability

- Any weekday service qualifies. Sparse service means longer waits in the
  sun, not less need; a frequency bar would exclude the neighborhoods
  transit serves worst.
- Unknown shelter status is included at factor 1.25 (confirmed none is 1.5,
  C's convention). OSM mapping is densest around campus and wealthier
  areas, so excluding unmapped stops would bias against under-mapped
  neighborhoods.
- social_vulnerability blends car-free households and residents 65 plus,
  the population heat harms most. Both columns are B's census work.

814 stops qualify; `shade_need_rank` and `top20_shade_need` join on
`stop_id`. Only 4 of the top 20 overlap with the official list. Rank 4 is
the stop at GRACE Marketplace, the homeless services campus (13 buses a
day, 23 percent green, no shelter). Others include Gainesville High School,
Westgate Mobile Manor Park, and CVS @ Millhopper in a tract that is 28
percent seniors. This is the demo list: real poles on bare asphalt where
the people waiting have no alternative.

Suggested use: a distinct marker or badge on the map ("needs shade most"),
or at minimum a second table in the README and Devpost text. One sentence
for judges: among stops without a confirmed shelter, need is how hot the
stop is, times how bare its surroundings are, times how vulnerable the
neighborhood is. Regenerate: `.venv/Scripts/python src/shade_need.py`.

## App-style map page (`docs/app.html`, new files only, say it out loud to C)

A second, app-style view at /app.html: full-screen light basemap, search box,
filter chips (all, priority top 20, needs shade most, no shelter), and a
Google-Maps-style side panel per stop with stats, badges, the no-nearby-
shelter warning with myGNV and RTS contacts, and rider photos grouped into
morning, midday, afternoon, evening and night tabs. It reuses C's Supabase
photo backend exactly (same config.js, same stop_reports table, same
validation and review flow), so one Supabase setup turns on uploads for both
pages, and photos submitted on either page appear on both. index.html is
untouched; the classic map stays the submitted artifact. Data comes from
docs/app_data.json, baked by src/make_app_data.py from the committed CSVs.

## EMERGE curriculum requirement (flag for C, from the track PDF in repo root)

The track requires naming at least one EMERGE curriculum and the lesson or method
used. The README and Devpost text must do this explicitly. This pipeline follows the
Textbook 1 (Data Analysis) workflow: acquire public environmental data, clean it
(cloud masking), analyze it (zonal statistics, ranking), visualize and communicate
it for a non-expert audience. C should pull up Textbook 1, pick the specific lesson
whose steps match, and cite it by name and link. The geoemerge package is optional;
if unused, say the workflow follows the curriculum method. The EMERGE lead is a
judge, so this framing is worth doing carefully. Submissions close 5 PM per the PDF,
not 4:30.
