# CLAUDE.md

Project context for Claude Code. Read this before writing any code.

## What this is

A 6-hour hackathon project for CityCamp Gainesville Hack Day (Sept 20, 2026, submissions
due 4:30 PM). Track: NASA / Environmental Data.

**One-line pitch:** Rank every RTS bus stop in Gainesville by heat exposure so the city
knows which stops should get shade structures first.

**The problem:** Riders stand on unshaded asphalt in Florida summer heat. The people most
affected are the ones without a car. Nobody has a ranked, data-backed list of which stops
are worst.

**The deliverable:** an interactive map, a `top_20_stops.csv`, and a notebook that runs
top to bottom. The Devpost submission accepts "a data analysis with a reproducible
notebook, map, or visualization," so this counts as a complete artifact on its own.

## Judging criteria (optimize for these, in this order)

1. **Problem and impact.** Would this actually help people in Gainesville? The census
   equity layer is what carries this. Do not cut it before cutting other things.
2. **Execution.** Does it run? A working narrow version beats a broken ambitious one.
3. **Design and usability.** The map has to be legible to a non-technical judge in five
   seconds.
4. **Clarity.** The scoring formula must be explainable in one sentence out loud.

## Data sources

Fetch in this order. Get each one working end to end before moving on.

| Layer | Source | Notes |
|---|---|---|
| Land surface temperature | Landsat 8/9 Collection 2 Level-2, via Microsoft Planetary Computer STAC API (`pystac-client`, `planetary-computer`, `odc-stac`) | No manual downloads, no auth. Use the `lwir11` surface temperature band. Pull several cloud-free summer 2026 scenes over Alachua County and take a median composite. Apply the Collection 2 scale factor (0.00341802) and offset (149.0) to get Kelvin, then convert to Celsius. |
| Bus stops and service frequency | RTS GTFS feed | `stops.txt` for coordinates, join `stop_times.txt` grouped by `stop_id` for trips per day. Trip count is the exposure weight since per-stop ridership is probably not public. |
| Shelter presence | OpenStreetMap via Overpass API | Query `highway=bus_stop` and `public_transport=platform` in the Gainesville bbox, read the `shelter` tag. Coverage is partial. Treat missing as unknown, not as "no shelter," and say so in the README. |
| Transit dependence | Census ACS 5-year, tract level, via the Census API | Table B08201 (households with no vehicle) and B01001 (age 65+). Spatial join stops to tracts. |

Optional upgrade if and only if everything above works and there is time left:
ECOSTRESS LST via NASA AppEEARS (needs a free Earthdata login). Roughly 70m resolution
and varied overpass times, which lets you show afternoon heat specifically. Stronger NASA
story, slower to get. Do not start here.

## Scoring formula

Keep it simple and defensible. Target shape:

```
score = lst_percentile * log1p(daily_trips) * shelter_multiplier * transit_dependence
```

- `lst_percentile`: percentile rank of mean LST within a 100m buffer of the stop, across
  all stops. Percentile rank, not raw temperature, so the numbers stay interpretable.
- `shelter_multiplier`: 1.5 if OSM says no shelter, 1.0 if sheltered, 1.25 if unknown.
- `transit_dependence`: normalized 0.5 to 1.5 from the tract's no-vehicle household share.

Do not build a model. Do not weight-tune to make a result look better. If a judge asks
"why is stop #1 first," the answer must be a sentence, not a paragraph.

## Stack

- Python 3.11, single notebook `analysis.ipynb`, with reusable bits in `src/`
- `geopandas`, `rasterio`/`rioxarray`, `pandas`, `pystac-client`, `planetary-computer`,
  `odc-stac`, `folium`, `requests`
- Output map: `docs/index.html` (static Folium export), served via GitHub Pages
- CRS: do analysis in EPSG:6440 (Florida North, meters) for the buffers, write outputs in
  EPSG:4326

## Build order and time budget

Hard stop for feature work is 3:30 PM. The last hour is submission, not code.

- **10:00 to 11:00** One Landsat scene loading, clipped to Alachua County, LST in Celsius,
  plotted once to eyeball it. Do not proceed until this renders.
- **11:00 to 12:00** GTFS parsed into a stops GeoDataFrame with `daily_trips`.
- **12:00 to 13:00** Buffer, zonal stats, join OSM shelters and census tracts, compute score.
- **13:00 to 14:30** Folium map and `top_20_stops.csv`.
- **14:30 to 15:30** README, notebook cleanup so it runs top to bottom from a fresh kernel,
  push, enable Pages.
- **15:30 to 16:00** Pull Google Street View images for the top 3 stops and save them to
  `assets/`. This is the demo. A judge seeing a real photo of a real bare stop pole with
  no bench is worth more than the whole pipeline.
- **16:00 to 16:30** Submit on Devpost. Do not be writing code during this window.

## Cut order (when time runs out)

Cut from the top of this list first:

1. ECOSTRESS
2. Multi-scene median composite (fall back to one good cloud-free scene)
3. OSM shelter join (keep the column, set everything to unknown)
4. Census equity layer (last resort, this is the impact argument)

Never cut: the ranked CSV, the map, the Street View photos.

## Map design rules

- Default view centered on Gainesville, zoom 12
- Stops as circle markers, size by score, color on a sequential ramp with a legend that
  says what the colors mean in plain words, not just numbers
- Top 20 stops get a distinct marker and a popup with: stop name, route(s), daily trips,
  mean LST, shelter status, rank
- One sentence of context in a title bar on the map itself, since the map may get shared
  without the README
- Works on a phone. A judge may open it on their own device.

## Writing conventions

- No em dashes anywhere, including in the README and map copy
- README leads with the problem and a screenshot, then the method, then how to run it
- State limitations plainly: partial OSM shelter coverage, trip counts as a ridership
  proxy, single-date or short-window satellite data, tract-level census as a coarse proxy
  for stop-level population. Naming these builds credibility rather than costing it.
- No claims about what the city "will" do with this. Say what the list shows.

## Repo layout

```
.
├── CLAUDE.md
├── README.md
├── analysis.ipynb
├── src/
│   ├── lst.py          # Landsat fetch, scale, composite, clip
│   ├── gtfs.py         # stop parsing, trip counts
│   ├── context.py      # OSM shelters, census tracts
│   └── score.py        # buffer, zonal stats, scoring
├── data/               # gitignored, cached downloads
├── outputs/
│   └── top_20_stops.csv
├── docs/
│   └── index.html      # the map, served by GitHub Pages
└── assets/             # Street View photos of top stops
```

## Working style for this session

- Write code that runs now over code that is architecturally clean. This repo has a
  6-hour lifespan.
- Cache every network fetch to `data/` so reruns are instant. Rate limits and flaky
  downloads are the most likely thing to eat an hour.
- Print shapes and value ranges after every major step. Silent geospatial bugs (wrong CRS,
  unscaled bands, empty joins) are the second most likely thing to eat an hour.
- If a step has taken more than 20 minutes past its budget, apply the cut list instead of
  debugging further.
