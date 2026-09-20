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
