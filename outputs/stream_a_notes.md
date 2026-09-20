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
